# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic", "rich"]
# ///

"""ask-claude: Query Claude from your terminal."""

import argparse
import os
import sys
from typing import Optional


VALID_MODES = ("plain", "stream", "stream+markdown")


def load_config() -> dict:
    api_key = os.environ.get("ASK_CLAUDE_API_KEY")
    if not api_key:
        print(
            "Error: ASK_CLAUDE_API_KEY is not set. Run install.sh or set it manually.",
            file=sys.stderr,
        )
        sys.exit(1)
    return {
        "api_key": api_key,
        "model": os.environ.get("ASK_CLAUDE_MODEL", "claude-sonnet-4-6"),
        "system": os.environ.get("ASK_CLAUDE_SYSTEM") or None,
        "max_tokens": int(os.environ.get("ASK_CLAUDE_MAX_TOKENS", "8096")),
        "output": os.environ.get("ASK_CLAUDE_OUTPUT", "stream+markdown"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ask-claude",
        description="Query Claude from your terminal.",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=VALID_MODES,
        default=None,
        help="Output mode: plain, stream, or stream+markdown",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Prompt for single-shot mode. Omit to start REPL.",
    )
    return parser.parse_args(argv)


def resolve_output_mode(cli_mode: Optional[str], env_mode: Optional[str]) -> str:
    return cli_mode or env_mode or "stream+markdown"


def main() -> None:
    pass


if __name__ == "__main__":
    main()
