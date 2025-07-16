"""
RecItem Content Analyzer
Analyzes email and file content to automatically update RecItems based on keywords.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from django.db.models import Q
from django.utils import timezone
from projects.models import RecItem, RecItemVersion, RecItemAttribute
from files.models import Email, File, ProjectMetadata

logger = logging.getLogger(__name__)

class RecItemContentAnalyzer:
    """Analyzes content to automatically update RecItems based on keywords."""
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.project = None
        self.rec_items = []
        self._load_project_data()
    
    def _load_project_data(self):
        """Load project and RecItem data."""
        from projects.models import Project
        try:
            self.project = Project.objects.get(id=self.project_id)
            self.rec_items = RecItem.objects.filter(
                scope_item__project=self.project
            ).select_related('scope_item')
        except Project.DoesNotExist:
            logger.error(f"Project {self.project_id} not found")
            raise ValueError(f"Project {self.project_id} not found")
    
    def analyze_emails(self) -> List[Dict[str, Any]]:
        """
        Analyze project emails for RecItem keywords and create/update versions.
        
        Returns:
            List of analysis results with RecItem updates
        """
        results = []
        
        # Get all emails for this project
        emails = Email.objects.filter(project=self.project).order_by('date')
        
        for email in emails:
            email_results = self._analyze_email_content(email)
            if email_results:
                results.extend(email_results)
        
        return results
    
    def analyze_files(self) -> List[Dict[str, Any]]:
        """
        Analyze project files for RecItem keywords and create/update versions.
        
        Returns:
            List of analysis results with RecItem updates
        """
        results = []
        
        # Get all files for this project
        files = File.objects.filter(project=self.project).order_by('uploaded_at')
        
        for file in files:
            file_results = self._analyze_file_content(file)
            if file_results:
                results.extend(file_results)
        
        return results
    
    def _analyze_email_content(self, email: Email) -> List[Dict[str, Any]]:
        """Analyze a single email for RecItem keywords."""
        results = []
        
        # Combine email subject and body for analysis
        content = f"{email.subject}\n{email.body}".lower()
        
        for rec_item in self.rec_items:
            if not rec_item.keywords:
                continue
            
            # Check if email content matches RecItem keywords
            keyword_matches = self._check_keyword_matches(content, rec_item.keywords)
            
            if keyword_matches:
                # Create new version if content is relevant
                version_data = self._extract_version_data_from_email(email, rec_item, keyword_matches)
                if version_data:
                    try:
                        new_version = self._create_recitem_version(
                            rec_item=rec_item,
                            source_email=email,
                            change_source='email',
                            **version_data
                        )
                        results.append({
                            'rec_item': rec_item,
                            'email': email,
                            'version': new_version,
                            'keyword_matches': keyword_matches,
                            'action': 'version_created'
                        })
                    except Exception as e:
                        logger.error(f"Failed to create RecItem version: {e}")
                        results.append({
                            'rec_item': rec_item,
                            'email': email,
                            'error': str(e),
                            'action': 'version_failed'
                        })
        
        return results
    
    def _analyze_file_content(self, file: File) -> List[Dict[str, Any]]:
        """Analyze a single file for RecItem keywords."""
        results = []
        
        # Get file content (this would need to be implemented based on file type)
        content = self._extract_file_content(file)
        if not content:
            return results
        
        content_lower = content.lower()
        
        for rec_item in self.rec_items:
            if not rec_item.keywords:
                continue
            
            # Check if file content matches RecItem keywords
            keyword_matches = self._check_keyword_matches(content_lower, rec_item.keywords)
            
            if keyword_matches:
                # Create new version if content is relevant
                version_data = self._extract_version_data_from_file(file, rec_item, keyword_matches)
                if version_data:
                    try:
                        new_version = self._create_recitem_version(
                            rec_item=rec_item,
                            source_file=file,
                            change_source='drawing',
                            **version_data
                        )
                        results.append({
                            'rec_item': rec_item,
                            'file': file,
                            'version': new_version,
                            'keyword_matches': keyword_matches,
                            'action': 'version_created'
                        })
                    except Exception as e:
                        logger.error(f"Failed to create RecItem version: {e}")
                        results.append({
                            'rec_item': rec_item,
                            'file': file,
                            'error': str(e),
                            'action': 'version_failed'
                        })
        
        return results
    
    def _check_keyword_matches(self, content: str, keywords: str) -> List[str]:
        """
        Check if content matches any RecItem keywords.
        
        Args:
            content: Text content to analyze
            keywords: Comma-separated keywords from RecItem
            
        Returns:
            List of matched keywords
        """
        if not keywords:
            return []
        
        keyword_list = [kw.strip().lower() for kw in keywords.split(',')]
        matches = []
        
        for keyword in keyword_list:
            if keyword in content:
                matches.append(keyword)
        
        return matches
    
    def _extract_version_data_from_email(self, email: Email, rec_item: RecItem, keyword_matches: List[str]) -> Optional[Dict[str, Any]]:
        """Extract version data from email content."""
        # Extract relevant information from email
        subject = email.subject
        body = email.body
        
        # Look for technical specifications in email content
        technical_specs = self._extract_technical_specs_from_text(body)
        
        # Create version description based on email content
        description = f"Email communication regarding {rec_item.title}. "
        if technical_specs:
            description += f"Technical specifications updated: {', '.join(technical_specs.keys())}"
        
        change_notes = f"Keywords matched: {', '.join(keyword_matches)}"
        
        return {
            'title': rec_item.title,
            'description': description,
            'technical_specs': technical_specs,
            'change_notes': change_notes
        }
    
    def _extract_version_data_from_file(self, file: File, rec_item: RecItem, keyword_matches: List[str]) -> Optional[Dict[str, Any]]:
        """Extract version data from file content."""
        # Extract relevant information from file
        file_content = self._extract_file_content(file)
        if not file_content:
            return None
        
        # Look for technical specifications in file content
        technical_specs = self._extract_technical_specs_from_text(file_content)
        
        # Create version description based on file content
        description = f"File update regarding {rec_item.title}. "
        if technical_specs:
            description += f"Technical specifications updated: {', '.join(technical_specs.keys())}"
        
        change_notes = f"Keywords matched: {', '.join(keyword_matches)}"
        
        return {
            'title': rec_item.title,
            'description': description,
            'technical_specs': technical_specs,
            'change_notes': change_notes
        }
    
    def _extract_technical_specs_from_text(self, text: str) -> Dict[str, str]:
        """
        Extract technical specifications from text content.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary of technical specifications
        """
        specs = {}
        
        # Look for common acoustic specifications
        acoustic_patterns = {
            'insertion_loss': r'insertion\s+loss[:\s]*(\d+(?:\.\d+)?)\s*(?:dB|decibel)',
            'stc_rating': r'stc[:\s]*(\d+(?:\.\d+)?)',
            'nc_rating': r'nc[:\s]*(\d+(?:\.\d+)?)',
            'dimensions': r'(?:dimensions?|size)[:\s]*(\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?)\s*(?:inches?|in|mm|cm)',
            'flow_rate': r'flow\s+rate[:\s]*(\d+(?:\.\d+)?)\s*(?:cfm|lpm)',
            'frequency': r'frequency[:\s]*(\d+(?:\.\d+)?)\s*(?:hz|hertz)',
            'pressure': r'pressure[:\s]*(\d+(?:\.\d+)?)\s*(?:pa|pascal|psi)',
        }
        
        for spec_name, pattern in acoustic_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                specs[spec_name] = matches[0]
        
        return specs
    
    def _extract_file_content(self, file: File) -> Optional[str]:
        """
        Extract text content from file.
        
        Args:
            file: File object to extract content from
            
        Returns:
            Extracted text content or None if not supported
        """
        # This is a simplified implementation
        # In a real implementation, you would use appropriate libraries
        # based on file type (pdfplumber for PDFs, python-docx for Word, etc.)
        
        try:
            # For now, return None - this would need to be implemented
            # based on the specific file types you're working with
            return None
        except Exception as e:
            logger.error(f"Failed to extract content from file {file.id}: {e}")
            return None
    
    def _create_recitem_version(self, rec_item: RecItem, **kwargs) -> RecItemVersion:
        """
        Create a new RecItemVersion.
        
        Args:
            rec_item: The RecItem to create a version for
            **kwargs: Version data
            
        Returns:
            Created RecItemVersion
        """
        # Get the next version number
        latest_version = rec_item.get_latest_version()
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Create the new version
        version = RecItemVersion.objects.create(
            rec_item=rec_item,
            version_number=version_number,
            **kwargs
        )
        
        # Update the main RecItem with latest info
        if 'title' in kwargs:
            rec_item.title = kwargs['title']
        if 'description' in kwargs:
            rec_item.description = kwargs['description']
        rec_item.save()
        
        return version
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run full content analysis for the project.
        
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Starting RecItem content analysis for project {self.project_id}")
        
        email_results = self.analyze_emails()
        file_results = self.analyze_files()
        
        total_updates = len([r for r in email_results + file_results if r.get('action') == 'version_created'])
        total_errors = len([r for r in email_results + file_results if r.get('action') == 'version_failed'])
        
        results = {
            'project_id': self.project_id,
            'project_title': self.project.title,
            'email_results': email_results,
            'file_results': file_results,
            'total_updates': total_updates,
            'total_errors': total_errors,
            'analysis_date': timezone.now(),
        }
        
        logger.info(f"RecItem analysis completed: {total_updates} updates, {total_errors} errors")
        
        return results


def analyze_project_recitems(project_id: int) -> Dict[str, Any]:
    """
    Convenience function to analyze RecItems for a project.
    
    Args:
        project_id: ID of the project to analyze
        
    Returns:
        Analysis results
    """
    analyzer = RecItemContentAnalyzer(project_id)
    return analyzer.run_full_analysis()


def update_recitem_from_keywords(rec_item_id: int, content: str, source_type: str = 'manual') -> Optional[RecItemVersion]:
    """
    Update a specific RecItem based on content analysis.
    
    Args:
        rec_item_id: ID of the RecItem to update
        content: Content to analyze
        source_type: Type of source ('email', 'file', 'manual')
        
    Returns:
        Created RecItemVersion or None if no update needed
    """
    try:
        rec_item = RecItem.objects.get(id=rec_item_id)
        
        if not rec_item.keywords:
            return None
        
        # Check for keyword matches
        keyword_matches = RecItemContentAnalyzer._check_keyword_matches(
            RecItemContentAnalyzer, content.lower(), rec_item.keywords
        )
        
        if not keyword_matches:
            return None
        
        # Extract technical specifications
        technical_specs = RecItemContentAnalyzer._extract_technical_specs_from_text(
            RecItemContentAnalyzer, content
        )
        
        # Create new version
        analyzer = RecItemContentAnalyzer(rec_item.scope_item.project.id)
        return analyzer._create_recitem_version(
            rec_item=rec_item,
            change_source=source_type,
            technical_specs=technical_specs,
            change_notes=f"Keywords matched: {', '.join(keyword_matches)}"
        )
        
    except RecItem.DoesNotExist:
        logger.error(f"RecItem {rec_item_id} not found")
        return None
    except Exception as e:
        logger.error(f"Failed to update RecItem {rec_item_id}: {e}")
        return None 