#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""This module provides the ocxwiki app functionality."""


# Sys imports
import sys
from collections import defaultdict
import asyncio
# Third party imports
from loguru import logger
import arrow
import typer
from rich import print
from rich.progress import track
from pathlib import Path
from typing_extensions import Annotated

# Module imports
from ocxwiki import __app_name__, __version__, WIKI_URL, WORKING_DRAFT, USER, TEST_PSWD, PSWD, TEST_WIKI_URL, \
    SCHEMA_FOLDER
from ocxwiki.wiki_manager import WikiManager, PublishState
from ocxwiki.async_helper import run_async
from tabulate import tabulate

wiki = typer.Typer()

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

@wiki.callback()
def main(ctx: typer.Context):
    """
    OCX Wiki CLI - Manage and publish OCX schema to Dokuwiki.
    """
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj['wiki_manager'] = get_wiki_manager()

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
def process_schema_url(
        ctx: typer.Context,
        url: Annotated[str, typer.Option(help='Process a schema for publishing.', prompt=True)] = WORKING_DRAFT,
        folder: Annotated[Path, typer.Option(help='The schema download folder.')] = Path(SCHEMA_FOLDER),
    ):
    """Process a schema before publishing."""
    wiki_manager = ctx.obj['wiki_manager']
    if wiki_manager:
        if result := wiki_manager.process_schema(url, folder): #ToDo: Fix error when processing a local file
            schema_summary(ctx)

@wiki.command()
def process_schema_folder(
        ctx: typer.Context,
        folder: Annotated[Path, typer.Option(help='The schema download folder.', prompt=True)] = Path(SCHEMA_FOLDER),
    ):
    """Process a schema before publishing."""
    wiki_manager = ctx.obj['wiki_manager']
    if wiki_manager:
        result =  wiki_manager.process_schema_folder(folder)
        if result:
            schema_summary(ctx)

@wiki.command()
def schema_summary(ctx: typer.Context):
    """Print a summary of the processed schema."""
    wiki_manager = ctx.obj['wiki_manager']
    if wiki_manager.transformer is not None:
        for ns, tbl in wiki_manager.transformer.parser.tbl_summary().items():
            print(f'Content of namespace {ns}:\n')
            print(tabulate(tbl, headers='keys'),'\n')
    else:
        print('Process a schema first')

@wiki.command()
def version():
    """Print the ocxwiki CLI version."""
    print(f'The {__app_name__} version: {__version__}')

@wiki.command()
def publish_all(ctx: typer.Context):
    """Publish the complete schema to the ocxwiki."""
    wiki_manager = ctx.obj['wiki_manager']
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
        prompt = typer.confirm('OK to proceed?')

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
    wiki_manager = ctx.obj['wiki_manager']
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
        prompt = typer.confirm('OK to proceed?')

        if prompt:
            print('Publishing schema asynchronously...')
            results = run_async(wiki_manager.publish_complete_schema_async(max_concurrent))

            print(f'\n[green]✓[/green] Publishing complete!')
            print(f'  Pages published: {results["pages"]}')
            print(f'  Enums published: {results["enums"]}')
            print(f'  Attributes published: {results["attributes"]}')
            print(f'  Simple types published: {results["simple_types"]}')

            if results['errors']:
                print(f'\n[red]⚠[/red] Errors encountered: {len(results["errors"])}')
                for i, error in enumerate(results['errors'][:5], 1):  # Show first 5 errors
                    print(f'  {i}. {error}')
                if len(results['errors']) > 5:
                    print(f'  ... and {len(results["errors"]) - 5} more errors')
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
    wiki_manager = ctx.obj['wiki_manager']
    publish_state = PublishState(not(draft))
    wiki_manager.set_publish_state(publish_state)
    print (wiki_manager.get_publish_state())

@wiki.command()
def list_pages(
         ctx: typer.Context,
         namespace: Annotated[str, typer.Option(
             help='All pages under the given namespace will be listed.',
             prompt=True)] = '/ocx-if:draft:ocx',

):
    """List the pages in the namespace"""
    wiki_manager = ctx.obj['wiki_manager']
    if wiki_manager is None:
        raise ValueError('WikiManager not found in context. Please ensure it is set up correctly.')
    result = wiki_manager._client.list_pages(namespace=namespace, md5_hash=False, skip_acl=True)
    tbl = defaultdict(list)
    for id, mtime, rev, *all  in result.items():
        tbl['Name'].append(str.replace(namespace,''))
        tbl['Revised'].append(arrow.get(mtime).format('YYYY-MM-DD HH:mm:ss ZZ'))
        tbl['Modified'].append(arrow.get(rev).format('YYYY-MM-DD HH:mm:ss ZZ'))
    print(tabulate(result, headers='keys'))

@wiki.command()
def page_info(
         ctx: typer.Context,
         page: Annotated[str, typer.Option(
             help='Get the page information.',
             prompt=True)] = 'start',

):
    """List the pages in the namespace"""
    wiki_manager = ctx.obj['wiki_manager']
    if wiki_manager is None:
        raise ValueError('WikiManager not found in context. Please ensure it is set up correctly.')
    result = wiki_manager._client.info(page=page, md5_hash=False, skip_acl=True)
    return result



@wiki.command()
def publish_ocx(
    ctx: typer.Context,
    ocx: Annotated[str, typer.Argument(
        help='The name of the OCX element to publish.')] = 'All',
    interactive: Annotated[bool, typer.Option(
         help='Require a user confirmation before publishing.')] = True,
):
    """Publish a global schema element to the ocxwiki."""
    wiki_manager = ctx.obj['wiki_manager']
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
            prompt = typer.confirm('OK to proceed?')
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
    wiki_manager = ctx.obj['wiki_manager']
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
            prompt = typer.confirm('OK to proceed?')
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
    wiki_manager = ctx.obj['wiki_manager']
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
            prompt = typer.confirm('OK to proceed?')
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
    wiki_manager = ctx.obj['wiki_manager']
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
            prompt = typer.confirm('OK to proceed?')
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
    wiki_manager = ctx.obj['wiki_manager']
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



