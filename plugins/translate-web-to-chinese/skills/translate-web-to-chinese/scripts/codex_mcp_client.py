#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Dict, Iterable, Optional


class JsonRpcError(RuntimeError):
    def __init__(self, error: Dict):
        self.error = error
        code = error.get("code", "unknown")
        message = error.get("message", "unknown error")
        super().__init__("JSON-RPC error {}: {}".format(code, message))


class CodexMcpClient:
    def __init__(
        self,
        command: Iterable[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        self._next_id = 0
        self._stderr_lines: "queue.Queue[str]" = queue.Queue()
        self._proc = subprocess.Popen(
            list(command),
            cwd=str(cwd) if cwd else None,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if self._proc.stdin is None or self._proc.stdout is None or self._proc.stderr is None:
            raise RuntimeError("Failed to open Codex MCP pipes")
        self._stdin = self._proc.stdin
        self._stdout = self._proc.stdout
        self._stderr = self._proc.stderr
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    def _drain_stderr(self) -> None:
        for line in self._stderr:
            self._stderr_lines.put(line.rstrip())

    def close(self) -> None:
        if self._proc.poll() is None:
            self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=5)

    def __enter__(self) -> "CodexMcpClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def last_stderr_lines(self) -> list:
        lines = []
        while True:
            try:
                lines.append(self._stderr_lines.get_nowait())
            except queue.Empty:
                break
        return lines

    def request(self, method: str, params: Optional[Dict] = None) -> Dict:
        self._next_id += 1
        request_id = self._next_id
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        self._stdin.write(json.dumps(payload) + "\n")
        self._stdin.flush()

        while True:
            line = self._stdout.readline()
            if not line:
                stderr = "\n".join(self.last_stderr_lines())
                raise RuntimeError(
                    "Codex MCP server closed the stream unexpectedly{}".format(
                        f": {stderr}" if stderr else ""
                    )
                )
            message = json.loads(line)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise JsonRpcError(message["error"])
            return message.get("result") or {}

    def notify(self, method: str, params: Optional[Dict] = None) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        self._stdin.write(json.dumps(payload) + "\n")
        self._stdin.flush()

    def call_tool(self, name: str, arguments: Dict) -> Dict:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError("Codex MCP tool returned error: {}".format(result))
        return result


def clean_env() -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    return env


def extract_text_from_tool_result(result: Dict) -> str:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        content = structured.get("content")
        if isinstance(content, str):
            return content

    content = result.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
            elif isinstance(item, str):
                chunks.append(item)
        if chunks:
            return "".join(chunks)
    raise RuntimeError("Codex MCP tool result did not include text content: {}".format(result))


def run_translation_via_codex_mcp(
    prompt: str,
    working_dir: Path,
    model: Optional[str] = None,
) -> Dict[str, str]:
    command = ["codex", "mcp-server"]
    with CodexMcpClient(command, cwd=working_dir, env=clean_env()) as client:
        client.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "translate-web-to-chinese", "version": "1.0"},
            },
        )
        client.notify("notifications/initialized", {})
        tool_result = client.call_tool(
            "codex",
            {
                "prompt": prompt,
                "approval-policy": "never",
                "sandbox": "workspace-write",
                "cwd": str(working_dir),
                "model": model,
            },
        )
        text = extract_text_from_tool_result(tool_result)
        return json.loads(text)
