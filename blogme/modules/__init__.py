# -*- coding: utf-8 -*-

import importlib
import types
from typing import Optional
import os


addons_path = ['blogme.modules.']


def add_module_path(folder: str) -> None:
    """
    Adds a new search path to the list of search paths.
    """
    import os
    addons_path.append(os.path.abspath(folder))


def find_module(name: str) -> Optional[types.ModuleType]:
    """
    Returns the module by the given name.
    """
    for path in reversed(addons_path):
        try:
            mn = path + name
            module = importlib.import_module(mn)
            return module
        except ImportError as e:
            pass
