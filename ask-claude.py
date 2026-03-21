# /// script
# requires-python = ">=3.11"
# dependencies = ["anthropic[bedrock]", "rich"]
# ///

"""ask-claude: Query Claude from your terminal."""

import argparse
import os
import sys
from typing import Iterator, Optional


VALID_MODES = ("plain", "stream", "stream+markdown")


def load_config() -> dict:
    provider = os.environ.get("ASK_CLAUDE_PROVIDER", "direct")
    if provider not in ("direct", "bedrock"):
        print(
            "Error: ASK_CLAUDE_PROVIDER must be 'direct' or 'bedrock'.",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = None
    bedrock_api_key = None

    if provider == "direct":
        api_key = os.environ.get("ASK_CLAUDE_API_KEY")
        if not api_key:
            print(
                "Error: ASK_CLAUDE_API_KEY is not set. Run install.sh or set it manually.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        bedrock_api_key = os.environ.get("ASK_CLAUDE_BEDROCK_API_KEY")
        if not bedrock_api_key:
            print(
                "Error: ASK_CLAUDE_BEDROCK_API_KEY is not set. Run install.sh or set it manually.",
                file=sys.stderr,
            )
            sys.exit(1)

    default_model = (
        "claude-sonnet-4-6" if provider == "direct" else "us.anthropic.claude-sonnet-4-6"
    )
    aws_region = (
        os.environ.get("ASK_CLAUDE_AWS_REGION")
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-west-2"
    )

    return {
        "provider": provider,
        "api_key": api_key,
        "bedrock_api_key": bedrock_api_key,
        "model": os.environ.get("ASK_CLAUDE_MODEL", default_model),
        "system": os.environ.get("ASK_CLAUDE_SYSTEM") or None,
        "max_tokens": int(os.environ.get("ASK_CLAUDE_MAX_TOKENS", "8096")),
        "output": os.environ.get("ASK_CLAUDE_OUTPUT", "stream+markdown"),
        "aws_region": aws_region,
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


def build_client(config: dict):
    """Construct the appropriate Anthropic client based on provider."""
    import anthropic

    if config["provider"] == "direct":
        return anthropic.Anthropic(api_key=config["api_key"])
    else:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = config["bedrock_api_key"]
        return anthropic.AnthropicBedrock(aws_region=config["aws_region"])


def _extract_text_events(stream: Iterator) -> Iterator[str]:
    """Yield text strings from Anthropic streaming events."""
    for event in stream:
        if (
            event.type == "content_block_delta"
            and event.delta.type == "text_delta"
        ):
            yield event.delta.text


def render_plain(stream: Iterator) -> str:
    """Buffer all tokens, return and print as plain text."""
    full_text = "".join(_extract_text_events(stream))
    print(full_text)
    return full_text


def render_stream(stream: Iterator) -> str:
    """Print tokens to stdout as they arrive."""
    parts = []
    for token in _extract_text_events(stream):
        print(token, end="", flush=True)
        parts.append(token)
    print()  # trailing newline
    return "".join(parts)


def render_stream_markdown(stream: Iterator) -> str:
    """Stream tokens, then re-render full response with rich markdown."""
    from rich.console import Console
    from rich.markdown import Markdown

    parts = []
    for token in _extract_text_events(stream):
        print(token, end="", flush=True)
        parts.append(token)
    full_text = "".join(parts)
    print("\r", end="")  # return to start of line before re-render
    console = Console()
    console.print(Markdown(full_text))
    return full_text


def _handle_api_error(e: Exception) -> None:
    print(f"\nError: {e}", file=sys.stderr)
    sys.exit(1)


def run_single_shot(prompt: str, config: dict, output_mode: str) -> None:
    import anthropic  # needed for error types in except clause
    client = build_client(config)

    stream_kwargs = dict(
        model=config["model"],
        max_tokens=config["max_tokens"],
        messages=[{"role": "user", "content": prompt}],
    )
    if config["system"]:
        stream_kwargs["system"] = config["system"]

    try:
        with client.messages.stream(**stream_kwargs) as stream:
            if output_mode == "plain":
                render_plain(stream)
            elif output_mode == "stream":
                render_stream(stream)
            else:
                render_stream_markdown(stream)
    except (anthropic.AuthenticationError, anthropic.APIStatusError) as e:
        _handle_api_error(e)


def run_repl(config: dict, output_mode: str) -> None:
    import anthropic  # needed for error types in except clause
    history: list[dict] = []

    print("Claude REPL — type /exit or /quit to exit.\n")

    client = None

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input in ("/exit", "/quit"):
            print("Goodbye.")
            break

        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        if client is None:
            client = build_client(config)

        stream_kwargs = dict(
            model=config["model"],
            max_tokens=config["max_tokens"],
            messages=history,
        )
        if config["system"]:
            stream_kwargs["system"] = config["system"]

        response_text = ""
        try:
            with client.messages.stream(**stream_kwargs) as stream:
                if output_mode == "plain":
                    response_text = render_plain(stream)
                elif output_mode == "stream":
                    response_text = render_stream(stream)
                else:
                    response_text = render_stream_markdown(stream)
        except (anthropic.AuthenticationError, anthropic.APIStatusError) as e:
            _handle_api_error(e)

        history.append({"role": "assistant", "content": response_text})


def main() -> None:
    config = load_config()
    args = parse_args()
    output_mode = resolve_output_mode(args.mode, config["output"])

    if args.prompt:
        run_single_shot(args.prompt, config, output_mode)
    else:
        run_repl(config, output_mode)


if __name__ == "__main__":
    main()
