import os
import django

# Set up Django with minimal settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultingmanager.minimal_settings')
django.setup()

print("Django setup complete")

# Try to import models
from clients.models import Client
print("Client model imported successfully")

from projects.models import Project
print("Project model imported successfully")

from files.models import File, ProjectFolder, FileMetadata, ProjectAnalysis
print("Files models imported successfully")

print("All models imported successfully")

# Try to create a test client
client = Client(
    name="Test Client",
    company="Test Company",
    email="test@example.com",
    phone="123-456-7890",
    address="123 Test St"
)
print("Test client object created successfully") 