import sys
from importlib import import_module
import time

def debug_import(module_name):
    print(f"Attempting to import {module_name}...")
    start = time.time()
    try:
        module = import_module(module_name)
        print(f"Successfully imported {module_name} in {time.time() - start:.2f} seconds")
        return module
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")
        return None

# Test basic Django imports
modules_to_test = [
    'django',
    'django.conf',
    'django.core',
    'django.db',
    'django.db.utils',
    'django.core.management',
    'django.core.checks',
]

for module in modules_to_test:
    debug_import(module) 