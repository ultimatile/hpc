"""HPC CLI entry point"""

import typer
from click import Argument, Option

app = typer.Typer(help="HPC job execution support tool")


def _generate_skill_reference(cli_app: typer.Typer) -> str:
    """Generate markdown CLI reference from Typer app metadata for use in SKILL.md."""
    click_app = typer.main.get_command(cli_app)
    lines = ["## Commands", ""]
    for name, cmd in sorted(click_app.commands.items()):
        lines.append(f"### `hpc {name}`")
        if cmd.help:
            lines.append(cmd.help)
        params = [p for p in cmd.params if not isinstance(p, Argument) or p.required]
        args = [p for p in params if isinstance(p, Argument)]
        opts = [p for p in params if isinstance(p, Option) and p.name != "help"]
        if args:
            for arg in args:
                type_name = arg.type.name.upper() if arg.type else ""
                required = " (required)" if arg.required else ""
                lines.append(f"- Argument: `{arg.human_readable_name}` {type_name}{required}")
        if opts:
            for opt in opts:
                decls = ", ".join(f"`{d}`" for d in opt.opts)
                help_text = f": {opt.help}" if opt.help else ""
                lines.append(f"- {decls}{help_text}")
        lines.append("")
    return "\n".join(lines)


def _skill_callback(value: bool):
    """Print CLI reference for SKILL.md and exit."""
    if not value:
        return
    from . import cli  # noqa: F401 - register commands

    print(_generate_skill_reference(app))
    raise typer.Exit()


@app.callback()
def app_callback(
    skill: bool = typer.Option(
        False, "--skill", hidden=True, callback=_skill_callback, is_eager=True,
        help="Print CLI reference for SKILL.md",
    ),
):
    pass


def main():
    from . import cli  # noqa: F401 - register commands

    app()


if __name__ == "__main__":
    main()
