import os
import django

# Set up Django with minimal settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultingmanager.minimal_settings')
django.setup()

print("Django setup complete")

# Try to import only the clients app
from clients.models import Client
print("Client model imported successfully")

print("Test completed successfully") 