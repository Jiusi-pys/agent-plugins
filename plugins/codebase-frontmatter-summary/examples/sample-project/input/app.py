"""Serve a small greeting for the example project."""

class Greeter:
    def format_name(self, name: str) -> str:
        return f"Hello, {name}!"


def main() -> None:
    print(Greeter().format_name("Codex"))


if __name__ == "__main__":
    main()
