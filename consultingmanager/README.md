# Consulting Manager

A Django-based project management system designed for consulting firms to manage clients, projects, files, and communications efficiently.

## Features

- **Project Management**: Track and manage consulting projects with detailed information
- **Client Management**: Maintain client information and relationships
- **File Management**: Organize and track project-related files with metadata
- **Billing System**: Handle project billing and financial tracking
- **Communication Tools**: Manage project communications and documentation
- **Data Analysis**: Built-in support for data analysis with pandas and matplotlib
- **Document Processing**: Support for various file formats (PDF, DOCX, MSG)

## Project Structure

```
consultingmanager/
├── billing/           # Billing and financial management
├── clients/           # Client management functionality
├── communications/    # Communication tools
├── files/            # File management system
├── projects/         # Project management core
├── projects_data/    # Project data storage
├── scripts/          # Utility scripts
├── static/           # Static files (CSS, JS, images)
├── templates/        # HTML templates
└── tests/            # Test suite
```

## Requirements

- Python 3.x
- Django >= 5.2
- pandas >= 2.0.0
- matplotlib >= 3.7.0
- networkx >= 3.0
- pdfplumber >= 0.10.0
- python-docx >= 0.8.11
- extract-msg >= 0.41.0
- django-crispy-forms >= 2.0

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd consultingmanager
```

2. Create and activate a virtual environment:
```bash

source .venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Usage

1. Access the admin interface at `http://localhost:8000/admin/`
2. Log in with your superuser credentials
3. Start managing your consulting projects, clients, and files

## Testing

The project includes a comprehensive test suite. Run tests using:
```bash
python manage.py test
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Specify your license here]

## Support

For support, please [contact information or issue tracker link] 