# Automatically populates 'handlers' from the scripts in this folder
# when imported
import os
import importlib
from classes.category_handlers.category_base import CategoryBase

category_handlers = {}
# List of files we shouldn't include in the search
_excluded_files = ["__init__.py", "category_base.py", "__pycache__"]

_parent_dir = os.path.dirname(__file__)
# Get list of files at the location of __init__.py
_file_list = os.listdir(_parent_dir)
# Filter files
_file_list = [file for file in _file_list if not file in _excluded_files]

for file in _file_list:
    handler_name = os.path.splitext(file)[0]
    try:
        a = importlib.import_module("classes.category_handlers." + handler_name)
        handler = a.handler
    except AttributeError:
        print(f"Category handler '{file}' has no 'handler' variable. It will not be used.")
        continue

    if not issubclass(handler, CategoryBase):
        print(f"Category handler '{file}' doesn't inherit from CategoryBase. It will not be used.")
        continue
    
    category_handlers[handler_name] = handler
