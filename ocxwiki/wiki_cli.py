#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""This module provides the ocxwiki app functionality."""


# Sys imports
from collections import defaultdict
# Third party imports
import arrow
import typer
from loguru import logger
from rich import print
from rich.progress import track
from typing_extensions import Annotated

# Module imports
from ocxwiki import __app_name__, __version__, WIKI_URL, USER, PSWD
from ocxwiki.wiki_manager import WikiManager, PublishState
from ocxwiki.async_helper import run_async
from tabulate import tabulate

wiki = typer.Typer()


def wiki_confirm(ctx: typer.Context, message: str) -> bool:
    """Prompt for confirmation, using the TUI callback if available.

    If ``ctx.obj`` contains a callable ``'confirm_callback'`` it is called with
    *message* and must return a bool.  This lets the Textual TUI intercept the
    confirmation and show its own dialog instead of blocking on stdin.
    Otherwise falls back to the standard :func:`typer.confirm` prompt.

    Args:
        ctx: The active Typer context.
        message: The confirmation question to show the user.

    Returns:
        ``True`` if the user confirmed, ``False`` otherwise.
    """
    confirm_cb = (ctx.obj or {}).get('confirm_callback')
    if callable(confirm_cb):
        return bool(confirm_cb(message))
    return typer.confirm(message)

# rich markup
MK_COLOR = 'blue'
MK_EMP = 'bold'
MK_ERR = 'red'

# Global singleton WikiManager instance
_wiki_manager_instance = None

def get_wiki_manager() -> WikiManager:
    """Get or create the WikiManager singleton."""
    global _wiki_manager_instance
    if _wiki_manager_instance is None:
        _wiki_manager_instance = WikiManager(WIKI_URL)
    return _wiki_manager_instance


def _get_wiki_manager(ctx: typer.Context) -> WikiManager:
    """Retrieve the WikiManager from the Typer context, falling back to the singleton.

    This is the preferred way to get the WikiManager inside a command so that
    the singleton is always returned even when *ctx.obj* has not been populated
    yet (e.g. when a CliRunner-based dispatch creates a fresh context dict).
    """
    return (ctx.obj or {}).get('wiki_manager') or get_wiki_manager()

@wiki.callback()
def main(ctx: typer.Context):
    """
    OCX Wiki CLI - Manage and publish OCX schema to Dokuwiki.
    """
    if ctx.obj is None:
        ctx.obj = {}
    # If wiki_manager was already injected by dispatch_typer_command (the common TUI path),
    # keep it as-is so state (connection, transformer) is preserved across commands.
    # Only create a new one when running outside the TUI (plain CLI invocation).
    if 'wiki_manager' not in ctx.obj:
        ctx.obj['wiki_manager'] = get_wiki_manager()
    logger.debug(
        f"wiki callback: wiki_manager id={id(ctx.obj['wiki_manager'])}, "
        f"connected={ctx.obj['wiki_manager']._client.is_connected()}, "
        f"has_transformer={ctx.obj['wiki_manager'].transformer is not None}"
    )

def markup(emphasis:str = MK_EMP, color:str = MK_COLOR) -> str:
    """Rich markup"""
    return f'[{emphasis} {color}]'

def markup_end(emphasis:str = MK_EMP, color:str = MK_COLOR) -> str:
    """Rich markup end"""
    return f'[/{emphasis} {color}]'

# def validate_ocx_callback(name: str) -> str:
#     if wiki_manager.transformer.get_ocx_element_from_type(name) is None:
#         print(f'The name {name} is not a valid schema element.')
#
#         typer.prompt(f'')


@wiki.command()
def version():
    """Print the ocxwiki CLI version."""
    print(f'The {__app_name__} version: {__version__}')

@wiki.command()
def publish_all(ctx: typer.Context):
    """Publish the complete schema to the ocxwiki."""
    wiki_manager = _get_wiki_manager(ctx)
    if wiki_manager.transformer is not None:
        wikiurl = wiki_manager._client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        version = wiki_manager.transformer.parser.get_schema_version()
        pages = len(wiki_manager.transformer.get_ocx_elements())
        pages += len(wiki_manager.transformer.get_global_attributes())
        pages += len(wiki_manager.transformer.get_simple_types())
        pages += len(wiki_manager.transformer.get_enumerators())
        msg = f'You are about to publish the schema version ' \
              f'{markup()}{version}{markup_end()}\nwith {markup()}{pages}{markup_end()} pages to namespace ' \
              f'{markup()}{namespace}{markup_end()} ' \
              f'to the ocxwiki with url {wikiurl}\n'
        print(msg)
        prompt = wiki_confirm(ctx, 'OK to proceed?')

        if prompt:
            publish_ocx(ctx, interactive=False)
            publish_simple_types(ctx, interactive=False)
            publish_attributes(ctx, interactive=False)
            publish_enums(ctx, interactive=False)
            print(f'Published in total {pages} pages.')
    else:
        print('Process a schema first')

