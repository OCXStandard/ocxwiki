#  Copyright (c) 2023. OCX Consortium https://3docx.org. See the LICENSE
"""Wiki content renderer."""
# System imports
from typing import Dict, List
from collections import defaultdict

# Third party imports
from tabulate import tabulate
#module imports
import ocxwiki.struct_data as struct_data
from ocx_schema_parser.elements import OcxGlobalElement
from ocx_schema_parser.data_classes import OcxEnumerator, BaseDataClass, SchemaAttribute




class Render:

    @staticmethod
    def table(table: dict) -> str:
        """Render dict to dokuwiki table.

        Arguments:
            table: The input table data

        Returns:
            dokuwiki table
        """
        # protect the table headers (keys) to be linked
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
        #Header
        content ='^'
        for col in attribute:
            content += f'{col}^'
        content += '\n|'
        for col in attribute.values():
            content += f'{col}|'
        content += '\n\n'
        return content

    @staticmethod
    def page(ocx: OcxGlobalElement, data: struct_data.WikiSchema, global_elements:List, builtins:Dict) -> str:
        """Render an OCX global element to a dokuwiki page.

        Arguments:
            builtins: Builtin W3C types
            global_elements: OCX global element names
            data: The dokuwiki structured data
            ocx: The OCX element to render

        Returns:
            dokuwiki page
        """
        # Page heading
        name = ocx.get_name()
        prefix = ocx.get_prefix()
        content = Render.page_header(name)
        # Element annotation
        content += Render.page_text(ocx.get_annotation())
        # Children table
        tbl = ocx.children_to_dict() # ToDo: Iterate over OcxSchemaChild data class
        if tbl:
            content += f'%%{name}%% has the following child elements:\n'
            content += f'\n{Render.table(tbl)}\n\n'
        # Attributes table
        tbl = ocx.attributes_to_dict() # To Do: Iterate over OcxSchemaAttribute data class
        if tbl:
            content += f'%%{name}%% has the following attributes:\n'
            content += f'\n{Render.table(tbl)}\n\n'
        # add that structured data
        content += struct_data.struct_gen('version', data.to_dict())
        return content

    @staticmethod
    def enum(enum: OcxEnumerator, data: struct_data.WikiSchema) -> str:
        """Render an OCX enumerator to a dokuwiki page.

        Arguments:
            enum: The enumerator to publish
            data: The dokuwiki structured data
            ocx: The OCX element to render

        Returns:
            dokuwiki page
        """
        # Page heading
        name = enum.name
        content = Render.page_header(name)
        if tbl := enum.to_dict():
            # Protect enum values from being linked
            table = defaultdict(list)
            for key in tbl:
                if 'Description' in key: table[key] = tbl[key]
                if 'Value' in key:
                    for v in tbl[key]:
                        table[key].append(f'%%{v}%%')
            content += f'%%{name}%% has the following values:\n'
            content += f'\n{Render.table(table)}\n\n'
        # add that structured data
        content += struct_data.struct_gen('version', data.to_dict())
        return content

    @staticmethod
    def attribute(attribute: SchemaAttribute, data: struct_data.WikiSchema) -> str:
        """Render an schema attribute to a dokuwiki page.

        Arguments:
            attribute: The attribute to publish
            data: The dokuwiki structured data
            ocx: The OCX element to render

        Returns:
            dokuwiki page
        """
        # Page heading
        name = attribute.name
        content = Render.page_header(name)
        content += f'%%{name}%% has the following values:\n'
        content += f'\n{Render.dict(attribute.to_dict())}\n\n'
        # add that structured data
        content += struct_data.struct_gen('version', data.to_dict())
        return content


    @staticmethod
    def page_header(name: str) -> str:
        """"Render a dokuwiki header with level 3.

        Arguments:
            name: Page header
        Returns:
            dokuwiki table
        """
        return f'===={name}====\n\n\n'

    @staticmethod
    def page_text(text: str) -> str:
        """Render dokuwiki body text.
        Arguments:
            text: content to be rendered

        Returns:
            dokuwiki table

            """
        return f'{text}\n'


    @staticmethod
    def dataclass(clazz: BaseDataClass) -> str:
        """Render dataclass to dokuwiki table.

        Arguments:
            clazz: dataclass to render

        Returns:
            dokuwiki table

        """
        tbl = clazz.to_dict()
        return Render.table(tbl)

    @staticmethod
    def data_struct(data: Dict) -> str:
        """Render the wiki page structured data."""

        return  struct_data.struct_gen('version', data)


    @staticmethod
    def link_internal(prefix: str, name: str, publish_ns: str) -> str:
        """Link a global element in the publishing namespace.

            Arguments:
                prefix: The ocx prefix
                name: The OCX element name
                publish_ns: The publishing namespace

        """
        return f'[[{publish_ns}:{prefix}:{name}|{name}]]'

    @staticmethod
    def link_external(name: str, builtins: Dict) -> str:
        """Link a global element in the publishing namespace.

            Arguments:
                name: The OCX name
                bultins: The W3C builtin external links

        """
        return f'[[{builtins[name]}|{name}]]'
