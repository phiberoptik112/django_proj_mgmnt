import sys
import os
import django

print("Python version:", sys.version)
print("Python path:", sys.path)
print("Django version:", django.get_version())
print("Current directory:", os.getcwd())
print("Directory contents:", os.listdir('.')) 