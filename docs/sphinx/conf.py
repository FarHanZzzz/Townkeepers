"""Sphinx configuration: API documentation generated from command, policy and contract docstrings."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django  # noqa: E402

django.setup()

project = "Amader TOWNHALL"
author = "Townkeepers"
release = "0.1.0 (Increments 1-2)"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx.ext.viewcode"]
autodoc_member_order = "bysource"
autodoc_default_options = {"members": True, "undoc-members": False, "show-inheritance": False}
autodoc_typehints = "description"
exclude_patterns = ["_build"]
html_theme = "alabaster"
html_title = "Amader TOWNHALL API"
suppress_warnings = ["autodoc.import_object"]
