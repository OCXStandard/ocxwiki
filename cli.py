#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Script entry point."""
from __future__ import annotations
from loguru import logger
import sys
from click import pass_context, clear, secho
from ocxwiki import __app_name__, __version__
from ocxwiki.wiki_cli import wiki
import typer
from typing import Optional
from pathlib import Path

MODULE = 'ocx_schema_parser'

# https://patorjk.com/software/taag/#p=testall&f=Graffiti&t=OCX-wiki
# Font: 3D Diagonal + Star Wars
LOGO = r"""

                                                                                         
    ,----..                                                                              
   /   /   \    ,----..   ,--,     ,--,  
  /   .     :  /   /   \  |'. \   / .`|  
 .   /   ;.  \|   :     : ; \ `\ /' / ;  
.   ;   /  ` ;.   |  ;. / `. \  /  / .' 
;   |  ; \ ; |.   ; /--`   \  \/  / ./  
|   :  | ; | ';   | ;       \  \.'  /   
.   |  ' ' ' :|   : |        \  ;  ;       ____    __    ____  __   __  ___  __ 
'   ;  \; /  |.   | '___    / \  \  \      \   \  /  \  /   / |  | |  |/  / |  |
 \   \  ',  / '   ; : .'|  ;  /\  \  \      \   \/    \/   /  |  | |  '  /  |  |
  ;   :    /  '   | '/  :./__;  \  ;  \      \            /   |  | |    <   |  |
   \   \ .'   |   :    / |   : / \  \  ;      \    /\    /    |  | |  .  \  |  |
    `---`      \   \ .'  ;   |/   \  ' |       \__/  \__/     |__| |__|\__\ |__|
                `---`    `---'     `--`    
                                                                                         
"""

config = {
"handlers": [
{"sink": sys.stdout, "format": "{time} - {message}"},
{"sink": f'{__app_name__}.log', "serialize": True},
],
"extra": {"user": "someone"}
}
logger.remove()  # Remove all handlers added so far, including the default one.
logger.add(sys.stderr, level="WARNING")
logger.configure(**config)
logger.level('INFO')

# console = Console()

# Create the main Typer app
cli = typer.Typer(
    name=__app_name__,
    help="Main CLI application",
    add_completion=False,
)



@cli.command(name="interactive", help="Launch the interactive TUI mode")
def interactive()-> None:
    """Launch the interactive TUI mode."""
    from ocxwiki.app import CLIApp
    cli_app = CLIApp()
    cli_app.run()



@cli.command(name="enable-logging", help="Enable all module logging")
def enable_logging():
    """Enable all module logging."""
    logger.enable(MODULE)

@cli.command(name="disable-logging", help="Disable all module logging")
def disable_logging():
    """Disable all module logging."""
    logger.disable(MODULE)


# Register subcommands AFTER all direct commands
cli.add_typer(wiki, name="wiki", help='Commands for OCX Wiki operations. Use "ocx-wiki wiki COMMAND --help" for details on each command.')

if __name__ == "__main__":
    cli()
