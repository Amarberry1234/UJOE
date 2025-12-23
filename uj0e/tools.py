from __future__ import annotations

import hashlib
import json
import logging
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    output: str
    ok: bool = True
    metadata: dict[str, Any] | None = None


class SandboxTool:
    """Executes code inside a sandboxed container with strict limits."""

    def __init__(self) -> None:
        self.memory = settings.sandbox_memory
        self.cpus = settings.sandbox_cpus
        self.timeout = settings.sandbox_timeout

    def run(self, command: str) -> ToolResult:
        docker_bin = shutil.which("docker")
        safe_command = ["/bin/bash", "-lc", command]
        if docker_bin:
            cmd = [
                docker_bin,
                "run",
                "--rm",
                "--network",
                "none",
                "--cpus",
                str(self.cpus),
                "--memory",
                str(self.memory),
                "--pids-limit",
                "128",
                "alpine",
                "timeout",
                str(self.timeout),
                "/bin/sh",
                "-c",
                command,
            ]
        else:
            cmd = ["timeout", str(self.timeout)] + safe_command

        logger.info("sandbox.run", extra={"cmd": cmd})
        try:
            start = time.time()
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            duration = time.time() - start
            output = proc.stdout + proc.stderr
            ok = proc.returncode == 0
            return ToolResult(output=output, ok=ok, metadata={"duration": duration})
        except Exception as exc:  # noqa: BLE001
            logger.exception("sandbox failure")
            return ToolResult(output=str(exc), ok=False)


class LocalFileTool:
    """Restricts file reads to DATA_ROOT."""

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.data_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self, relative_path: str) -> ToolResult:
        target = (self.root / relative_path).resolve()
        if self.root not in target.parents and self.root != target:
            return ToolResult(output="Access denied", ok=False)
        if not target.exists():
            return ToolResult(output="Not found", ok=False)
        return ToolResult(output=target.read_text())

    def write(self, relative_path: str, content: str) -> ToolResult:
        target = (self.root / relative_path).resolve()
        if self.root not in target.parents and self.root != target:
            return ToolResult(output="Access denied", ok=False)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return ToolResult(output="written", metadata={"path": str(target)})


class AuditLogger:
    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or settings.audit_log)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, action: str, payload: dict[str, Any]) -> None:
        line = json.dumps({"action": action, **payload})
        self.path.write_text(self.path.read_text() + line + "\n" if self.path.exists() else line + "\n")


class Fingerprinter:
    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 80) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - chunk_overlap
        return chunks


class TempDir:
    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp())
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        shutil.rmtree(self.path, ignore_errors=True)
