#!/bin/bash

# Django Consulting Manager Initialization Script
# This script activates the virtual environment and starts the Django development server

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Run Django development server
echo "Starting Django development server..."
python manage.py runserver
