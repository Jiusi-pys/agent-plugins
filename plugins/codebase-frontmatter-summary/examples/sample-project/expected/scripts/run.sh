#!/usr/bin/env bash
# codex-file-meta: begin
# relative_path: "scripts/run.sh"
# language: "shell"
# summary: "Shell script defining `say_hello`, and `main`."
# symbols: ["say_hello", "main"]
# generated_by: "codebase-frontmatter-summary"
# codex-file-meta: end

say_hello() {
  echo "hello from the sample project"
}

main() {
  say_hello
}

main "$@"