@wiki.command()
def publish_all_async(
        ctx: typer.Context,
        max_concurrent: Annotated[int, typer.Option(
            help='Maximum number of concurrent publish operations')] = 10
):
    """Publish the complete schema to the ocxwiki using async operations for better performance."""
    wiki_manager = (ctx.obj or {}).get('wiki_manager') or get_wiki_manager()
    logger.debug(f'publish_all_async: wiki_manager={wiki_manager!r}, connected={wiki_manager._client.is_connected() if wiki_manager else False}')
    if wiki_manager is None:
        print('[bold red]Error:[/bold red] WikiManager not available. Please restart the application.')
        return
    if not wiki_manager._client.is_connected():
        print('[bold red]Error:[/bold red] Not connected to the wiki. Please run [bold]wiki connect[/bold] first.')
        return
    if wiki_manager.transformer is not None:
        wikiurl = wiki_manager._client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        version = wiki_manager.transformer.parser.get_schema_version()
        pages = len(wiki_manager.transformer.get_ocx_elements())
        pages += len(wiki_manager.transformer.get_global_attributes())
        pages += len(wiki_manager.transformer.get_simple_types())
        pages += len(wiki_manager.transformer.get_enumerators())
        msg = f'You are about to publish the schema version ' \
              f'{markup()}{version}{markup_end()}\nwith {markup()}{pages}{markup_end()} pages to namespace ' \
              f'{markup()}{namespace}{markup_end()} ' \
              f'to the ocxwiki with url {wikiurl}\n' \
              f'Using async mode with max {markup()}{max_concurrent}{markup_end()} concurrent operations\n'
        print(msg)
        prompt = wiki_confirm(ctx, 'OK to proceed?')

        if prompt:
            print('Publishing schema asynchronously...')
            # Extract optional TUI callbacks injected by dispatch_typer_command / app.py
            progress_cb = (ctx.obj or {}).get('progress_callback')
            summary_cb = (ctx.obj or {}).get('summary_callback')
            results = run_async(wiki_manager.publish_complete_schema_async(max_concurrent,
                                                                           progress_callback=progress_cb))

            # Build summary lines
            summary_lines = [
                f'\n[green]✓[/green] Publishing complete!',
                f'  Pages published:       {results["pages"]}',
                f'  Enums published:       {results["enums"]}',
                f'  Attributes published:  {results["attributes"]}',
                f'  Simple types published:{results["simple_types"]}',
                f'  Total published:       {results.get("total", "?")}',
            ]
            if results['errors']:
                summary_lines.append(f'\n[red]⚠[/red] Errors encountered: {len(results["errors"])}')
                for i, error in enumerate(results['errors'][:5], 1):
                    summary_lines.append(f'  {i}. {error}')
                if len(results['errors']) > 5:
                    summary_lines.append(f'  ... and {len(results["errors"]) - 5} more errors')

            for line in summary_lines:
                print(line)

            # Send summary to TUI main window if a callback was provided
            if callable(summary_cb):
                try:
                    summary_cb('\n'.join(summary_lines))
                except Exception:
                    pass
    else:
        print('Process a schema first')

@wiki.command()
def publish_state(
        ctx: typer.Context,
        draft: Annotated[bool, typer.Option(
            help='The schema status, draft or public. True if the schema is a draft.',
            prompt=True)] = True

):
    """Set the publishing state (draft or public)."""
    wiki_manager = _get_wiki_manager(ctx)
    publish_state = PublishState(not(draft))
    wiki_manager.set_publish_state(publish_state)
    print (wiki_manager.get_publish_state())

@wiki.command()
def list_pages(
         ctx: typer.Context,
         namespace: Annotated[str, typer.Option(
             help='All pages under the given namespace will be listed.',
             prompt=True)] = 'public:schema:3.1.0:ocx',

):
    """List the pages in the namespace"""
    wiki_manager = _get_wiki_manager(ctx)
    if wiki_manager is None:
        raise ValueError('WikiManager not found in context. Please ensure it is set up correctly.')
    result = wiki_manager._client.list_pages(namespace=namespace, md5_hash=False, skip_acl=True)
    tbl = defaultdict(list)
    for page in result:
        tbl['Name'].append(page.get('id', ''))
        rev = page.get('rev', 0)
        mtime = page.get('mtime', 0)
        tbl['Revised'].append(arrow.get(rev).format('YYYY-MM-DD HH:mm:ss ZZ') if rev else '')
        tbl['Modified'].append(arrow.get(mtime).format('YYYY-MM-DD HH:mm:ss ZZ') if mtime else '')
        tbl['Size'].append(page.get('bytes', ''))
    print(tabulate(tbl, headers='keys'))

@wiki.command()
def page_info(
         ctx: typer.Context,
         page: Annotated[str, typer.Option(
             help='Get the page information.',
             prompt=True)] = 'start',

):
    """List the pages in the namespace"""
    wiki_manager = _get_wiki_manager(ctx)
    if wiki_manager is None:
        raise ValueError('WikiManager not found in context. Please ensure it is set up correctly.')
    result = wiki_manager._client.get_page_info(page=page)
    print(result)



