import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from ..models import Project, ProjectAnalysis
from .quick_project_analysis import (
    extract_text_from_file,
    find_dollar_amounts,
    analyze_scope_of_work,
    create_project_db
)

class ProjectAnalyzer:
    """Service class for analyzing project content"""
    
    def __init__(self, project: Project):
        self.project = project
        
    def analyze_project(self):
        """Run all available analyses on the project"""
        self._analyze_proposals()
        self._analyze_scope_of_work()
        
    def _analyze_proposals(self):
        """Analyze proposal documents for dollar amounts"""
        # Get all proposal files
        proposal_files = self.project.files.filter(
            filename__icontains='proposal',
            file_type__in=['.pdf', '.doc', '.docx']
        )
        
        findings = []
        for file in proposal_files:
            try:
                text_content = extract_text_from_file(file.full_path)
                if text_content:
                    dollar_findings = find_dollar_amounts(text_content)
                    for finding in dollar_findings:
                        finding['source_file'] = file.filename
                        findings.append(finding)
            except Exception as e:
                print(f"Error analyzing proposal {file.filename}: {str(e)}")
                
        # Store analysis results
        if findings:
            ProjectAnalysis.objects.create(
                project=self.project,
                analysis_type='proposal',
                results_json={
                    'findings': findings,
                    'analysis_date': datetime.now().isoformat()
                }
            )
            
    def _analyze_scope_of_work(self):
        """Analyze scope of work sections in project documents"""
        # Get business folder
        business_folder = self.project.folders.filter(folder_type='BUSINESS').first()
        if not business_folder:
            return
            
        # Get all documents in business folder
        documents = business_folder.files.filter(
            file_type__in=['.pdf', '.doc', '.docx']
        )
        
        scope_findings = []
        for doc in documents:
            try:
                text_content = extract_text_from_file(doc.full_path)
                if text_content:
                    # Use existing scope analysis function
                    scope_df = analyze_scope_of_work([doc.full_path])
                    if not scope_df.empty:
                        scope_findings.extend(scope_df.to_dict('records'))
            except Exception as e:
                print(f"Error analyzing scope in {doc.filename}: {str(e)}")
                
        # Store analysis results
        if scope_findings:
            ProjectAnalysis.objects.create(
                project=self.project,
                analysis_type='scope',
                results_json={
                    'findings': scope_findings,
                    'analysis_date': datetime.now().isoformat()
                }
            )
            
    @staticmethod
    def get_analysis_results(project: Project, analysis_type: str) -> Optional[Dict]:
        """Get the most recent analysis results for a project"""
        analysis = ProjectAnalysis.objects.filter(
            project=project,
            analysis_type=analysis_type
        ).order_by('-analysis_date').first()
        
        return analysis.results_json if analysis else None 