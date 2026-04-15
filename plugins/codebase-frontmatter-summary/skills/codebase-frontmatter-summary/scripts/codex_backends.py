#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import queue
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DEFAULT_BACKEND = "sdk"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_MODEL_REASONING_EFFORT = "xhigh"


class JsonRpcError(RuntimeError):
    def __init__(self, error: Dict[str, Any]) -> None:
        self.error = error
        code = error.get("code", "unknown")
        message = error.get("message", "unknown error")
        super().__init__(f"JSON-RPC error {code}: {message}")


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

    def last_stderr_lines(self) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                lines.append(self._stderr_lines.get_nowait())
            except queue.Empty:
                break
        return lines

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    def notify(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        self._stdin.write(json.dumps(payload) + "\n")
        self._stdin.flush()

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(f"Codex MCP tool returned error: {result}")
        return result


def clean_child_env() -> Dict[str, str]:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    return env


def extract_text_from_tool_result(result: Dict[str, Any]) -> str:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        content = structured.get("content")
        if isinstance(content, str):
            return content

    content = result.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
            elif isinstance(item, str):
                chunks.append(item)
        if chunks:
            return "".join(chunks)
    raise RuntimeError(f"Codex MCP tool result did not include text content: {result}")


def parse_json_output(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError(f"Unable to parse JSON from Codex output:\n{text}")


def run_json_via_codex_mcp(
    prompt: str,
    *,
    working_dir: Path,
    model: Optional[str] = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_MODEL_REASONING_EFFORT,
) -> Dict[str, Any]:
    command = ["codex", "mcp-server"]
    with CodexMcpClient(command, cwd=working_dir, env=clean_child_env()) as client:
        client.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "codebase-frontmatter-summary", "version": "1.0"},
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
                "config": {"model_reasoning_effort": reasoning_effort},
            },
        )
        return parse_json_output(extract_text_from_tool_result(tool_result))


def run_json_via_sdk_bridge(
    prompt: str,
    *,
    output_schema: Dict[str, Any],
    sdk_bridge: Path,
    working_dir: Path,
    model: Optional[str] = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_MODEL_REASONING_EFFORT,
) -> Dict[str, Any]:
    if not sdk_bridge.exists():
        raise FileNotFoundError(f"SDK bridge not found: {sdk_bridge}")

    payload = {
        "prompt": prompt,
        "outputSchema": output_schema,
        "workingDirectory": str(working_dir),
        "model": model,
        "reasoningEffort": reasoning_effort,
    }
    completed = subprocess.run(
        ["node", str(sdk_bridge)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=clean_child_env(),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "SDK bridge failed with code {}:\n{}\n{}".format(
                completed.returncode, completed.stdout, completed.stderr
            )
        )
    response = json.loads(completed.stdout)
    final_response = response.get("finalResponse")
    if not isinstance(final_response, dict):
        raise RuntimeError(f"Unexpected SDK bridge response: {response}")
    return final_response


def run_json_via_codex_exec(
    prompt: str,
    *,
    output_schema: Dict[str, Any],
    working_dir: Path,
    model: Optional[str] = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_MODEL_REASONING_EFFORT,
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="codebase-frontmatter-") as temp_dir:
        schema_path = Path(temp_dir) / "schema.json"
        output_path = Path(temp_dir) / "final-message.json"
        schema_path.write_text(json.dumps(output_schema), encoding="utf-8")

        command = [
            "codex",
            "-c",
            f'model_reasoning_effort="{reasoning_effort}"',
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "-C",
            str(working_dir),
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
        ]
        if model:
            command.extend(["-m", model])

        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            env=clean_child_env(),
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "codex exec failed with code {}:\n{}\n{}".format(
                    completed.returncode, completed.stdout, completed.stderr
                )
            )
        return json.loads(output_path.read_text(encoding="utf-8"))


def run_json_task(
    prompt: str,
    *,
    output_schema: Dict[str, Any],
    backend: str,
    sdk_bridge: Path,
    working_dir: Path,
    model: Optional[str] = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_MODEL_REASONING_EFFORT,
) -> Dict[str, Any]:
    if backend == "mcp":
        return run_json_via_codex_mcp(
            prompt,
            working_dir=working_dir,
            model=model,
            reasoning_effort=reasoning_effort,
        )
    if backend == "sdk":
        return run_json_via_sdk_bridge(
            prompt,
            output_schema=output_schema,
            sdk_bridge=sdk_bridge,
            working_dir=working_dir,
            model=model,
            reasoning_effort=reasoning_effort,
        )
    if backend == "exec":
        return run_json_via_codex_exec(
            prompt,
            output_schema=output_schema,
            working_dir=working_dir,
            model=model,
            reasoning_effort=reasoning_effort,
        )
    if backend != "auto":
        raise ValueError(f"unsupported backend: {backend}")

    failures: list[str] = []
    for candidate in ("mcp", "sdk", "exec"):
        try:
            return run_json_task(
                prompt,
                output_schema=output_schema,
                backend=candidate,
                sdk_bridge=sdk_bridge,
                working_dir=working_dir,
                model=model,
                reasoning_effort=reasoning_effort,
            )
        except Exception as exc:
            failures.append(f"{candidate}: {exc}")
    raise RuntimeError("All Codex backends failed:\n" + "\n".join(failures))
