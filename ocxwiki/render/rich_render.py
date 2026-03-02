#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""Rich terminal renderer – produces Rich renderables from OCX schema data."""

# System imports
from typing import Dict, List, Optional
from collections import defaultdict

# Third party imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Module imports
import ocxwiki.struct_data as struct_data
from ocx_schema_parser.elements import OcxGlobalElement
from ocx_schema_parser.data_classes import OcxEnumerator, BaseDataClass, SchemaAttribute


class RichRender:
    """Render OCX schema element tables as Rich-formatted output for the terminal.
    """


    @staticmethod
    def make_table(clazz: BaseDataClass, title: str = "Table") -> Table:
        """Build a :class:`rich.table.Table` from a plain *dict*.

        Arguments:
            clazz: BaseDataClass instance to render as a table.
            title: Optional table title rendered above the table.

        Returns:
            An empty :class:`rich.table.Table` ready for adding rows.
        """
        tbl = Table(title=title or None, box=box.ROUNDED, highlight=True, show_header=True)
        if not clazz:
            return tbl

        columns = clazz.to_dict().keys() if isinstance(clazz, BaseDataClass) else clazz.keys()
        for col in columns:
            tbl.add_column(str(col), style="cyan", no_wrap=False)

        return tbl


    @staticmethod
    def page_header(name: str) -> Panel:
        """Render a Rich Panel as a page header.

        Arguments:
            name: The element name to display in the header.

        Returns:
            A :class:`rich.panel.Panel`.
        """
        return Panel(Text(name, style="bold magenta", justify="center"), expand=False)

    @staticmethod
    def page_text(text: str) -> Text:
        """Render annotation / body text.

        Arguments:
            text: The description or annotation string.

        Returns:
            A :class:`rich.text.Text`.
        """
        return Text(text or "", style="white")

    # ------------------------------------------------------------------ #
    # Table renderers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def add_rows(table:Table, ocx:OcxGlobalElement) -> None:
        """
        Print schema information in a formatted table using Rich.

        Args:
            table: Dictionary containing table information
                columns: Table headers
                rows: list of row values
        table dict format example:
        {
            "title": "Child Elements",
            "columns": ["Name", "Type", "Description"],
            "rows": [
                {"Name": "child1", "Type": "string", "Description": "First child element"},
                {"Name": "child2", "Type": "integer", "Description": "Second child element"},
                {"Name": "child3", "Type": "boolean", "
                    "Description": "Third child element"},
            ]
        }
        Returns:
            None.
        """
        name = ocx.get_name()

        # Children table
        tbl = ocx.children_to_dict()

        return

    @staticmethod
    def dict(attribute: dict, title: str = "") -> Table:
        """Render an attribute dict as a single-row Rich table.

        Arguments:
            attribute: The attribute dict (key → scalar value).
            title:     Optional table title.

        Returns:
            A :class:`rich.table.Table`.
        """
        return RichRender._make_table(attribute, title=title)

    @staticmethod
    def dataclass(clazz: BaseDataClass, title: str = "") -> Table:
        """Render a :class:`~ocx_schema_parser.data_classes.BaseDataClass` as a Rich table.

        Arguments:
            clazz: The dataclass instance to render.
            title: Optional table title.

        Returns:
            A :class:`rich.table.Table`.
        """
        return RichRender._make_table(clazz.to_dict(), title=title)

    @staticmethod
    def data_struct(data: Dict, title: str = "Structured Data") -> Table:
        """Render wiki page structured data as a Rich table.

        Arguments:
            data:  Key/value structured-data dict.
            title: Optional table title (default: ``"Structured Data"``).

        Returns:
            A :class:`rich.table.Table`.
        """
        return RichRender._make_table(data, title=title)

    # ------------------------------------------------------------------ #
    # Composite page renderers                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def page(
        ocx: OcxGlobalElement,
        data: struct_data.WikiSchema,
        global_elements: List,
        builtins: Dict,
        console: Optional[Console] = None,
    ) -> None:
        """Render an OCX global element to the terminal using Rich.

        Prints the page header, annotation, children table, attributes table
        and structured-data table – all formatted with Rich.

        Arguments:
            ocx:             The OCX element to render.
            data:            The wiki structured data.
            global_elements: OCX global element names.
            builtins:        Builtin W3C types.
            console:         Optional :class:`rich.console.Console`; falls back
                             to the class-level shared console when *None*.
        """
        con = console or RichRender._console
        name = ocx.get_name()

        con.print(RichRender.page_header(name))
        con.print(RichRender.page_text(ocx.get_annotation()))

        children_tbl = ocx.children_to_dict()
        if children_tbl:
            con.print(f"[bold]{name}[/bold] has the following child elements:")
            con.print(RichRender._make_table(children_tbl, title="Child Elements"))

        attrs_tbl = ocx.attributes_to_dict()
        if attrs_tbl:
            con.print(f"[bold]{name}[/bold] has the following attributes:")
            con.print(RichRender._make_table(attrs_tbl, title="Attributes"))

        con.print(RichRender.data_struct(data.to_dict(), title="Structured Data"))

    @staticmethod
    def enum(
        enum: OcxEnumerator,
        data: struct_data.WikiSchema,
        console: Optional[Console] = None,
    ) -> None:
        """Render an OCX enumerator to the terminal using Rich.

        Arguments:
            enum:    The enumerator to render.
            data:    The wiki structured data.
            console: Optional :class:`rich.console.Console`.
        """
        con = console or RichRender._console
        name = enum.name

        con.print(RichRender.page_header(name))

        raw = enum.to_dict()
        if raw:
            table: dict = defaultdict(list)
            for key, values in raw.items():
                if "Description" in key:
                    table[key] = values
                elif "Value" in key:
                    table[key] = list(values)  # no wiki %%-escaping needed for terminal output

            if table:
                con.print(f"[bold]{name}[/bold] has the following values:")
                con.print(RichRender._make_table(table, title="Enum Values"))

        con.print(RichRender.data_struct(data.to_dict(), title="Structured Data"))

    @staticmethod
    def attribute(
        attribute: SchemaAttribute,
        data: struct_data.WikiSchema,
        console: Optional[Console] = None,
    ) -> None:
        """Render a schema attribute to the terminal using Rich.

        Arguments:
            attribute: The attribute to render.
            data:      The wiki structured data.
            console:   Optional :class:`rich.console.Console`.
        """
        con = console or RichRender._console
        name = attribute.name

        con.print(RichRender.page_header(name))
        con.print(f"[bold]{name}[/bold] has the following values:")
        con.print(RichRender.dict(attribute.to_dict(), title=name))
        con.print(RichRender.data_struct(data.to_dict(), title="Structured Data"))

    @staticmethod
    def element(
        ocx: OcxGlobalElement,
        console: Optional[Console] = None,
    ) -> None:
        """Render an OCX global element as Rich tables printed to the terminal.

        Prints the element name header, annotation, children table and
        attributes table.  Simpler than :meth:`page` – does not require
        ``global_elements`` or ``builtins`` lookup tables so it can be called
        with just the :class:`~ocx_schema_parser.elements.OcxGlobalElement`.

        Arguments:
            ocx:     The OCX global element to render.
            console: Optional :class:`rich.console.Console`; falls back to the
                     class-level shared console when *None*.
        """
        con = console or RichRender._console
        name = ocx.get_name()

        con.print(RichRender.page_header(name))
        annotation = ocx.get_annotation()
        if annotation:
            con.print(RichRender.page_text(annotation))

        children_tbl = ocx.children_to_dict()
        if children_tbl:
            con.print(f"[bold]{name}[/bold] has the following child elements:")
            con.print(RichRender._make_table(children_tbl, title="Child Elements"))

        attrs_tbl = ocx.attributes_to_dict()
        if attrs_tbl:
            con.print(f"[bold]{name}[/bold] has the following attributes:")
            con.print(RichRender._make_table(attrs_tbl, title="Attributes"))

    # ------------------------------------------------------------------ #
    # Link helpers (return Rich markup strings)                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def link_internal(prefix: str, name: str, publish_ns: str) -> str:
        """Return a Rich markup hyperlink string for an internal wiki element.

        Arguments:
            prefix:     The OCX namespace prefix.
            name:       The OCX element name.
            publish_ns: The publishing namespace.

        Returns:
            A Rich ``[link=…]…[/link]`` markup string.
        """
        return f"[link={publish_ns}:{prefix}:{name}]{name}[/link]"

    @staticmethod
    def link_external(name: str, builtins: Dict) -> str:
        """Return a Rich markup hyperlink string for an external W3C builtin.

        Arguments:
            name:     The OCX element name.
            builtins: Dict mapping names to external URLs.

        Returns:
            A Rich ``[link=…]…[/link]`` markup string.
        """
        url = builtins.get(name, "")
        return f"[link={url}]{name}[/link]"

