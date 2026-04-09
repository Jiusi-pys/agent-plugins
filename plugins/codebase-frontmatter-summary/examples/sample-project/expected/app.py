# codex-file-meta: begin
# relative_path: "app.py"
# language: "python"
# summary: "Serve a small greeting for the example project."
# symbols: ["Greeter", "main"]
# generated_by: "codebase-frontmatter-summary"
# codex-file-meta: end

"""Serve a small greeting for the example project."""

class Greeter:
    def format_name(self, name: str) -> str:
        return f"Hello, {name}!"


def main() -> None:
    print(Greeter().format_name("Codex"))


if __name__ == "__main__":
    main()
