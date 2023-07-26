#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""This module provides the ocxwiki app functionality."""

from ocx_tools.ocxwiki import __app_name__, __version__
import sys
import typer
from pathlib import Path
import xsdata
from typing_extensions import Annotated
from typing import Optional
from loguru import logger
from rich.console import Console
from ocx_tools.ocxwiki.client import WikiClient
from tabulate import tabulate

wiki_cli = typer.Typer()
ocxwiki = WikiClient()


@wiki_cli.command()
def connect(
        url: Annotated[str, typer.Option(help='The wiki URL.')] = WIKI_URL,

    ):
    """Serialize an OCX model to JSON."""
    if parser.is_parsed():
        logger.info(f'Serializing {model} to JSON')
        if parser.xml_to_json():
            logger.info(f'Successfully serialized OCX model.')
        else:
            logger.error(f'Unable to parse OCX model.')
    else:
        typer.secho(f'Parse an OCX model before serializing to JSON.')

@parse.command()
def model(model: Path):
    """Parse an OCX model."""
    logger.info(f'Parsing OCX model {model}')
    if parser.parse(model):
        logger.info(f'Successfully parsed OCX model.')
    else:
        logger.error(f'Unable to parse OCX model.')


@parse.command()
def xsdata_version():
    """Print the XSdata parser version."""

    typer.secho(f'The XSdata version: {xsdata.__version__}')


@parse.command()
def parts(
        part: Annotated[str, typer.Argument(help='The name of the ocx part to retrieve.')] = 'Plate'
    ):
    """Get all parts of type ```part``` from the OCX model."""
    cont = False
    result = parser.get_parts(part)
    item = result[0]
    typer.echo(tabulate(result))

