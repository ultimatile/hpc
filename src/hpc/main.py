"""HPC CLI entry point"""

import typer

app = typer.Typer(help="HPC job execution support tool")


def main():
    from . import cli  # noqa: F401 - register commands

    app()


if __name__ == "__main__":
    main()
