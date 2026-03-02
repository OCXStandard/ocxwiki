#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Compatibility shim – import Render and RichRender from the render package instead."""

# Re-export from the canonical locations so existing ``from ocxwiki.renderer import …``
# imports continue to work without modification.
from ocxwiki.render.wiki_render import Render
from ocxwiki.render.rich_render import RichRender

__all__ = ["Render", "RichRender"]
