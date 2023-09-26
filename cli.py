#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Script entry point."""
from __future__ import annotations
from click_shell import shell
from loguru import logger
import sys
from click import pass_context, clear, secho
from ocxwiki import __app_name__, __version__
from ocxwiki.cli import wiki
import typer

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

def exit_cli():
    logger.info(f'{__app_name__} session finished.')

@shell(prompt=f"{__app_name__} >: ", intro=f"Starting {__app_name__}...")
@pass_context
def cli(ctx):
    """
    Main CLI
    """

    secho(LOGO, fg='blue')
    secho(f"Version: {__version__}", fg='green')
    secho("Copyright (c) 2023. OCX Consortium https://3docx.org\n", fg='green')
    logger.info(f'{__app_name__} session started.')
    ctx.call_on_close(exit_cli)
@cli.command(short_help="Clear the screen")
def clear():
    """Clear the console window."""
    clear()


@cli.command(short_help="Clear the screen")
def enable_logging():
    """Enable all module logging."""
    logger.enable(MODULE)

@cli.command(short_help="Clear the screen")
def disable_logging():
    """Disable all module logging."""
    logger.disable(MODULE)


# Arrange all command groups from Typer
typer_click_object = typer.main.get_command(wiki)
cli.add_command(typer_click_object, 'wiki')
""" The Typer sub-commands """

if __name__ == "__main__":
    cli(prog_name=__app_name__)