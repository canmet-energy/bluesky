"""Main CLI entry point for Bluesky application."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pyfiglet import Figlet
from colorama import init

# Initialize colorama for cross-platform color support
init(autoreset=True)

console = Console()


@click.command()
@click.option(
    "--name",
    default="World",
    help="Name to greet",
    show_default=True,
)
@click.option(
    "--fancy",
    is_flag=True,
    help="Show fancy ASCII art greeting",
)
@click.option(
    "--color",
    default="cyan",
    type=click.Choice(["cyan", "green", "yellow", "red", "magenta"]),
    help="Color for the fancy greeting",
)
@click.version_option(version="0.1.0", prog_name="bluesky")
def main(name: str, fancy: bool, color: str) -> None:
    """Bluesky - A simple hello world application with style!"""

    if fancy:
        # Create ASCII art
        fig = Figlet(font='slant')
        ascii_art = fig.renderText('Bluesky')

        # Create greeting message
        greeting = f"Hello, {name}!"

        # Display with Rich
        console.print(Panel.fit(
            Text(ascii_art, style=f"bold {color}"),
            title="[bold blue]Welcome to Bluesky[/bold blue]",
            border_style="blue",
        ))
        console.print(
            Panel(
                greeting,
                title="Greeting",
                border_style=color,
                padding=(1, 2),
            )
        )
        console.print(f"\n[dim]Version: 0.1.0[/dim]")
    else:
        # Simple greeting
        console.print(f"[bold {color}]Hello, {name}![/bold {color}]")
        console.print("[dim]Welcome to Bluesky![/dim]")


if __name__ == "__main__":
    main()