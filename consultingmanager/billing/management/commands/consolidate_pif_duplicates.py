"""
Management command to consolidate duplicate PIF scan results
"""

from django.core.management.base import BaseCommand
from billing.models import PIFScanResult, PIFScanBatch
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Consolidate duplicate PIF scan results for the same project'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-id',
            type=int,
            help='Consolidate only results from a specific batch ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be consolidated without making changes',
        )

    def handle(self, *args, **options):
        batch_id = options.get('batch_id')
        dry_run = options.get('dry_run')
        
        if batch_id:
            batch = PIFScanBatch.objects.get(id=batch_id)
            self.stdout.write(f'Consolidating duplicates in batch: {batch.name}')
        else:
            batch = None
            self.stdout.write('Consolidating duplicates in all scan results')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get scan results to analyze
        if batch:
            scan_results = PIFScanResult.objects.filter(scan_batch=batch)
        else:
            scan_results = PIFScanResult.objects.all()
        
        # Group by project number and name
        project_groups = {}
        for result in scan_results:
            if result.project_number and result.project_name:
                key = (result.project_number, result.project_name)
                if key not in project_groups:
                    project_groups[key] = []
                project_groups[key].append(result)
        
        # Find duplicates
        duplicates_found = 0
        total_duplicates = 0
        
        for (project_number, project_name), results in project_groups.items():
            if len(results) > 1:
                duplicates_found += 1
                total_duplicates += len(results) - 1  # -1 because we keep one
                
                self.stdout.write(f'\nDuplicate found: {project_number} - {project_name}')
                for i, result in enumerate(results):
                    status_icon = "✓" if result.status == 'ingested' else "⚠" if result.status == 'error' else "○"
                    self.stdout.write(f'  {i+1}. {status_icon} {result.folder_kind} - {result.status} - {result.container_dir}')
                    if result.pif_file:
                        self.stdout.write(f'     PIF: {result.pif_file}')
                    if result.files_count:
                        self.stdout.write(f'     Files: {result.files_count}')
                    if result.rows:
                        self.stdout.write(f'     Rows: {result.rows}')
        
        if duplicates_found == 0:
            self.stdout.write(self.style.SUCCESS('No duplicates found!'))
            return
        
        self.stdout.write(f'\nFound {duplicates_found} projects with duplicates')
        self.stdout.write(f'Total duplicate entries: {total_duplicates}')
        
        if not dry_run:
            # Perform consolidation
            consolidated_count, deleted_count = PIFScanResult.consolidate_duplicates(batch)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Consolidated {consolidated_count} projects, deleted {deleted_count} duplicate entries'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would consolidate {duplicates_found} projects, would delete {total_duplicates} duplicate entries'
                )
            )
