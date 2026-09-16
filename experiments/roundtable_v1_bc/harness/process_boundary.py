"""Adapted from committed research 0505e699; same known containment limits."""

from __future__ import annotations

import json
import math
import os
import resource
import selectors
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .records import sha


class BoundaryError(RuntimeError):
    pass


def profile(workspace: Path, writable: bool = True) -> str:
    roots = [
        "/System",
        "/usr",
        "/Library/Apple",
        "/private/preboot",
        "/private/var/db",
        "/dev",
        str(Path(sys.base_prefix).resolve()),
        str(workspace.resolve()),
    ]
    reads = " ".join("(subpath " + json.dumps(p) + ")" for p in roots)
    # Root-directory reads are needed by the runtime; this does not grant descendant reads.
    return (
        "(version 1)(deny default)(allow process-exec)(allow sysctl-read)(allow file-read-metadata)"
        '(allow file-read-data (literal "/") '
        + reads
        + ")"
        + (
            "(allow file-write* (subpath " + json.dumps(str(workspace.resolve())) + "))"
            if writable
            else ""
        )
    )


def run_python(
    workspace: Path,
    code: str,
    stdin: str = "",
    seconds: float = 5,
    writable: bool = True,
    cancel: Path | None = None,
) -> dict[str, Any]:
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").exists():
        raise BoundaryError("No qualified sandbox on this host")

    def limits() -> None:
        resource.setrlimit(
            resource.RLIMIT_CPU, (max(1, math.ceil(seconds)), max(1, math.ceil(seconds)))
        )
        resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

    began = time.monotonic()
    policy = profile(workspace, writable)
    argv = [
        "/usr/bin/sandbox-exec",
        "-p",
        policy,
        str(Path(sys.executable).resolve()),
        "-I",
        "-c",
        code,
    ]
    process = subprocess.Popen(
        argv,
        cwd=workspace,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(workspace),
            "TMPDIR": str(workspace),
            "LANG": "C.UTF-8",
            "TZ": "UTC",
        },
        preexec_fn=limits,
    )
    assert process.stdin and process.stdout and process.stderr
    out = {"stdout": bytearray(), "stderr": bytearray()}
    pending = memoryview(stdin.encode())
    reason = None
    try:
        with selectors.DefaultSelector() as selector:
            for f, label in [
                (process.stdout, "stdout"),
                (process.stderr, "stderr"),
                (process.stdin, "stdin"),
            ]:
                os.set_blocking(f.fileno(), False)
                selector.register(
                    f, selectors.EVENT_WRITE if label == "stdin" else selectors.EVENT_READ, label
                )
            while selector.get_map() or process.poll() is None:
                if time.monotonic() - began > seconds:
                    reason = "CANDIDATE_TIMEOUT"
                    break
                if cancel is not None and cancel.exists():
                    reason = "CANCELLED"
                    break
                for key, _ in selector.select(0.02):
                    if key.data == "stdin":
                        try:
                            pending = pending[os.write(key.fd, pending[:8192]) :]
                        except BrokenPipeError:
                            pending = memoryview(b"")
                        if not pending:
                            selector.unregister(key.fileobj)
                            process.stdin.close()
                    else:
                        chunk = os.read(key.fd, 8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            out[key.data].extend(chunk)
                            if len(out[key.data]) > 1048576:
                                reason = "OUTPUT_LIMIT"
                                break
                if reason:
                    break
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for f in (process.stdin, process.stdout, process.stderr):
            f.close()
    return {
        **{k: bytes(v[:1048576]).decode(errors="replace") for k, v in out.items()},
        "exit": process.returncode,
        "failure": reason,
        "seconds": time.monotonic() - began,
        "profile_hash": sha(policy.encode()),
    }


def negative_access_check() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="domain-canary-") as d:
        root = Path(d).resolve()
        work = root / "workspace"
        work.mkdir()
        for name in ("hidden", "prior_attempt", "credentials", "researcher"):
            (root / name).write_text("PRIVATE_CANARY_" + name)
        (work / "escape").symlink_to(root / "hidden")
        script = """import json,socket,os
from pathlib import Path
from typing import Any
paths=json.loads(input());result={}
for name,path in paths.items():
 try: Path(path).read_text();result[name]=False
 except PermissionError:result[name]=True
s=socket.socket();s.settimeout(.2)
try: s.connect(('127.0.0.1',9));result['network']=False
except PermissionError:result['network']=True
except OSError:result['network']=False
try: os.fork();result['fork']=False
except PermissionError:result['fork']=True
print(json.dumps(result))
"""
        paths = {
            name: str(root / name)
            for name in ("hidden", "prior_attempt", "credentials", "researcher")
        }
        paths["symlink"] = str(work / "escape")
        result = run_python(work, script, json.dumps(paths), writable=False)
        if result["exit"] != 0:
            raise BoundaryError("Sandbox probe failed: " + repr(result))
        checks = json.loads(result["stdout"])
        if not all(checks.values()):
            raise BoundaryError("Negative access failed: " + repr(checks))
        return {
            "checks": checks,
            "enforced": [
                "filesystem content allowlist",
                "network denial",
                "fork denial",
                "CPU seconds",
                "file size",
                "file descriptors",
                "wall timeout",
                "captured-output cap",
            ],
            "not_enforced": ["hard resident-memory cap", "read-metadata secrecy"],
            "result": result,
        }
