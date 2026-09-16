"""Record primitives adapted from research commit 9d4140a; no product dependency."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def encoded(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_bytes())


def publish(path: Path, value: Any) -> None:
    """Adapted from research commit 9d4140a: fsync, then no-overwrite hard link."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.link(name, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        Path(name).unlink(missing_ok=True)


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", value):
        raise ValueError("Invalid identifier")
    return value


def safe_path(root: Path, name: str) -> Path:
    relative = Path(name)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(p in {"..", ".git"} for p in relative.parts)
    ):
        raise ValueError("PATH_ESCAPE")
    path = root / relative
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError("SYMLINK_REFUSED")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("PATH_ESCAPE")
    return path


def snapshot(root: Path) -> dict[str, Any]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("SYMLINK_REFUSED")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha(path.read_bytes()),
                "mode": path.stat().st_mode & 0o777,
                "symlink": None,
                "bytes": path.stat().st_size,
            }
    return result
