"""``python -m scripts`` -> the repo tooling CLI (prints help without args)."""

import sys

from scripts.cli import app


def main() -> None:
    # No args -> print the Typer help with a clean exit code 0.
    app(args=sys.argv[1:] or ["--help"], prog_name="python -m scripts")


if __name__ == "__main__":
    main()
