"""Reproduce the typed loader check without network access or model inference."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def configuration_result(report: dict[str, Any]) -> dict[str, Any]:
    """Only publish the model and the configuration check, never full configuration."""
    check = report.get("checks", {}).get("config.load", {})
    details = check.get("details", {})
    return {
        "status": check.get("status"),
        "summary": check.get("summary"),
        "model": details.get("model"),
        "provider": details.get("model provider"),
        "scope": details.get("configuration scope"),
    }


def main() -> None:
    manifest = Path(__file__).resolve().parent
    runtime = json.loads((manifest / "runtime.json").read_text())
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").exists():
        raise SystemExit("This containment check requires macOS sandbox-exec.")
    command = shutil.which("codex")
    if command is None:
        raise SystemExit("Codex CLI is missing.")
    binary = Path(command).resolve()
    if hashlib.sha256(binary.read_bytes()).hexdigest() != runtime["binary_sha256"]:
        raise SystemExit(
            "CLI binary differs from audited runtime; qualification is not transferable."
        )
    scratch = manifest.parents[1] / ".scratch-cli"
    scratch.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="doctor-reproduction-", dir=scratch))
    profile = run / "containment.sb"
    profile.write_text(
        (manifest / "containment.sb.in")
        .read_text()
        .replace("{{SCRATCH_PATH}}", json.dumps(str(run)))
    )
    records: list[dict[str, Any]] = []
    for label, effort in [("valid", "medium"), ("invalid_type", 17)]:
        output = run / label
        output.mkdir()
        argv = ["/usr/bin/sandbox-exec", "-f", str(profile), str(binary), "doctor", "--json"]
        settings = {
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": effort,
            "sqlite_home": str(output),
            "log_dir": str(output),
            "features.apps": False,
            "features.plugins": False,
            "features.memories": False,
            "features.hooks": False,
            "features.multi_agent": False,
            "features.unbounded_connection_retries": False,
            "analytics.enabled": False,
            "feedback.enabled": False,
            "check_for_update_on_startup": False,
            "web_search": "disabled",
        }
        for key, value in settings.items():
            argv.extend(["-c", key + "=" + json.dumps(value)])
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=output,
            env={**os.environ, "TMPDIR": str(output), "CODEX_SQLITE_HOME": str(output)},
            start_new_session=True,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=25)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        try:
            report = json.loads(stdout)
        except json.JSONDecodeError:
            report = {}
        record = {
            "label": label,
            "argv": argv,
            "returncode": process.returncode,
            "timed_out": timed_out,
            "configuration_load": configuration_result(report),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "network_denied": True,
            "file_writes_confined_to": str(run),
            "provider_model_calls": 0,
        }
        (run / f"{label}.json").write_text(json.dumps(record, indent=2) + "\n")
        records.append(record)
    passed = [r["configuration_load"]["status"] for r in records] == ["ok", "fail"]
    passed = passed and not any(r["timed_out"] for r in records)
    conclusion = {"configuration_loader_passed": passed, "live_preflight_passed": False}
    (run / "conclusion.json").write_text(json.dumps(conclusion, indent=2) + "\n")
    print(json.dumps({**conclusion, "receipt_directory": str(run)}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        result = configuration_result(
            {
                "checks": {
                    "config.load": {
                        "status": "ok",
                        "details": {"model": "x", "secret": "DO_NOT_EXPORT"},
                    }
                }
            }
        )
        assert result["status"] == "ok" and result["model"] == "x"
        assert "DO_NOT_EXPORT" not in json.dumps(result)
        assert configuration_result({})["status"] is None
        print("Safe configuration extraction checks passed.")
    else:
        main()
