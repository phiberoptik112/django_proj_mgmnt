import pdfplumber
import re
from datetime import datetime
from projects.models import Project
from files.models import Proposal
import json
import logging
from pathlib import Path
import hashlib
from django.db.models import Q
from files.models import Proposal, FileMetadata
from files.utils.utilities import calculate_file_hash, find_proposal_by_hash
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proposal_parser.log'),
        logging.StreamHandler()
    ]
)

class ProposalParser:   
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.text = self.extract_text_from_pdf()
        # self.proposal_data = self.parse_proposal_text()
        self.logger = logging.getLogger(__name__)
        self.errors = []

    def extract_text_from_pdf(self):
        """
        Extract all text from the PDF file and return as a single string.
        Returns:
            str: The extracted text from the PDF, or an empty string if extraction fails.
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                return "\n".join(
                    page.extract_text() for page in pdf.pages if page.extract_text()
                )
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def extract_text(self):
        """Extract all text from the PDF"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                self.text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                return True
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {e}")
            return False
        

    def parse(self):
        """Parse the proposal text into a structured format"""
        if not self.text:
            success = self.extract_text()
            if not success:
                self.logger.error("Failed to extract text from PDF")
                return False
        self.extracted_data = {
            "date": self._extract_date(),
            "recipient_name": self._extract_recipient_name(),
            "recipient_company": self._extract_recipient_company(),
            "recipient_address": self._extract_recipient_address(),
            # "introduction": self._extract_introduction(),
            "basic_services": self._extract_basic_services(),
            "additional_services": self._extract_additional_services(),
            "compensation": self._extract_compensation(),
            # "attachments": self._extract_attachments()
        }
        return self.extracted_data
    def _extract_date(self):
        """Extract the date from the text"""
        patterns = [
            r'\b\d{2}/\d{2}/\d{4}\b',
            r'\b\d{2}-\d{2}-\d{4}\b',
            r'\b\d{2}\s[A-Za-z]{3}\s\d{4}\b',
            r'\b\d{2}\s[A-Za-z]{3}\.\s\d{4}\b',
            r'\b\d{2}\s[A-Za-z]{3}\.\s\d{4}\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                date_str = match.group(1)
                try:
                    if '/' in date_str:
                        return datetime.strptime(date_str, "%m/%d/%Y").date()
                    elif '-' in date_str:
                        return datetime.strptime(date_str, "%m-%d-%Y").date()
                    else:
                        return datetime.strptime(date_str, "%B %d, %Y").date()
                except ValueError:
                    continue
        
        return None
    
    def _extract_section(self, text, start_heading, end_heading=None):
        """Extract a section of text between headings."""
        start_pattern = re.escape(start_heading) + r'\s*'
        if end_heading:
            end_pattern = re.escape(end_heading) + r'\s*'
            pattern = f"{start_pattern}(.*?){end_pattern}"
        else:
            pattern = f"{start_pattern}(.*?)(?:$|(?:{self._get_all_headings_pattern()}))"
        self.logger.info(f"Extracting section with pattern: {pattern}")
        match = re.search(pattern, self.text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _get_all_headings_pattern(self):
        """Get a regex pattern for all headings in the text."""
        headings = set()
        for line in self.text.split('\n'):
            line = line.strip()
            if line:
                headings.add(line)
        return '|'.join(re.escape(h) for h in headings)
    

    def _extract_section_with_structure(self, heading, end_heading=None):
        """
        Extract a section with structured content including subheadings and numbered lists
        
        Args:
            heading: The main section heading (e.g., "BASIC SERVICES")
            end_heading: Optional ending heading to limit extraction
            
        Returns:
            A dictionary with structured content
        """
        # Get the raw section text first
        section_text = self._extract_section(heading, end_heading)
        if not section_text:
            return {"title": heading, "content": "", "items": []}
        
        # Split into lines for processing
        lines = section_text.split('\n')
        
        # Identify subheadings (typically underlined or in different format)
        # In your example, "Acoustical Testing Services" appears to be a subheading
        subheadings = []
        content_before_list = []
        current_line = 0
        
        # Extract any content before numbered list starts
        while current_line < len(lines) and not re.match(r'^\s*\d+\.', lines[current_line]):
            # Check if line looks like a subheading (non-empty, not starting with number)
            if lines[current_line].strip() and not lines[current_line].strip()[0].isdigit():
                subheadings.append(lines[current_line].strip())
            else:
                content_before_list.append(lines[current_line])
            current_line += 1
        
        # Extract the numbered list items with their content
        list_items = []
        current_item = None
        
        while current_line < len(lines):
            line = lines[current_line]
            
            # Check if this line starts a new numbered item
            number_match = re.match(r'^\s*(\d+)\.\s*(.*)', line)
            
            if number_match:
                # If we were processing a previous item, add it to our list
                if current_item:
                    list_items.append(current_item)
                
                # Start a new item
                item_number = int(number_match.group(1))
                item_content = number_match.group(2)
                current_item = {
                    "number": item_number,
                    "content": [item_content],
                    "standards": []  # Will store any referenced standards
                }
            elif current_item and line.strip():
                # Continue with the current item
                current_item["content"].append(line)
                
                # Check for standards references (ASTM, etc.)
                standards_match = re.findall(r'(ASTM [A-Z]\d+-\d+)', line)
                if standards_match:
                    current_item["standards"].extend(standards_match)
                    
            current_line += 1
        
        # Don't forget to add the last item
        if current_item:
            list_items.append(current_item)
        
        # Clean up the content in each item
        for item in list_items:
            item["content"] = " ".join([line.strip() for line in item["content"]]).strip()
        
        # Return structured data
        return {
            "title": heading,
            "subheadings": subheadings,
            "introduction": " ".join(content_before_list).strip(),
            "items": list_items
        }
    
    def _extract_basic_services(self):
        """Extract and structure the Basic Services section"""
        
        # Use the structured extraction method
        basic_services = self._extract_section_with_structure("BASIC SERVICES", "ADDITIONAL SERVICES")
        
        # Further process to identify specific types of services
        # For example, identify service categories from subheadings
        service_types = []
        for subheading in basic_services.get("subheadings", []):
            if "testing" in subheading.lower():
                service_types.append("testing")
            elif "design" in subheading.lower():
                service_types.append("design")
            # Add more categories as needed
        
        # Add service types to the structure
        basic_services["service_types"] = service_types
        
        # Format for database storage - convert to format expected by your model
        formatted_for_db = []
        for item in basic_services.get("items", []):
            formatted_for_db.append({
                "id": item["number"],
                "description": item["content"],
                "standards": item["standards"],
                "type": service_types[0] if service_types else "general"  # Default to first type or "general"
            })
        
        return formatted_for_db
    
    def _extract_additional_services(self):
        """Extract and structure the Additional Services section"""
        return self._extract_section_with_structure("ADDITIONAL SERVICES", "COMPENSATION")
    def _extract_compensation(self):
        """Extract and structure the Compensation section"""
        return self._extract_section_with_structure("COMPENSATION", "sincerely")
    
    

    def to_model_dict(self):
        """Convert the extracted data to a dictionary that can be used to create a Proposal model instance"""
        if not self.extracted_data:
            self.parse()

        basic_services = self._extract_basic_services()
        model_data = {
            "date": self.extracted_data["date"],
            "recipient_name": self.extracted_data["recipient_name"],
            "recipient_company": self.extracted_data["recipient_company"], 
            "recipient_address": self.extracted_data["recipient_address"],
            # "introduction": self.extracted_data["introduction"],
            "basic_services": json.dumps(basic_services),
            "additional_services": self.extracted_data["additional_services"],
            "compensation": self.extracted_data["compensation"],
            # "attachments": self.extracted_data["attachments"],
            "status": "draft",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return model_data

    def check_duplicate_by_hash(self, project_id=None):
        """
        Check if this proposal already exists by comparing file hash
        
        Args:
            project_id: Optional project ID to limit the search
            
        Returns:
            tuple: (is_duplicate, existing_proposal, hash_value)
        """
        try:
            # Calculate MD5 hash
            md5_hash = calculate_file_hash(self.pdf_path, 'md5')
            
            # Optional: also calculate SHA256 for higher security
            # sha256_hash = calculate_file_hash(self.pdf_path, 'sha256')
            
            # Search for proposal with this hash
            existing_proposal = find_proposal_by_hash(md5_hash, project_id, 'md5')
            
            if existing_proposal:
                return True, existing_proposal, md5_hash
            
            return False, None, md5_hash
            
        except Exception as e:
            # Log the error
            print(f"Error checking for duplicate: {e}")
            # Return the error but don't stop the import process
            return False, None, None
    
    def store_file_hash(self, proposal, filename=None):
        """
        Store the file hash in the proposal's attachments
        
        Args:
            proposal: Proposal object to update
            filename: Original filename (optional)
            
        Returns:
            bool: Success or failure
        """
        try:
            # Calculate hashes
            md5_hash = calculate_file_hash(self.pdf_path, 'md5')
            sha256_hash = calculate_file_hash(self.pdf_path, 'sha256')
            
            # Get file size
            file_size = os.path.getsize(self.pdf_path)
            
            # Prepare attachment info
            attachment_info = {
                'filename': filename or os.path.basename(self.pdf_path),
                'md5_hash': md5_hash,
                'sha256_hash': sha256_hash,
                'size_bytes': file_size,
                'mime_type': 'application/pdf'
            }
            
            # Update the proposal's attachments
            import json
            
            # Handle case where attachments is None or empty
            if not proposal.attachments:
                proposal.attachments = json.dumps([attachment_info])
            else:
                # Handle string format
                if isinstance(proposal.attachments, str):
                    try:
                        existing_attachments = json.loads(proposal.attachments)
                    except json.JSONDecodeError:
                        existing_attachments = []
                else:
                    existing_attachments = proposal.attachments
                
                # Handle both list and dict formats
                if isinstance(existing_attachments, list):
                    existing_attachments.append(attachment_info)
                else:
                    existing_attachments = [existing_attachments, attachment_info]
                
                proposal.attachments = json.dumps(existing_attachments)
            
            # Save the proposal
            proposal.save()
            return True
            
        except Exception as e:
            # Log the error
            print(f"Error storing file hash: {e}")
            return False

    def _extract_recipient_block(self):
        """
        Extracts the block of text containing recipient info (name, company, address)
        which appears after the date and before 'RE:' or 'BASIC SERVICES'.
        """
        # Find the date in the text
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
        date_match = re.search(date_pattern, self.text)
        if not date_match:
            return ""
        start_idx = date_match.end()

        # Find the next heading ("RE:" or "BASIC SERVICES")
        after_date = self.text[start_idx:]
        end_match = re.search(r'\b(RE:|BASIC SERVICES)\b', after_date)
        end_idx = end_match.start() if end_match else len(after_date)

        # Extract the block and clean up
        recipient_block = after_date[:end_idx].strip()
        # Remove empty lines and strip
        lines = [line.strip() for line in recipient_block.split('\n') if line.strip()]
        return lines

    def _extract_recipient_name(self):
        """Extract the recipient's name from the recipient block."""
        lines = self._extract_recipient_block()
        return lines[0] if lines else ""

    def _extract_recipient_company(self):
        """Extract the recipient's company from the recipient block."""
        lines = self._extract_recipient_block()
        return lines[1] if len(lines) > 1 else ""

    def _extract_recipient_address(self):
        """Extract the recipient's address from the recipient block."""
        lines = self._extract_recipient_block()
        if len(lines) > 2:
            return " ".join(lines[2:])
        return ""