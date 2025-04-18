from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects"

# Example usage in a view or service
def process_project_emails(project_id: str, email_directory: str):
    # Import here to avoid circular imports
    from files.utils.email_processor import process_email_batch
    return process_email_batch(email_directory, project_id)
