# files/utilities.py
import hashlib
import os
from django.db.models import Q
from ..models import FileMetadata, Proposal

def calculate_file_hash(file_path, algorithm='md5'):
    """
    Calculate hash of a file using specified algorithm
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')
        
    Returns:
        String containing the file hash
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    if algorithm.lower() == 'md5':
        hash_func = hashlib.md5()
    elif algorithm.lower() == 'sha1':
        hash_func = hashlib.sha1()
    elif algorithm.lower() == 'sha256':
        hash_func = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    # Read in chunks to handle large files efficiently
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
            
    return hash_func.hexdigest()

def find_proposal_by_hash(file_hash, project_id=None, hash_type='md5'):
    """
    Check if a proposal with the given hash exists
    
    Args:
        file_hash: Hash value to search for
        project_id: Optional project ID to limit the search
        hash_type: Type of hash ('md5', 'sha1', 'sha256')
        
    Returns:
        Proposal object if found, None otherwise
    """
    # First, search in FileMetadata
    hash_field = f"{hash_type}_hash"
    query = {hash_field: file_hash}
    
    if project_id:
        query['project_id'] = project_id
        
    try:
        file_metadata = FileMetadata.objects.filter(**query).first()
        if file_metadata:
            # If the file is found in a project folder, try to find a related proposal
            # This assumes proposals are linked to projects
            proposals = Proposal.objects.filter(project_id=file_metadata.project_id)
            if proposals.exists():
                return proposals.first()
    except Exception as e:
        # Log error but continue the search
        print(f"Error searching FileMetadata: {e}")
    
    # Next, search in Proposal.attachments (assuming it's a JSONField)
    proposals = Proposal.objects.all()
    if project_id:
        proposals = proposals.filter(project_id=project_id)
    
    for proposal in proposals:
        try:
            attachments = proposal.attachments
            if not attachments:
                continue
                
            # Handle both string and dict formats
            if isinstance(attachments, str):
                import json
                try:
                    attachments = json.loads(attachments)
                except json.JSONDecodeError:
                    continue
            
            # Handle both list and dict formats
            if isinstance(attachments, list):
                for attachment in attachments:
                    if attachment.get(hash_field) == file_hash:
                        return proposal
            elif isinstance(attachments, dict):
                if attachments.get(hash_field) == file_hash:
                    return proposal
        except Exception as e:
            # Skip this proposal if there's an error
            print(f"Error checking proposal {proposal.id}: {e}")
            continue
    
    return None