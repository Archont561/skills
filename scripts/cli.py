"""Repo tooling entry point: ``python -m scripts.cli <command> [...]``.

Commands are plugins: every ``*.py`` module in ``scripts/commands/`` is loaded
automatically. A module must expose either

- ``command``: a plain function -> mounted as a top-level command named after
  the module (``lint.py`` -> ``... cli lint``), or
- ``app``: a ``typer.Typer`` instance -> mounted as a command group named
  after the module.

Modules prefixed with ``_`` are skipped.
"""

import importlib
import pkgutil

import typer

app = typer.Typer(help="Repo tooling for this skills registry.", no_args_is_help=True)


@app.callback()
def callback() -> None:
    """Repo tooling for this skills registry.

    (Presence of a callback keeps Typer in group mode even when exactly one
    command is registered, so `python -m scripts` always prints help.)
    """


def _load_commands() -> None:
    package = importlib.import_module("scripts.commands")
    for info in pkgutil.iter_modules(package.__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{package.__name__}.{info.name}")
        name = info.name.replace("_", "-")
        if isinstance(getattr(module, "app", None), typer.Typer):
            app.add_typer(module.app, name=name)
        elif callable(getattr(module, "command", None)):
            app.command(name=name)(module.command)


_load_commands()

if __name__ == "__main__":
    app()
