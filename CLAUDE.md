# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based consulting project management system called "Consulting Manager". The main Django project is located in the `consultingmanager/` directory, which contains the core application and all Django apps.

## Development Commands

### Environment Setup
- Activate virtual environment: `source consultingmanager/.venv/bin/activate` (or `consultingmanager/.venv/Scripts/activate` on Windows)
- Install dependencies: `pip install -r consultingmanager/requirements.txt`

### Django Commands (run from consultingmanager/ directory)
- Start development server: `python manage.py runserver`
- Run migrations: `python manage.py migrate`
- Create migrations: `python manage.py makemigrations`
- Create superuser: `python manage.py createsuperuser`
- Run tests: `python manage.py test`
- Collect static files: `python manage.py collectstatic`
- Shell access: `python manage.py shell`

## Architecture

### Core Django Apps
- **projects**: Core project management functionality with timeline features
- **clients**: Client management and relationships
- **files**: File management system with metadata tracking
- **billing**: Financial tracking and billing management
- **communications**: Project communication tools
- **api**: RESTful API endpoints for project timelines and data access

### Key Features
- Django REST Framework API with CORS support
- Crispy Forms with Bootstrap 5 styling
- Debug toolbar for development
- Comprehensive file processing (PDF, DOCX, MSG, etc.)
- Data analysis capabilities with pandas/matplotlib
- Custom authentication and user management

### Database
- Uses SQLite for development (`db.sqlite3`)
- Models span across multiple apps for modular design

### File Structure
- Main Django project: `consultingmanager/consultingmanager/`
- Apps: `consultingmanager/{app_name}/`
- Templates: `consultingmanager/templates/`
- Static files: `consultingmanager/static/`
- Media files: `consultingmanager/media/`
- Project data: `consultingmanager/projects_data/`

### URL Routing
- Root redirects to client list view
- App-specific URLs: `/clients/`, `/projects/`, `/files/`
- API endpoints: `/api/` (includes project timelines and unified timeline)
- Admin interface: `/admin/`
- Built-in authentication URLs for login/logout/password management

### Environment Variables
- `PROJECTS_BASE_PATH`: Override default projects data directory
- Django settings module: `consultingmanager.settings`

### Testing
- Test files are distributed across apps and in dedicated `tests/` app
- Run all tests with `python manage.py test`
- Additional test files in root: `test_*.py`

## Development Notes

- The project uses Django 5.2+ with modern Python practices
- Virtual environment is located at `consultingmanager/.venv/`
- Development database contains real project data
- API functionality is actively being developed (current branch: api_setup_feature)
- Project includes extensive document processing capabilities
- Custom templatetags available in some apps for enhanced template functionality