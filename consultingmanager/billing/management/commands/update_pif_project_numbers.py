"""
Management command to update existing PIF scan results with correct project numbers
"""

from django.core.management.base import BaseCommand
from billing.models import PIFScanResult
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update existing PIF scan results with correct project number extraction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-id',
            type=int,
            help='Update only results from a specific batch ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--link-projects',
            action='store_true',
            help='Also attempt to link results to existing projects',
        )

    def handle(self, *args, **options):
        batch_id = options.get('batch_id')
        dry_run = options.get('dry_run')
        link_projects = options.get('link_projects')
        
        # Get scan results to update
        if batch_id:
            scan_results = PIFScanResult.objects.filter(scan_batch_id=batch_id)
            self.stdout.write(f'Updating scan results from batch {batch_id}')
        else:
            scan_results = PIFScanResult.objects.all()
            self.stdout.write('Updating all scan results')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        updated_count = 0
        linked_count = 0
        
        for result in scan_results:
            old_project_number = result.project_number
            old_project_name = result.project_name
            
            # Re-extract project information
            result.extract_project_info_from_path()
            
            # Check if anything changed
            if (old_project_number != result.project_number or 
                old_project_name != result.project_name):
                
                self.stdout.write(
                    f'Result {result.id}: '
                    f'Project number: "{old_project_number}" -> "{result.project_number}", '
                    f'Project name: "{old_project_name}" -> "{result.project_name}"'
                )
                
                if not dry_run:
                    result.save()
                
                updated_count += 1
                
                # Try to link to project if requested
                if link_projects and result.project_number:
                    if not dry_run:
                        if result.link_to_project():
                            linked_count += 1
                            self.stdout.write(f'  -> Linked to project: {result.project}')
                        else:
                            self.stdout.write(f'  -> No matching project found for {result.project_number}')
                    else:
                        # In dry run, just check if a match would be found
                        project = result.find_matching_project()
                        if project:
                            linked_count += 1
                            self.stdout.write(f'  -> Would link to project: {project}')
                        else:
                            self.stdout.write(f'  -> No matching project found for {result.project_number}')
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN: Would update {updated_count} results, '
                    f'would link {linked_count} to projects'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated {updated_count} results, '
                    f'linked {linked_count} to projects'
                )
            )
