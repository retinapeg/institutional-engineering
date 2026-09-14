"""Two local brains, one structured response contract. No automatic retries."""

import json
import tempfile
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from .runner import Blocked, Runner

T = TypeVar("T", bound=BaseModel)


class Provider(Protocol):
    def ask(
        self, provider: str, prompt: str, schema: type[T], *, model: str | None = None
    ) -> T: ...


class CliProviders:
    def __init__(
        self, runner: Runner, claude_model: str = "sonnet", codex_model: str = "gpt-5.6-terra"
    ):
        self.runner = runner
        self.models = {"claude": claude_model, "codex": codex_model}
        self.last_usage: dict[str, Any] = {}

    def ask(self, provider: str, prompt: str, schema: type[T], *, model: str | None = None) -> T:
        if provider not in self.models:
            raise Blocked(f"Unsupported provider: {provider}")
        self.last_usage = {}
        selected_model = model or self.models[provider]
        prompt = (
            "Use only the supplied repository snapshot and evidence. Do not use tools or access "
            "other files. Return one JSON object, no markdown fences, matching this schema:\n"
            + json.dumps(schema.model_json_schema())
            + "\n"
            + prompt
        )
        with tempfile.TemporaryDirectory(prefix="inst-call-") as directory:
            cwd = Path(directory)
            if provider == "claude":
                argv = [
                    "claude",
                    "-p",
                    "--output-format",
                    "json",
                    "--tools",
                    "",
                    "--safe-mode",
                    "--strict-mcp-config",
                    "--mcp-config",
                    '{"mcpServers":{}}',
                    "--no-session-persistence",
                    "--permission-mode",
                    "dontAsk",
                    "--model",
                    selected_model,
                ]
            else:
                argv = [
                    "codex",
                    "exec",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--json",
                    "-c",
                    'approval_policy="never"',
                    "-c",
                    'web_search="disabled"',
                    "-c",
                    "project_doc_max_bytes=0",
                    "-c",
                    "suppress_unstable_features_warning=true",
                    "-c",
                    'model_reasoning_effort="medium"',
                    "--model",
                    selected_model,
                ]
                for feature in (
                    "hooks",
                    "plugins",
                    "apps",
                    "shell_tool",
                    "unified_exec",
                    "multi_agent",
                    "multi_agent_v2",
                    "browser_use",
                    "in_app_browser",
                    "image_generation",
                    "view_image",
                    "memories",
                    "skill_search",
                    "sleep_tool",
                    "js_repl",
                    "tool_suggest",
                ):
                    argv.extend(["--disable", feature])
                argv.extend(["--enable", "skip_host_skill_discovery", "-"])
            _, stdout, _ = self.runner.run(argv, cwd, prompt)
        try:
            if provider == "claude":
                envelope = json.loads(stdout)
                if envelope.get("is_error") or envelope.get("subtype") != "success":
                    raise Blocked("Claude returned an unsuccessful result; check login or limits")
                payload = envelope["result"]
                self.last_usage = {
                    "models": envelope.get("modelUsage", {}),
                    "usage": envelope.get("usage", {}),
                    "reported_cost_usd": envelope.get("total_cost_usd"),
                    "monetary_spend": None,  # CLI estimate is not subscription marginal spend.
                }
            else:
                events = [json.loads(line) for line in stdout.splitlines() if line.strip()]
                messages = []
                completed = False
                for event in events:
                    if event.get("type") in {"error", "turn.failed"}:
                        raise Blocked("Codex returned a failed turn; check login or limits")
                    item = event.get("item", {})
                    if item.get("type") == "error":
                        raise Blocked("Codex: " + str(item.get("message", "unspecified CLI error")))
                    if item and item.get("type") not in {"agent_message", "reasoning", "todo_list"}:
                        raise Blocked(
                            f"Codex attempted {item.get('type')} instead of returning a structured response"
                        )
                    if (
                        event.get("type") == "item.completed"
                        and item.get("type") == "agent_message"
                    ):
                        messages.append(item["text"])
                    if event.get("type") == "turn.completed":
                        completed = True
                        self.last_usage = {
                            "usage": event.get("usage", {}),
                            "selected_model": selected_model,
                        }
                if not completed or len(messages) != 1:
                    raise Blocked("Codex did not return exactly one completed response")
                payload = messages[0]
            return schema.model_validate_json(payload)
        except (ValueError, KeyError, TypeError) as exc:
            raise Blocked(
                f"Malformed {provider} output for {schema.__name__}; adapter failed closed"
            ) from exc
