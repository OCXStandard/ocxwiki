#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""Schema CLI commands for processing and summarising OCX schema files."""

# Third party imports
import typer
from loguru import logger
from rich import print
from pathlib import Path
from typing_extensions import Annotated
from tabulate import tabulate

# Module imports
from ocxwiki import WORKING_DRAFT, SCHEMA_FOLDER
from ocxwiki.wiki_manager import WikiManager

schema = typer.Typer(
    help="Commands for processing and summarising OCX schema files.",
    add_completion=False,
)


def _get_wiki_manager(ctx: typer.Context) -> WikiManager:
    """Retrieve the WikiManager from the Typer context.

    Falls back to the singleton exposed by :mod:`ocxwiki.wiki_cli` so that
    state is always shared regardless of which sub-CLI dispatched the command.
    """
    from ocxwiki.wiki_cli import get_wiki_manager
    return (ctx.obj or {}).get('wiki_manager') or get_wiki_manager()


@schema.callback()
def schema_callback(ctx: typer.Context):
    """Schema commands – process and inspect OCX schema files."""
    if ctx.obj is None:
        ctx.obj = {}
    if 'wiki_manager' not in ctx.obj:
        from ocxwiki.wiki_cli import get_wiki_manager
        ctx.obj['wiki_manager'] = get_wiki_manager()
    logger.debug(
        f"schema callback: wiki_manager id={id(ctx.obj['wiki_manager'])}, "
        f"has_transformer={ctx.obj['wiki_manager'].transformer is not None}"
    )


@schema.command()
def process_url(
        ctx: typer.Context,
        url: Annotated[str, typer.Option(
            help='Process a schema URL for publishing.',
            prompt=True,
        )] = WORKING_DRAFT,
        folder: Annotated[Path, typer.Option(
            help='The schema download folder.',
        )] = Path(SCHEMA_FOLDER),
):
    """Download and process a schema from a URL before publishing."""
    wiki_manager = _get_wiki_manager(ctx)
    if wiki_manager:
        if wiki_manager.process_schema(url, folder):
            summary(ctx)


@schema.command()
def process_folder(
        ctx: typer.Context,
        folder: Annotated[Path, typer.Option(
            help='The folder containing the schema files.',
            prompt=True,
        )] = Path(SCHEMA_FOLDER),
):
    """Process a schema from a local folder before publishing."""
    wiki_manager = _get_wiki_manager(ctx)
    if wiki_manager:
        result = wiki_manager.process_schema_folder(folder)
        if result:
            summary(ctx)


@schema.command()
def element_table(
        ctx: typer.Context,

        name: Annotated[str, typer.Option(
            help='Filter by OCX element name (case-insensitive substring match).'
        )] = '',
):
    """Print the global schema element as a Rich table in the terminal.

    Iterates over all global attributes in the processed schema and renders
    each one as a formatted Rich table using :class:`RichRender`.  Mirrors
    the iteration logic of :func:`~ocxwiki.wiki_cli.publish_attributes` but
    outputs to the terminal instead of publishing to the wiki.
    """
    wiki_manager = _get_wiki_manager(ctx)
    if wiki_manager.transformer is None:
        print('[bold red]No schema processed.[/bold red] Run [bold]schema process-url[/bold] first.')
        return

    elements = wiki_manager.transformer.get_ocx_elements()
    if not elements:
        print('[yellow]No global OCX elements found in the processed schema.[/yellow]')
        return

    # Apply name filter
    filter_str = name.lower()
    filtered = [a for a in elements if filter_str in a.get_name().lower()] if filter_str else elements

    if not filtered:
        print(f'[yellow]No OCX elements matching [bold]{name}[/bold] found.[/yellow]')
        return

    version = wiki_manager.transformer.parser.get_schema_version()
    print(f'[bold cyan]Global schema elements[/bold cyan] ({len(filtered)} of {len(elements)} total) – schema v{version}\n')
    for ocx in filtered:
        print(f'[bold magenta]{ocx.get_name()}[/bold magenta]')
        annotation = ocx.get_annotation()
        if annotation:
            print(annotation)
        children = ocx.children_to_dict()
        if children:
            print(f'  [bold]Child elements:[/bold]')
            print(children)
        attrs = ocx.attributes_to_dict()
        if attrs:
            print(f'  [bold]Attributes:[/bold]')
            print(attrs)
        print()



@schema.command()
def summary(ctx: typer.Context):
    """Print a summary of the processed schema."""
    wiki_manager = _get_wiki_manager(ctx)
    if wiki_manager.transformer is not None:
        for ns, tbl in wiki_manager.transformer.parser.tbl_summary().items():
            print(f'Content of namespace {ns}:\n')
            print(tabulate(tbl, headers='keys'), '\n')
    else:
        print('Process a schema first')

