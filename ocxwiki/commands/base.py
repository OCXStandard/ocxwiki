from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

from loguru import logger
import typer
from typer.testing import CliRunner

if TYPE_CHECKING:
    from ocxwiki.app import CLIApp


@dataclass
class DispatchResult:
    exit_code: int
    stdout: str
    stderr: str
    help_text: str


async def dispatch_typer_command(
    app: typer.Typer,
    args: Sequence[str],
    confirm_callback: Optional[Callable[[str], bool]] = None,
    progress_callback: Optional[Callable] = None,
    summary_callback: Optional[Callable] = None,
) -> DispatchResult:
    """
    Dispatch a Typer command asynchronously using CliRunner.

    The shared ``WikiManager`` singleton is always injected into *ctx.obj* so
    that every command—regardless of invocation order—operates on the same
    instance (same connection, same processed schema, same state).

    Args:
        app: The Typer application instance
        args: Command arguments to pass (e.g., ["wiki", "connect", "--user", "me"])
        confirm_callback: Optional callable that receives a confirmation message and
            returns ``True``/``False``.  When provided it is injected into
            ``ctx.obj['confirm_callback']`` so that :func:`wiki_cli.wiki_confirm`
            can use it instead of blocking on ``typer.confirm``.
        progress_callback: Optional callable(advance, total, description) injected into
            ``ctx.obj['progress_callback']``.  Commands call it after each published item
            so the TUI progress bar can be updated.  ``advance=0`` with a non-None
            ``total`` signals the grand total at the start of the operation.
        summary_callback: Optional callable(text) injected into
            ``ctx.obj['summary_callback']``.  Commands call it with a final summary
            string when the operation is complete so the TUI can display it.

    Returns:
        DispatchResult containing exit code, stdout, stderr, and help text
    """
    # Import here to avoid circular imports at module load time.
    from ocxwiki.wiki_cli import get_wiki_manager  # noqa: PLC0415

    runner = CliRunner()

    def _build_obj(base_obj: dict | None) -> dict:
        obj = dict(base_obj) if base_obj else {}
        # Always inject the shared singleton so every CliRunner invocation
        # sees the same WikiManager (connection + processed schema are preserved).
        obj.setdefault('wiki_manager', get_wiki_manager())
        if confirm_callback is not None:
            obj['confirm_callback'] = confirm_callback
        if progress_callback is not None:
            obj['progress_callback'] = progress_callback
        if summary_callback is not None:
            obj['summary_callback'] = summary_callback
        return obj

    def _invoke(argv: list[str]):
        logger.debug(f"Invoking with argv: {argv}")
        obj = _build_obj(None)
        logger.debug(
            f"Invoking with wiki_manager id={id(obj['wiki_manager'])}, "
            f"connected={obj['wiki_manager']._client.is_connected()}, "
            f"has_transformer={obj['wiki_manager'].transformer is not None}"
        )
        result = runner.invoke(app, argv, catch_exceptions=True, obj=obj)
        logger.debug(f"Result: exit_code={result.exit_code}")
        if result.exception:
            logger.error(f"Exception during invoke: {result.exception}")
        if not result.stdout and not result.stderr and result.exit_code != 0:
            logger.warning(f"Command failed silently: exit_code={result.exit_code}")
        return result

    try:
        result = await asyncio.to_thread(_invoke, list(args))

        logger.debug(
            f"Command result: exit_code={result.exit_code}, "
            f"stdout_len={len(result.stdout)}, "
            f"stderr_len={len(result.stderr) if result.stderr else 0}"
        )

        help_text = ""
        if "--help" in args:
            help_text = result.stdout
            logger.debug(f"Help requested, help_text length: {len(help_text)}")
        elif result.exit_code != 0 and not result.stdout and not result.stderr:
            help_result = await asyncio.to_thread(_invoke, list(args) + ["--help"])
            help_text = help_result.stdout
            logger.debug(f"Command failed, fetched help_text length: {len(help_text)}")

        return DispatchResult(
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr or "",
            help_text=help_text,
        )
    except Exception as e:
        logger.exception(f"Error dispatching command: {e}")
        return DispatchResult(
            exit_code=1,
            stdout="",
            stderr=f"Command execution failed: {str(e)}",
            help_text="",
        )


class Command:
    """Represents a CLI command."""

    def __init__(
        self,
        name: str,
        description: str,
        typer_command=None,
        is_group: bool = False,
        parent: str = None,
        params: list = None,
    ):
        self.name = name
        self.description = description
        self._typer_command = typer_command
        self.is_group = is_group
        self.parent = parent
        self.params = params or []

    async def execute(self, app: CLIApp, args: list[str]) -> None:
        """Execute the command via Typer dispatch."""
        if self._typer_command:
            # For subcommands (e.g., "serialize excel"), split the name
            cmd_parts = self.name.split()

            # Combine command parts with any additional arguments
            full_args = cmd_parts + args

            # Execute through the Typer CLI
            result = await dispatch_typer_command(app.typer_cli, full_args)

            if result.stdout:
                app.add_output(result.stdout)
            if result.stderr:
                app.add_output(f"[red]Error:[/red] {result.stderr}")
            if result.exit_code != 0 and not result.stdout and not result.stderr:
                # Show help if command failed silently
                app.add_output(result.help_text)
        else:
            app.add_output("[yellow]Command not implemented[/yellow]")
