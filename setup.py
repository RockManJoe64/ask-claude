# /// script
# requires-python = ">=3.11"
# dependencies = ["questionary", "rich"]
# ///

"""askclaude interactive configuration."""

import argparse
import os
import re
import sys


def parse_existing_config(config_file: str) -> dict:
    """Parse existing shell export config into a dict of key->value."""
    config = {}
    if not os.path.exists(config_file):
        return config
    with open(config_file) as f:
        for line in f:
            m = re.match(r'^export\s+(\w+)="([^"]*)"', line.strip())
            if m:
                config[m.group(1)] = m.group(2)
    return config


def write_config(config_file: str, values: dict) -> None:
    """Write shell export statements to the config file."""
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    lines = [
        "# askclaude configuration",
        "# Edit this file to change defaults. Re-run setup.py to reconfigure.",
        f'export ASK_CLAUDE_PROVIDER="{values["provider"]}"',
        f'export ASK_CLAUDE_MODEL="{values["model"]}"',
        f'export ASK_CLAUDE_OUTPUT="{values["output"]}"',
    ]
    if values["provider"] == "anthropic":
        lines.append(f'export ASK_CLAUDE_API_KEY="{values["api_key"]}"')
    else:
        lines.append(f'export ASK_CLAUDE_BEDROCK_API_KEY="{values["bedrock_api_key"]}"')
        lines.append(f'export ASK_CLAUDE_AWS_REGION="{values["aws_region"]}"')
    if values.get("system"):
        lines.append(f'export ASK_CLAUDE_SYSTEM="{values["system"]}"')
    # zsh: prevent glob expansion on natural-language arguments (?, *, etc.)
    lines.append('[ -n "${ZSH_VERSION:-}" ] && alias askclaude=\'noglob askclaude\'')
    with open(config_file, "w") as f:
        f.write("\n".join(lines) + "\n")


def _ensure_tty() -> None:
    """Reopen stdin from /dev/tty if it isn't a terminal.

    When the installer is piped (curl … | sh), fd 0 is the pipe and
    prompt_toolkit / questionary refuse to run.  Replacing fd 0 with
    /dev/tty at the OS level makes them see a real terminal.
    """
    if not os.isatty(sys.stdin.fileno()):
        tty_path = "CONIN$" if sys.platform == "win32" else "/dev/tty"
        tty_fd = os.open(tty_path, os.O_RDONLY)
        os.dup2(tty_fd, 0)
        os.close(tty_fd)
        sys.stdin = os.fdopen(0, "r")


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure askclaude interactively.")
    parser.add_argument("--config-file", default=os.path.expanduser("~/.config/askclaude/config"))
    args = parser.parse_args()

    _ensure_tty()

    import questionary
    from rich.console import Console
    from rich.text import Text

    console = Console()

    # Load existing config as defaults
    existing = parse_existing_config(args.config_file)
    has_existing = bool(existing)

    # Header
    console.print()
    title = Text()
    title.append("  askclaude  ", style="bold white on blue")
    title.append("  Configuration", style="bold")
    console.print(title)
    console.print()
    if has_existing:
        console.print("  [dim]Existing configuration found — press Enter to keep current values.[/dim]")
        console.print()

    # Provider
    current_provider = existing.get("ASK_CLAUDE_PROVIDER", "anthropic")
    provider = questionary.select(
        "Provider:",
        choices=["anthropic", "bedrock"],
        default=current_provider if current_provider in ("anthropic", "bedrock") else "anthropic",
    ).ask()
    if provider is None:
        sys.exit(0)

    # Credentials
    api_key = ""
    bedrock_api_key = ""
    aws_region = "us-west-2"

    if provider == "anthropic":
        existing_key = existing.get("ASK_CLAUDE_API_KEY", "")
        if existing_key:
            keep = questionary.confirm(
                "Keep existing Anthropic API key?",
                default=True,
            ).ask()
            if keep is None:
                sys.exit(0)
            if keep:
                api_key = existing_key
            else:
                api_key = questionary.password("Anthropic API key:").ask()
                if not api_key:
                    console.print("[red]API key is required.[/red]")
                    sys.exit(1)
        else:
            api_key = questionary.password("Anthropic API key:").ask()
            if not api_key:
                console.print("[red]API key is required.[/red]")
                sys.exit(1)
    else:
        existing_bedrock_key = existing.get("ASK_CLAUDE_BEDROCK_API_KEY", "")
        if existing_bedrock_key:
            keep = questionary.confirm(
                "Keep existing Bedrock API key?",
                default=True,
            ).ask()
            if keep is None:
                sys.exit(0)
            if keep:
                bedrock_api_key = existing_bedrock_key
            else:
                bedrock_api_key = questionary.password("Bedrock API key:").ask()
                if not bedrock_api_key:
                    console.print("[red]Bedrock API key is required.[/red]")
                    sys.exit(1)
        else:
            bedrock_api_key = questionary.password("Bedrock API key:").ask()
            if not bedrock_api_key:
                console.print("[red]Bedrock API key is required.[/red]")
                sys.exit(1)

        current_region = existing.get("ASK_CLAUDE_AWS_REGION", "us-west-2")
        aws_region = questionary.text(
            "AWS region:",
            default=current_region,
        ).ask()
        if aws_region is None:
            sys.exit(0)

    # Model
    tier_map = {"sonnet": "Sonnet", "opus": "Opus", "haiku": "Haiku"}
    reverse_map = {"Sonnet": "sonnet", "Opus": "opus", "Haiku": "haiku"}
    current_tier = existing.get("ASK_CLAUDE_MODEL", "sonnet")
    current_choice = tier_map.get(current_tier, "Sonnet")
    model_choice = questionary.select(
        "Model:",
        choices=["Sonnet", "Opus", "Haiku"],
        default=current_choice,
    ).ask()
    if model_choice is None:
        sys.exit(0)
    model = reverse_map[model_choice]

    # System prompt
    current_system = existing.get("ASK_CLAUDE_SYSTEM", "")
    system_prompt = questionary.text(
        "System prompt (optional, press Enter to skip):",
        default=current_system,
    ).ask()
    if system_prompt is None:
        sys.exit(0)

    # Output mode
    current_output = existing.get("ASK_CLAUDE_OUTPUT", "stream+markdown")
    output = questionary.select(
        "Output mode:",
        choices=["stream+markdown", "stream", "plain"],
        default=current_output if current_output in ("stream+markdown", "stream", "plain") else "stream+markdown",
    ).ask()
    if output is None:
        sys.exit(0)

    # Write config
    write_config(
        args.config_file,
        {
            "provider": provider,
            "api_key": api_key,
            "bedrock_api_key": bedrock_api_key,
            "aws_region": aws_region,
            "model": model,
            "system": system_prompt,
            "output": output,
        },
    )

    console.print()
    console.print(f"  [green]Config written to[/green] {args.config_file}")
    console.print()


if __name__ == "__main__":
    main()
