"""Sphinx configuration for the Phonebook API documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# Модулі застосунку читають налаштування під час імпорту; для збірки документації
# підставляємо заглушки, якщо реальних змінних середовища немає.
for key, value in {
    "DB_URL": "postgresql+asyncpg://user:pass@localhost:5432/docs",
    "JWT_SECRET": "sphinx-docs-placeholder-secret-0000",
    "MAIL_FROM": "noreply@example.com",
    "CLD_NAME": "docs",
    "CLD_API_KEY": "docs",
    "CLD_API_SECRET": "docs",
}.items():
    os.environ.setdefault(key, value)

project = "Phonebook API"
copyright = "2026, Mykola Masiuk"
author = "Mykola Masiuk"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "exclude-members": "metadata, registry",
}
# models.User і schemas.User мають однакову назву — неоднозначні посилання не критичні
suppress_warnings = ["ref.python"]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
language = "uk"

html_theme = "alabaster"
html_static_path = ["_static"]
