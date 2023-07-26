#  Copyright (c) 2023. #  OCX Consortium https://3docx.org. See the LICENSE
"""Top level module for the ocxwiki package"""
import os
from os.path import join, dirname
from dotenv import load_dotenv
from pathlib import Path
from ocx_schema_parser.utils import utilities

__app_name__ = "ocxwiki"
__version__ = '0.1.0'

config_file = Path(__file__).parent / "wiki_config.yaml"  # The wiki config

app_config = utilities.load_yaml_config(config_file)  # safe yaml load

WIKI_URL = app_config.get("WIKI_URL")
USER = app_config.get("USER")
PSWD = app_config.get("PSWD")
DEFAULT_NSP = app_config.get("DEFAULT_NSP")
DATA_SCHEMA = app_config.get("DATA_SCHEMA")
