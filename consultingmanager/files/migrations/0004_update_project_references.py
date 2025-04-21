from django.db import migrations

def copy_and_update_project_references(apps, schema_editor):
    # Get the old and new Project models
    OldProject = apps.get_model('files', 'Project')
    NewProject = apps.get_model('projects', 'Project')
    FileMetadata = apps.get_model('files', 'FileMetadata')
    ProjectFolder = apps.get_model('files', 'ProjectFolder')
    ProjectAnalysis = apps.get_model('files', 'ProjectAnalysis')
    ProjectMetadata = apps.get_model('files', 'ProjectMetadata')

    # First, copy all projects from the old model to the new model
    for old_project in OldProject.objects.all():
        new_project = NewProject.objects.create(
            id=old_project.id,
            name=old_project.name,
            description=old_project.description,
            created_at=old_project.created_at,
            updated_at=old_project.updated_at,
            status=old_project.status,
            client=old_project.client,
            project_type=old_project.project_type,
            start_date=old_project.start_date,
            end_date=old_project.end_date,
            budget=old_project.budget,
            priority=old_project.priority
        )

    # Now update all foreign key references
    for file_metadata in FileMetadata.objects.all():
        try:
            new_project = NewProject.objects.get(id=file_metadata.project_id)
            file_metadata.project = new_project
            file_metadata.save()
        except NewProject.DoesNotExist:
            file_metadata.delete()

    for folder in ProjectFolder.objects.all():
        try:
            new_project = NewProject.objects.get(id=folder.project_id)
            folder.project = new_project
            folder.save()
        except NewProject.DoesNotExist:
            folder.delete()

    for analysis in ProjectAnalysis.objects.all():
        try:
            new_project = NewProject.objects.get(id=analysis.project_id)
            analysis.project = new_project
            analysis.save()
        except NewProject.DoesNotExist:
            analysis.delete()

    for metadata in ProjectMetadata.objects.all():
        try:
            new_project = NewProject.objects.get(id=metadata.project_id)
            metadata.project = new_project
            metadata.save()
        except NewProject.DoesNotExist:
            metadata.delete()

class Migration(migrations.Migration):
    dependencies = [
        ('files', '0003_alter_projectanalysis_project_and_more'),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(copy_and_update_project_references),
    ] 