# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic", "rich"]
# ///

"""ask-claude: Query Claude from your terminal."""

import os
import sys


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


def main() -> None:
    pass


if __name__ == "__main__":
    main()
