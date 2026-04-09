#!/usr/bin/env node
import process from "node:process";

let Codex;
try {
  ({ Codex } = await import("@openai/codex-sdk"));
} catch (error) {
  console.error(
    [
      "Unable to load @openai/codex-sdk.",
      "Install it under this skill before using the SDK bridge:",
      "  npm install @openai/codex-sdk",
      "",
      `Original error: ${error.message}`,
    ].join("\n"),
  );
  process.exit(1);
}

const readStdin = async () => {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8");
};

const raw = await readStdin();
const request = JSON.parse(raw);

const env = { ...process.env };
delete env.OPENAI_API_KEY;
delete env.CODEX_API_KEY;

const codex = new Codex({ env });
const thread = codex.startThread({
  workingDirectory: request.workingDirectory,
  skipGitRepoCheck: true,
  model: request.model,
  modelReasoningEffort: request.reasoningEffort,
});

const turn = await thread.run(request.prompt, {
  outputSchema: request.outputSchema,
});

let finalResponse = turn.finalResponse;
if (typeof finalResponse === "string") {
  try {
    finalResponse = JSON.parse(finalResponse);
  } catch {
    // Keep the raw string when the SDK returns a non-JSON final response.
  }
}

process.stdout.write(
  JSON.stringify(
    {
      finalResponse,
      items: turn.items ?? [],
    },
    null,
    2,
  ),
);
