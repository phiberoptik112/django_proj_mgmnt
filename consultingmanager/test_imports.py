import time
import sys

def timed_import(module_name):
    start = time.time()
    print(f"Attempting to import {module_name}...")
    try:
        __import__(module_name)
        print(f"Successfully imported {module_name} in {time.time() - start:.2f} seconds")
    except Exception as e:
        print(f"Failed to import {module_name}: {str(e)}")
    print("-" * 50)

# Test basic Python imports first
print("Testing basic Python imports...")
timed_import("os")
timed_import("sys")
timed_import("datetime")

print("\nTesting Django imports...")
# Test Django imports in order of dependency
timed_import("django")
timed_import("django.conf")
timed_import("django.core")
timed_import("django.db")
timed_import("django.db.models")
timed_import("django.db.models.fields")
timed_import("django.db.models.manager")
timed_import("django.db.models.query") 