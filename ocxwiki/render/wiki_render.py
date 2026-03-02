#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""DokuWiki content renderer – produces dokuwiki markup strings."""

# System imports
from typing import Dict, List
from collections import defaultdict

# Third party imports
from tabulate import tabulate

# Module imports
import ocxwiki.struct_data as struct_data
from ocx_schema_parser.elements import OcxGlobalElement
from ocx_schema_parser.data_classes import OcxEnumerator, BaseDataClass, SchemaAttribute


class Render:
    """Render OCX schema data as DokuWiki markup strings."""

    @staticmethod
    def table(table: dict) -> str:
        """Render dict to dokuwiki table.

        Arguments:
            table: The input table data

        Returns:
            dokuwiki table
        """
        # protect the table headers (keys) from being linked
        table = {f'%%{key}%%': table[key] for key in table}
        # Jira format is closest to the dokuwiki table format
        result = tabulate(table, headers="keys", tablefmt="jira")
        # Just need to replace header separators
        content = result.replace('||', '^')
        return content

    @staticmethod
    def dict(attribute: dict) -> str:
        """Render an attribute dict to dokuwiki table.

        Arguments:
            attribute: The input table data

        Returns:
            dokuwiki table
        """
        # protect the table headers (keys) to be linked
        attribute = {f'%%{key}%%': attribute[key] for key in attribute}
        # Header
        content = '^'
        for col in attribute:
            content += f'{col}^'
        content += '\n|'
        for col in attribute.values():
            content += f'{col}|'
        content += '\n\n'
        return content

    @staticmethod
    def page(ocx: OcxGlobalElement, data: struct_data.WikiSchema, global_elements: List, builtins: Dict) -> str:
        """Render an OCX global element to a dokuwiki page.

        Arguments:
            ocx:             The OCX element to render
            data:            The dokuwiki structured data
            global_elements: OCX global element names
            builtins:        Builtin W3C types

        Returns:
            dokuwiki page
        """
        name = ocx.get_name()
        prefix = ocx.get_prefix()
        content = Render.page_header(name)
        content += Render.page_text(ocx.get_annotation())
        # Children table
        tbl = ocx.children_to_dict()
        if tbl:
            content += f'%%{name}%% has the following child elements:\n'
            content += f'\n{Render.table(tbl)}\n\n'
        # Attributes table
        tbl = ocx.attributes_to_dict()
        if tbl:
            content += f'%%{name}%% has the following attributes:\n'
            content += f'\n{Render.table(tbl)}\n\n'
        content += struct_data.struct_gen('version', data.to_dict())
        return content

    @staticmethod
    def enum(enum: OcxEnumerator, data: struct_data.WikiSchema) -> str:
        """Render an OCX enumerator to a dokuwiki page.

        Arguments:
            enum: The enumerator to publish
            data: The dokuwiki structured data

        Returns:
            dokuwiki page
        """
        name = enum.name
        content = Render.page_header(name)
        if tbl := enum.to_dict():
            # Protect enum values from being linked
            table = defaultdict(list)
            for key in tbl:
                if 'Description' in key:
                    table[key] = tbl[key]
                if 'Value' in key:
                    for v in tbl[key]:
                        table[key].append(f'%%{v}%%')
            content += f'%%{name}%% has the following values:\n'
            content += f'\n{Render.table(table)}\n\n'
        content += struct_data.struct_gen('version', data.to_dict())
        return content

    @staticmethod
    def attribute(attribute: SchemaAttribute, data: struct_data.WikiSchema) -> str:
        """Render a schema attribute to a dokuwiki page.

        Arguments:
            attribute: The attribute to publish
            data:      The dokuwiki structured data

        Returns:
            dokuwiki page
        """
        name = attribute.name
        content = Render.page_header(name)
        content += f'%%{name}%% has the following values:\n'
        content += f'\n{Render.dict(attribute.to_dict())}\n\n'
        content += struct_data.struct_gen('version', data.to_dict())
        return content

    @staticmethod
    def page_header(name: str) -> str:
        """Render a dokuwiki header with level 3.

        Arguments:
            name: Page header

        Returns:
            dokuwiki header string
        """
        return f'===={name}====\n\n\n'

    @staticmethod
    def page_text(text: str) -> str:
        """Render dokuwiki body text.

        Arguments:
            text: Content to be rendered

        Returns:
            dokuwiki text string
        """
        return f'{text}\n'

    @staticmethod
    def dataclass(clazz: BaseDataClass) -> str:
        """Render a dataclass to a dokuwiki table.

        Arguments:
            clazz: Dataclass to render

        Returns:
            dokuwiki table
        """
        tbl = clazz.to_dict()
        return Render.table(tbl)

    @staticmethod
    def data_struct(data: Dict) -> str:
        """Render the wiki page structured data.

        Arguments:
            data: Key/value structured-data dict

        Returns:
            dokuwiki dataentry block
        """
        return struct_data.struct_gen('version', data)

    @staticmethod
    def link_internal(prefix: str, name: str, publish_ns: str) -> str:
        """Return a dokuwiki internal link to a global element.

        Arguments:
            prefix:     The OCX namespace prefix
            name:       The OCX element name
            publish_ns: The publishing namespace

        Returns:
            dokuwiki ``[[…|…]]`` link string
        """
        return f'[[{publish_ns}:{prefix}:{name}|{name}]]'

    @staticmethod
    def link_external(name: str, builtins: Dict) -> str:
        """Return a dokuwiki external link to a W3C builtin.

        Arguments:
            name:     The OCX element name
            builtins: Dict mapping names to external URLs

        Returns:
            dokuwiki ``[[…|…]]`` link string
        """
        return f'[[{builtins[name]}|{name}]]'

