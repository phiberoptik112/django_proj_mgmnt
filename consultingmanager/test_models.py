import os
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultingmanager.settings')
django.setup()

print("Django setup complete")

# Now try to import the models
from clients.models import Client
print("Client model imported successfully")

from projects.models import Project
print("Project model imported successfully")

# Try to create a test client
client = Client(
    name="Test Client",
    company="Test Company",
    email="test@example.com",
    phone="123-456-7890",
    address="123 Test St"
)
print("Test client object created successfully") 