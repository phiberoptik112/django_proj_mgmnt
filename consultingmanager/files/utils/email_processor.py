import os
import logging
from typing import Optional
import extract_msg
from django.conf import settings

logger = logging.getLogger(__name__)

class EmailProcessingError(Exception):
    """Custom exception for email processing errors."""
    pass

def convert_msg_to_text(input_dir: str, output_file: str) -> Optional[str]:
    """
    Convert all .msg files in a directory to a single text file.
    
    Args:
        input_dir (str): Path to directory containing .msg files
        output_file (str): Path to output text file
    
    Returns:
        Optional[str]: Path to the output file if successful, None if failed
        
    Raises:
        EmailProcessingError: If there are issues processing the email files
        ValueError: If the input directory is invalid
    """
    if not os.path.isdir(input_dir):
        raise ValueError(f"Invalid directory path: {input_dir}")
        
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Walk through directory
            for root, dirs, files in os.walk(input_dir):
                for file in files:
                    if file.lower().endswith('.msg'):
                        msg_path = os.path.join(root, file)
                        try:
                            # Open the MSG file
                            msg = extract_msg.Message(msg_path)
                            
                            # Write email details to text file
                            outfile.write(f"\n{'='*50}\n")
                            outfile.write(f"From: {msg.sender}\n")
                            outfile.write(f"To: {msg.to}\n")
                            outfile.write(f"Subject: {msg.subject}\n")
                            outfile.write(f"Date: {msg.date}\n")
                            outfile.write(f"\nBody:\n{msg.body}\n")
                            
                            msg.close()
                        except Exception as e:
                            logger.error(f"Error processing {msg_path}: {str(e)}")
                            continue
                            
        return output_file
    except Exception as e:
        logger.error(f"Failed to process emails: {str(e)}")
        raise EmailProcessingError(f"Failed to process emails: {str(e)}")

def process_email_batch(input_dir: str, project_id: str) -> Optional[str]:
    """
    Process a batch of email files for a specific project.
    
    Args:
        input_dir (str): Directory containing the email files
        project_id (str): ID of the project these emails belong to
        
    Returns:
        Optional[str]: Path to the processed output file
    """
    # Create output directory if it doesn't exist
    output_dir = os.path.join(settings.MEDIA_ROOT, 'processed_emails', project_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    output_file = os.path.join(output_dir, f'email_summary_{project_id}.txt')
    
    try:
        return convert_msg_to_text(input_dir, output_file)
    except (ValueError, EmailProcessingError) as e:
        logger.error(f"Failed to process email batch for project {project_id}: {str(e)}")
        return None 