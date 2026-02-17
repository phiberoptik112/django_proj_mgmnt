"""
Email Scanner Service

Scans project directories for .msg email files, processes them using the
EmailTimelineParser, and stores extracted timeline events and status indicators.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class EmailScannerError(Exception):
    """Custom exception for email scanner errors"""
    pass


class EmailScanner:
    """
    Scans directories for .msg files and extracts timeline information.
    """
    
    # Supported email file extensions
    EMAIL_EXTENSIONS = ['.msg', '.eml']
    
    def __init__(self):
        self.parser = None
        self._load_parser()
    
    def _load_parser(self):
        """Lazy load the parser to avoid circular imports"""
        from .email_timeline_parser import EmailTimelineParser
        self.parser = EmailTimelineParser()
    
    def scan_directory(self, directory_path: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Scan a directory for email files.
        
        Args:
            directory_path: Path to the directory to scan
            recursive: Whether to scan subdirectories
            
        Returns:
            List of dicts with email file information
        """
        if not os.path.isdir(directory_path):
            raise EmailScannerError(f"Directory not found: {directory_path}")
        
        email_files = []
        
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                for filename in files:
                    if self._is_email_file(filename):
                        full_path = os.path.join(root, filename)
                        email_files.append({
                            'path': full_path,
                            'filename': filename,
                            'relative_path': os.path.relpath(full_path, directory_path),
                            'size': os.path.getsize(full_path),
                            'modified': datetime.fromtimestamp(os.path.getmtime(full_path))
                        })
        else:
            for filename in os.listdir(directory_path):
                if self._is_email_file(filename):
                    full_path = os.path.join(directory_path, filename)
                    if os.path.isfile(full_path):
                        email_files.append({
                            'path': full_path,
                            'filename': filename,
                            'relative_path': filename,
                            'size': os.path.getsize(full_path),
                            'modified': datetime.fromtimestamp(os.path.getmtime(full_path))
                        })
        
        return email_files
    
    def _is_email_file(self, filename: str) -> bool:
        """Check if a file is an email file based on extension"""
        return any(filename.lower().endswith(ext) for ext in self.EMAIL_EXTENSIONS)
    
    def process_msg_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a single .msg file and extract email data.
        
        Args:
            file_path: Path to the .msg file
            
        Returns:
            Dict with email data or None if processing failed
        """
        try:
            import extract_msg
            
            msg = extract_msg.Message(file_path)
            
            # Extract email date
            email_date = None
            if msg.date:
                try:
                    # msg.date can be a string or datetime
                    if isinstance(msg.date, str):
                        # Try common date formats
                        for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S']:
                            try:
                                email_date = datetime.strptime(msg.date.strip(), fmt)
                                break
                            except ValueError:
                                continue
                        if not email_date:
                            # Fallback: try to parse just the date part
                            import re
                            date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', msg.date)
                            if date_match:
                                day, month, year = date_match.groups()
                                month_map = {
                                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                                }
                                month_num = month_map.get(month[:3], 1)
                                email_date = datetime(int(year), month_num, int(day))
                    else:
                        email_date = msg.date
                except Exception as e:
                    logger.warning(f"Could not parse date from {file_path}: {e}")
            
            if not email_date:
                # Use file modification time as fallback
                email_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            email_data = {
                'sender': str(msg.sender or ''),
                'to': str(msg.to or ''),
                'subject': str(msg.subject or ''),
                'body': str(msg.body or ''),
                'date': email_date,
                'attachments': [att.longFilename for att in msg.attachments] if msg.attachments else [],
                'file_path': file_path,
            }
            
            msg.close()
            return email_data
            
        except ImportError:
            logger.error("extract_msg library not installed. Run: pip install extract-msg")
            return None
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return None
    
    def process_email_and_extract_events(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email data and extract timeline events using the parser.
        
        Args:
            email_data: Dict with email subject, body, date
            
        Returns:
            Dict with extracted events and indicators
        """
        result = self.parser.parse_email(
            subject=email_data.get('subject', ''),
            body=email_data.get('body', ''),
            email_date=email_data.get('date', datetime.now())
        )
        
        return {
            'events': result.events,
            'indicators': result.indicators,
            'inferred_phase': result.inferred_phase,
            'errors': result.errors
        }
    
    def run_scan_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Run a complete email scan batch.
        
        Args:
            batch_id: ID of the EmailScanBatch to run
            
        Returns:
            Dict with scan results and statistics
        """
        from files.models import EmailScanBatch, EmailTimelineEvent, ProjectStatusIndicator, Email, ProjectFolder
        
        batch = EmailScanBatch.objects.get(id=batch_id)
        
        # Update batch status
        batch.status = 'running'
        batch.started_at = timezone.now()
        batch.save()
        
        stats = {
            'emails_scanned': 0,
            'events_found': 0,
            'indicators_found': 0,
            'errors': []
        }
        
        try:
            # Determine what to scan
            if batch.project:
                # Scan emails already in the database for this project
                emails_to_process = self._get_project_emails(batch)
            elif batch.folder_paths:
                # Scan folder paths for .msg files
                emails_to_process = self._scan_folder_paths(batch)
            else:
                raise EmailScannerError("No project or folder paths specified for scan")
            
            # Process each email
            for email_info in emails_to_process:
                try:
                    result = self._process_single_email(batch, email_info)
                    stats['emails_scanned'] += 1
                    stats['events_found'] += result.get('events_created', 0)
                    stats['indicators_found'] += result.get('indicators_created', 0)
                except Exception as e:
                    logger.error(f"Error processing email: {str(e)}")
                    stats['errors'].append(str(e))
            
            # Update batch statistics
            batch.status = 'completed'
            batch.completed_at = timezone.now()
            batch.total_emails_scanned = stats['emails_scanned']
            batch.total_events_found = stats['events_found']
            if stats['errors']:
                batch.error_summary = '\n'.join(stats['errors'][:10])  # Keep first 10 errors
            batch.save()
            
        except Exception as e:
            logger.error(f"Batch scan failed: {str(e)}")
            batch.status = 'failed'
            batch.error_summary = str(e)
            batch.completed_at = timezone.now()
            batch.save()
            stats['errors'].append(str(e))
        
        return stats
    
    def _get_project_emails(self, batch) -> List[Dict[str, Any]]:
        """Get emails from database for a project"""
        from files.models import Email
        
        emails = Email.objects.filter(project=batch.project)
        
        # Apply date filters if specified
        if batch.scan_date_from:
            emails = emails.filter(date__gte=batch.scan_date_from)
        if batch.scan_date_to:
            emails = emails.filter(date__lte=batch.scan_date_to)
        
        return [
            {
                'email_obj': email,
                'subject': email.subject,
                'body': email.body,
                'date': email.date,
                'sender': email.sender,
                'project': batch.project,
            }
            for email in emails
        ]
    
    def _scan_folder_paths(self, batch) -> List[Dict[str, Any]]:
        """Scan folder paths for .msg files"""
        emails_to_process = []
        
        for folder_path in batch.folder_paths:
            if not os.path.isdir(folder_path):
                logger.warning(f"Folder not found: {folder_path}")
                continue
            
            email_files = self.scan_directory(folder_path, recursive=True)
            
            for file_info in email_files:
                email_data = self.process_msg_file(file_info['path'])
                if email_data:
                    # Apply date filters
                    email_date = email_data.get('date')
                    if email_date:
                        if batch.scan_date_from and email_date.date() < batch.scan_date_from:
                            continue
                        if batch.scan_date_to and email_date.date() > batch.scan_date_to:
                            continue
                    
                    email_data['file_info'] = file_info
                    email_data['project'] = batch.project
                    emails_to_process.append(email_data)
        
        return emails_to_process
    
    @transaction.atomic
    def _process_single_email(self, batch, email_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single email and create timeline events"""
        from files.models import EmailTimelineEvent, ProjectStatusIndicator, Email
        
        result = {
            'events_created': 0,
            'indicators_created': 0,
        }
        
        # Get or create Email object
        email_obj = email_info.get('email_obj')
        if not email_obj:
            # This is from a file scan, we need to find or create the Email record
            # For now, we'll skip creating new Email records from file scans
            # and only process emails already in the database
            logger.info(f"Skipping file-based email (no database record): {email_info.get('file_path', 'unknown')}")
            return result
        
        project = email_info.get('project') or batch.project
        if not project:
            logger.warning("No project associated with email, skipping")
            return result
        
        # Extract events using parser
        parse_result = self.process_email_and_extract_events(email_info)
        
        # Create timeline events
        for event in parse_result['events']:
            # Check for duplicates
            existing = EmailTimelineEvent.objects.filter(
                project=project,
                email=email_obj,
                event_type=event.event_type.value,
                event_date=event.event_date
            ).exists()
            
            if not existing:
                EmailTimelineEvent.objects.create(
                    scan_batch=batch,
                    email=email_obj,
                    project=project,
                    event_type=event.event_type.value,
                    event_date=event.event_date,
                    event_description=event.description[:500],
                    extracted_text=event.extracted_text[:2000],
                    confidence=event.confidence,
                    extraction_method=event.extraction_method,
                )
                result['events_created'] += 1
        
        # Create status indicators
        for indicator in parse_result['indicators']:
            # Check for duplicates
            existing = ProjectStatusIndicator.objects.filter(
                project=project,
                email=email_obj,
                indicator_type=indicator.indicator_type.value,
                indicator_date=indicator.indicator_date
            ).exists()
            
            if not existing:
                ProjectStatusIndicator.objects.create(
                    scan_batch=batch,
                    email=email_obj,
                    project=project,
                    indicator_type=indicator.indicator_type.value,
                    indicator_date=indicator.indicator_date,
                    description=indicator.description[:500],
                    extracted_text=indicator.extracted_text[:2000],
                    confidence=indicator.confidence,
                    inferred_phase=indicator.inferred_phase,
                )
                result['indicators_created'] += 1
        
        return result
    
    def get_project_timeline_summary(self, project_id: int) -> Dict[str, Any]:
        """
        Get a summary of timeline events and status for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Dict with timeline summary data
        """
        from files.models import EmailTimelineEvent, ProjectStatusIndicator
        from projects.models import Project
        
        project = Project.objects.get(id=project_id)
        
        # Get all events
        events = EmailTimelineEvent.objects.filter(
            project=project
        ).order_by('event_date')
        
        # Get indicators
        indicators = ProjectStatusIndicator.objects.filter(
            project=project
        ).order_by('-indicator_date')
        
        # Infer current phase from recent indicators
        recent_indicators = indicators[:10]
        phase_votes = {}
        for ind in recent_indicators:
            if ind.inferred_phase:
                phase_votes[ind.inferred_phase] = phase_votes.get(ind.inferred_phase, 0) + 1
        
        current_phase = max(phase_votes, key=phase_votes.get) if phase_votes else ''
        
        # Event statistics
        event_stats = {
            'total': events.count(),
            'pending': events.filter(status='pending').count(),
            'confirmed': events.filter(status='confirmed').count(),
            'converted': events.filter(status='converted').count(),
            'by_type': {}
        }
        
        for event in events:
            event_type = event.get_event_type_display()
            event_stats['by_type'][event_type] = event_stats['by_type'].get(event_type, 0) + 1
        
        # Upcoming events
        today = timezone.now().date()
        upcoming = events.filter(event_date__gte=today).order_by('event_date')[:10]
        
        return {
            'project': project,
            'events': events,
            'indicators': indicators,
            'current_phase': current_phase,
            'event_stats': event_stats,
            'upcoming_events': upcoming,
            'phase_votes': phase_votes,
        }
