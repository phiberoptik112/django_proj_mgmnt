"""
Management command to run PIF scans on a schedule
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from billing.models import PIFScanSchedule, PIFScanBatch, PIFScanResult
from billing.utils.pif_scanner import PIFScanner
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run PIF scans for active schedules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='Run scan for a specific schedule ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force run even if not due',
        )

    def handle(self, *args, **options):
        schedule_id = options.get('schedule_id')
        force = options.get('force')
        
        if schedule_id:
            # Run specific schedule
            try:
                schedule = PIFScanSchedule.objects.get(id=schedule_id)
                self.run_schedule(schedule, force)
            except PIFScanSchedule.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Schedule {schedule_id} not found'))
        else:
            # Run all active schedules that are due
            schedules = PIFScanSchedule.objects.filter(is_active=True)
            
            if not schedules.exists():
                self.stdout.write(self.style.WARNING('No active schedules found'))
                return
            
            for schedule in schedules:
                if self.should_run_schedule(schedule) or force:
                    self.run_schedule(schedule, force)
                else:
                    self.stdout.write(f'Schedule "{schedule.name}" not due yet')

    def should_run_schedule(self, schedule):
        """Check if a schedule should run based on frequency and last run"""
        if not schedule.last_run:
            return True
        
        now = timezone.now()
        last_run = schedule.last_run
        
        if schedule.frequency == 'daily':
            return (now - last_run).days >= 1
        elif schedule.frequency == 'weekly':
            return (now - last_run).days >= 7
        elif schedule.frequency == 'monthly':
            return (now - last_run).days >= 30
        else:  # manual
            return False

    def run_schedule(self, schedule, force=False):
        """Run a PIF scan for a specific schedule"""
        self.stdout.write(f'Running scan for schedule: {schedule.name}')
        
        try:
            with transaction.atomic():
                # Create batch
                batch = PIFScanBatch.objects.create(
                    name=f"{schedule.name} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                    description=f"Automated scan from schedule: {schedule.name}",
                    year_folders=schedule.year_folders,
                    status='running',
                    started_at=timezone.now()
                )
                
                # Run scanner
                scanner = PIFScanner()
                total_scanned = 0
                total_ingested = 0
                total_skipped = 0
                total_errors = 0
                
                for folder_path in schedule.year_folders:
                    self.stdout.write(f'  Scanning folder: {folder_path}')
                    
                    try:
                        results = scanner.scan_year_folder(folder_path)
                        
                        for result_data in results:
                            # Create scan result
                            scan_result = PIFScanResult.objects.create(
                                scan_batch=batch,
                                container_dir=result_data.get('container_dir', ''),
                                folder_kind=result_data.get('folder_kind', ''),
                                pif_file=result_data.get('pif_file', ''),
                                files_count=result_data.get('files_count'),
                                rows=result_data.get('rows'),
                                status=result_data.get('status', 'skipped'),
                                reason=result_data.get('reason', ''),
                            )
                            scan_result.extract_project_info_from_path()
                            scan_result.save()
                            
                            total_scanned += 1
                            if result_data.get('status') == 'ingested':
                                total_ingested += 1
                            elif result_data.get('status') == 'skipped':
                                total_skipped += 1
                            elif result_data.get('status') == 'error':
                                total_errors += 1
                    
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'Error scanning {folder_path}: {str(e)}'))
                        total_errors += 1
                
                # Update batch statistics
                batch.total_scanned = total_scanned
                batch.total_ingested = total_ingested
                batch.total_skipped = total_skipped
                batch.total_errors = total_errors
                batch.status = 'completed'
                batch.completed_at = timezone.now()
                batch.save()
                
                # Update schedule
                schedule.last_run = timezone.now()
                schedule.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Scan completed: {total_scanned} scanned, {total_ingested} ingested, '
                        f'{total_skipped} skipped, {total_errors} errors'
                    )
                )
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error running schedule {schedule.name}: {str(e)}'))
            
            # Update batch status if it was created
            if 'batch' in locals():
                batch.status = 'failed'
                batch.error_summary = str(e)
                batch.save()
