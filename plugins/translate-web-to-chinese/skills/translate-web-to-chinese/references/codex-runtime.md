# Codex Runtime Notes

Use this reference when adjusting the translation backend or auth behavior.

## What the current OpenAI docs show

- The official Codex SDK page documents a TypeScript package: `@openai/codex-sdk`.
- The local Codex CLI supports `codex exec` for non-interactive runs and `codex mcp-server` for exposing Codex as an MCP server over stdio.
- The non-interactive CLI supports `--output-schema`, which is the most reliable local way to force structured JSON for page-by-page translation.

Official references:

- https://developers.openai.com/codex/sdk
- https://developers.openai.com/codex/noninteractive
- `codex --help`
- `codex exec --help`
- `codex mcp-server --help`

## Practical implication for this skill

- Keep the orchestration layer in Python.
- Prefer `translate_site.py --backend auto`.
- `auto` first tries the local `codex mcp-server` path, then `scripts/codex_sdk_bridge.mjs`, then `codex exec`.
- Use `codex exec` only as the last fallback, because the MCP path is the primary requirement for this skill.

## Auth rule

- Do not pass `OPENAI_API_KEY`.
- Do not pass `CODEX_API_KEY`.
- Use the user's existing `codex login` session instead.
- The helper scripts strip both env vars before they launch Codex child processes.
- If the user is not logged in, stop and ask them to run `codex login`.

## MCP export

Use `scripts/codex_mcp_client.py` when the translation run needs to talk to the live Codex MCP server.
Use `scripts/start_codex_mcp.py --print-config` to print a local MCP config snippet.
Use `scripts/start_codex_mcp.py --foreground` to run `codex mcp-server` directly without exposing API-key env vars.
