import os
from datetime import datetime
from .models import ProjectMetadata
from .utils.email_processor import process_email_batch

def analyze_project_metadata(metadata_id: int) -> None:
    """
    Analyze a project's files and update its metadata.
    
    Args:
        metadata_id: ID of the ProjectMetadata instance to analyze
    """
    # Import analysis functions here to avoid loading heavy dependencies during Django startup
    from .utils.quick_project_analysis import (
        analyze_proposals,
        analyze_scope_of_work,
        create_project_file_list,
        plot_folder_tree
    )
    
    try:
        metadata = ProjectMetadata.objects.get(id=metadata_id)
        metadata.status = 'in_progress'
        metadata.save()

        project_path = metadata.project_path
        
        # Validate project path
        if not os.path.exists(project_path):
            raise ValueError(f"Project path does not exist: {project_path}")

        # Create file structure analysis
        file_structure = create_project_file_list(project_path)
        metadata.save_file_structure(file_structure)
        
        # Generate folder tree visualization
        plot_folder_tree(project_path, file_structure)
        
        # Analyze proposals for dollar amounts
        proposal_results = analyze_proposals([project_path])
        metadata.save_dollar_amounts(proposal_results)
        
        # Analyze scope of work
        scope_results = analyze_scope_of_work([project_path])
        metadata.save_scope_analysis(scope_results)
        
        # Process emails if they exist
        emails_dir = os.path.join(project_path, 'emails')
        if os.path.exists(emails_dir):
            email_summary_path = process_email_batch(emails_dir, str(metadata.project.id))
            if email_summary_path:
                with open(email_summary_path, 'r') as f:
                    metadata.email_summary = f.read()

        # Update metadata status
        metadata.status = 'completed'
        metadata.last_analyzed = datetime.now()
        metadata.save()

    except Exception as e:
        if metadata:
            metadata.status = 'failed'
            metadata.save()
        raise e 