@wiki.command()
def publish_ocx(
    ctx: typer.Context,
    ocx: Annotated[str, typer.Argument(
        help='The name of the OCX element to publish.')] = 'All',
    interactive: Annotated[bool, typer.Option(
         help='Require a user confirmation before publishing.')] = True,
):
    """Publish a global schema element to the ocxwiki."""
    wiki_manager = _get_wiki_manager(ctx)
    prompt = True
    pages = []
    if wiki_manager.transformer is not None:
        if ocx == 'All':
            pages = wiki_manager.transformer.get_ocx_elements()
        else:
            element = wiki_manager.transformer.get_ocx_element_from_type(ocx)
            if element is not None:
                pages = [element]
            else:
                print(f'No schema element with name {ocx}')
                return
        wikiurl = wiki_manager._client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(pages)}{markup_end()} pages in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}\n'
            print(msg)
            prompt = wiki_confirm(ctx, 'OK to proceed?')
        total = 0
        if prompt:
            for ocx in track(pages, description="Publishing global elements..."):
                wiki_manager.publish_page(ocx)
                total += 1
            print(f'Published {total} pages')
    else:
        print('Process a schema first')

@wiki.command()
def publish_attributes(
        ctx: typer.Context,
        interactive: Annotated[bool, typer.Option(
            help='Require a user confirmation before publishing.')] = True,

):
    """Publish all the global schema attributes to the ocxwiki."""
    wiki_manager = _get_wiki_manager(ctx)
    prompt = True
    if wiki_manager.transformer is not None:
        attributes = wiki_manager.transformer.get_global_attributes()
        wikiurl = wiki_manager._client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(attributes)}{markup_end()} pages in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}'
            print(msg)
            prompt = wiki_confirm(ctx, 'OK to proceed?')
        total = 0
        if prompt:
            for attribute in track(attributes, description="Publishing attributes..."):
                wiki_manager.publish_attribute(attribute)
                total += 1
            print(f'Published {total} attribute pages')
    else:
        print('Process a schema first')

@wiki.command()
def publish_enums(
        ctx: typer.Context,
        interactive: Annotated[bool, typer.Option(
            help='Require a user confirmation before publishing.')] = True,
):
    """Publish the global schema enumerators to the ocxwiki."""
    wiki_manager = _get_wiki_manager(ctx)
    prompt = True
    if wiki_manager.transformer is not None:
        enums = wiki_manager.transformer.get_enumerators()
        wikiurl = wiki_manager._client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(enums)}{markup_end()} enumerators in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}'
            print(msg)
            prompt = wiki_confirm(ctx, 'OK to proceed?')
        if prompt:
            total = 0
            for enum in track(enums, description="Publishing enumerators..."):
                wiki_manager.publish_enum(enums[enum])
                total += 1
            print(f'Published {total} enumerator pages')
    else:
        print('Process a schema first')


@wiki.command()
def publish_simple_types(
        ctx: typer.Context,
        interactive: Annotated[bool, typer.Option(
            help='Require a user confirmation before publishing.')] = True,

):
    """Publish the schema simple types to the ocxwiki."""
    wiki_manager = _get_wiki_manager(ctx)
    prompt = True
    if wiki_manager.transformer is not None:
        simples = wiki_manager.transformer.get_simple_types()
        wikiurl = wiki_manager._client.current_url()
        namespace = wiki_manager.get_publish_namespace()
        if interactive:
            msg = f'You are about to publish {markup()}{len(simples)}{markup_end()} simpleType elements in namespace ' \
                  f'{markup()}{namespace}{markup_end()} ' \
                  f'to the ocxwiki with url {wikiurl}'
            print(msg)
            prompt = wiki_confirm(ctx, 'OK to proceed?')
        if prompt:
            total = 0
            for simple in track(simples, description="Publishing simpleType..."):
                wiki_manager.publish_simple_type(simple)
                total += 1
            print(f'Published {total} simpleType pages')
    else:
        print('Process a schema first')


@wiki.command()
def connect(
        ctx: typer.Context,
        user: Annotated[str, typer.Option(
            help='The ocxwiki user. If not provided, uses USER from .env file.'
        )] = None,
        password: Annotated[str, typer.Option(
            help='The ocxwiki user password. If not provided, uses PSWD from .env file.'
        )] = None,
):
    """Connect to the ocxwiki."""
    wiki_manager = _get_wiki_manager(ctx)
    # Use environment variables as fallback if not provided
    username = user if user else USER
    passwd = password if password else PSWD

    if not username or not passwd:
        print('[bold red]Error:[/bold red] Username and password are required.')
        print('Please provide them via --user and --password options or set USER and PSWD in .env file')
        return

    if connected := wiki_manager._client.connect(user=username, password=passwd):
        print(f'[green]✓[/green] Connected to {wiki_manager._client.current_url()}')
        print(f'  Dokuwiki version: {wiki_manager._client.wiki_version()}')
        print(f'  XMLRPC version: {wiki_manager._client.xmlrpc_version()}')
    else:
        print('[bold red]Error:[/bold red] Failed to connect. Please check your credentials.')



