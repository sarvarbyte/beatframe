"""Importing this package registers every template module in it."""

import importlib
import pkgutil

from .base import REGISTRY, BeatScene, Template, get_template

for _m in pkgutil.iter_modules(__path__):
    if _m.name != "base":
        importlib.import_module(f"{__name__}.{_m.name}")

__all__ = ["REGISTRY", "BeatScene", "Template", "get_template"]
