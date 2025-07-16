"""
Django management command to analyze RecItems for projects.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from files.utils.recitem_analyzer import analyze_project_recitems, RecItemContentAnalyzer
from projects.models import Project, RecItem
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Analyze RecItems for projects based on email and file content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='Analyze RecItems for a specific project ID'
        )
        parser.add_argument(
            '--all-projects',
            action='store_true',
            help='Analyze RecItems for all projects'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run analysis without creating new versions'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        all_projects = options.get('all_projects')
        dry_run = options.get('dry_run')
        verbose = options.get('verbose')

        if verbose:
            logging.getLogger().setLevel(logging.INFO)

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No versions will be created')
            )

        if project_id:
            # Analyze specific project
            try:
                project = Project.objects.get(id=project_id)
                self.analyze_project(project, dry_run, verbose)
            except Project.DoesNotExist:
                raise CommandError(f'Project {project_id} does not exist')
        
        elif all_projects:
            # Analyze all projects
            projects = Project.objects.all()
            self.stdout.write(f'Analyzing RecItems for {projects.count()} projects...')
            
            for project in projects:
                self.analyze_project(project, dry_run, verbose)
        
        else:
            # Analyze projects with RecItems
            projects_with_recitems = Project.objects.filter(
                scope_items__rec_items__isnull=False
            ).distinct()
            
            if not projects_with_recitems.exists():
                self.stdout.write(
                    self.style.WARNING('No projects with RecItems found')
                )
                return
            
            self.stdout.write(f'Analyzing RecItems for {projects_with_recitems.count()} projects...')
            
            for project in projects_with_recitems:
                self.analyze_project(project, dry_run, verbose)
        
        self.stdout.write(
            self.style.SUCCESS('RecItem analysis completed')
        )

    def analyze_project(self, project, dry_run=False, verbose=False):
        """Analyze RecItems for a specific project."""
        self.stdout.write(f'\nAnalyzing project: {project.title} (ID: {project.id})')
        
        # Count RecItems for this project
        rec_items_count = RecItem.objects.filter(
            scope_item__project=project
        ).count()
        
        if rec_items_count == 0:
            self.stdout.write(
                self.style.WARNING(f'  No RecItems found for project {project.title}')
            )
            return
        
        self.stdout.write(f'  Found {rec_items_count} RecItems')
        
        if dry_run:
            # In dry run mode, just show what would be analyzed
            rec_items = RecItem.objects.filter(
                scope_item__project=project
            ).select_related('scope_item')
            
            for rec_item in rec_items:
                self.stdout.write(f'    - {rec_item.title} (Keywords: {rec_item.keywords})')
            
            # Count emails and files
            email_count = project.emails.count()
            file_count = project.files.count()
            
            self.stdout.write(f'  Would analyze {email_count} emails and {file_count} files')
            return
        
        try:
            # Run the analysis
            analyzer = RecItemContentAnalyzer(project.id)
            results = analyzer.run_full_analysis()
            
            # Display results
            self.display_analysis_results(results, verbose)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  Error analyzing project {project.title}: {str(e)}')
            )

    def display_analysis_results(self, results, verbose=False):
        """Display analysis results."""
        project_title = results['project_title']
        total_updates = results['total_updates']
        total_errors = results['total_errors']
        
        self.stdout.write(f'  Results for {project_title}:')
        self.stdout.write(f'    - Versions created: {total_updates}')
        self.stdout.write(f'    - Errors: {total_errors}')
        
        if verbose and results['email_results']:
            self.stdout.write('    Email analysis results:')
            for result in results['email_results']:
                if result.get('action') == 'version_created':
                    rec_item = result['rec_item']
                    email = result['email']
                    self.stdout.write(f'      ✓ Created version for "{rec_item.title}" from email "{email.subject}"')
                elif result.get('action') == 'version_failed':
                    self.stdout.write(f'      ✗ Failed to create version: {result.get("error")}')
        
        if verbose and results['file_results']:
            self.stdout.write('    File analysis results:')
            for result in results['file_results']:
                if result.get('action') == 'version_created':
                    rec_item = result['rec_item']
                    file = result['file']
                    self.stdout.write(f'      ✓ Created version for "{rec_item.title}" from file "{file.title}"')
                elif result.get('action') == 'version_failed':
                    self.stdout.write(f'      ✗ Failed to create version: {result.get("error")}')
        
        if total_updates > 0:
            self.stdout.write(
                self.style.SUCCESS(f'    ✓ Successfully created {total_updates} new versions')
            )
        
        if total_errors > 0:
            self.stdout.write(
                self.style.WARNING(f'    ⚠ {total_errors} errors occurred')
            ) 