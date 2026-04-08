#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch codex mcp-server without API-key env vars.")
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print a JSON config snippet for local MCP clients and exit.",
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run the MCP server in the foreground instead of detaching.",
    )
    parser.add_argument(
        "--log-file",
        default="codex-mcp-server.log",
        help="Log file used when running in detached mode.",
    )
    return parser


def sanitized_env() -> dict:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    return env


def main() -> int:
    args = build_arg_parser().parse_args()

    if args.print_config:
        payload = {
            "mcpServers": {
                "codex": {
                    "command": "codex",
                    "args": ["mcp-server"],
                    "env": {
                        "OPENAI_API_KEY": "",
                        "CODEX_API_KEY": "",
                    },
                }
            }
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.foreground:
        return subprocess.call(["codex", "mcp-server"], env=sanitized_env())

    log_path = Path(args.log_file).resolve()
    with log_path.open("a", encoding="utf-8") as handle:
        process = subprocess.Popen(
            ["codex", "mcp-server"],
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=handle,
            env=sanitized_env(),
        )
    print("Started codex mcp-server with pid {}".format(process.pid))
    print("Log file: {}".format(log_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
