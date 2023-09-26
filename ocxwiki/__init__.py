#  Copyright (c) 2023. #  OCX Consortium https://3docx.org. See the LICENSE
"""Top level module for the ocxwiki package"""
import os
from dotenv import load_dotenv
from pathlib import Path
from ocx_schema_parser.utils import utilities

__app_name__ = "ocxwiki"
__version__ = '0.2.0'


# Secrets
load_dotenv()
USER = os.getenv("USER")
PSWD = os.getenv("PSWD")
TEST_PSWD = os.getenv("TEST_PSWD")
# package configs
config_file = Path(__file__).parent / "wiki_config.yaml"  # The wiki config
app_config = utilities.load_yaml_config(config_file)  # safe yaml load
WIKI_URL = app_config.get("WIKI_URL")
TEST_WIKI_URL = app_config.get("TEST_WIKI_URL")
DEFAULT_NSP = app_config.get("DEFAULT_NSP")
WORKING_DRAFT = app_config.get("WORKING_DRAFT")
SCHEMA_FOLDER = app_config.get("SCHEMA_FOLDER")
