import pdfplumber
import re
from datetime import datetime
from projects.models import Project
from files.models import Proposal
import json
import logging
from pathlib import Path

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
        self.proposal_data = self.parse_proposal_text()
        self.logger = logging.getLogger(__name__)
        self.errors = []

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
            "subject": self._extract_subject(),
            "reference": self._extract_reference(),
            "introduction": self._extract_introduction(),
            "basic_services": self._extract_basic_services(),
            "additional_services": self._extract_additional_services(),
            "compensation": self._extract_compensation(),
            "terms": self._extract_terms(),
            "attachments": self._extract_attachments()
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
        start_pattern = r'(?i)' + re.escape(start_heading) + r'\s*'
        if end_heading:
            end_pattern = r'(?i)' + re.escape(end_heading) + r'\s*'
            pattern = f"{start_pattern}(.*?){end_pattern}"
        else:
            pattern = f"{start_pattern}(.*?)(?:$|(?i)(?:{self._get_all_headings_pattern()}))"
        self.logger.info(f"Extracting section with pattern: {pattern}")
        match = re.search(pattern, self.text, re.DOTALL)
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
    
    def to_model_dict(self):
        """Convert the extracted data to a dictionary that can be used to create a Proposal model instance"""
        model_data = {
            "date": self.extracted_data["date"],
            "recipient_name": self.extracted_data["recipient_name"],
            "recipient_company": self.extracted_data["recipient_company"], 
            "recipient_address": self.extracted_data["recipient_address"],
            "subject": self.extracted_data["subject"],
            "reference": self.extracted_data["reference"],
            "introduction": self.extracted_data["introduction"],
            "basic_services": self.extracted_data["basic_services"],
            "additional_services": self.extracted_data["additional_services"],
            "compensation": self.extracted_data["compensation"],
            "terms": self.extracted_data["terms"],
            "attachments": self.extracted_data["attachments"],
            "status": "draft",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        return model_data

    
    # def extract_proposal_data(text):
    #     """Extract data from the proposal text."""
    #     proposal_data = {}
    #     proposal_data['proposal_date'] = extract_date(text)
    #     proposal_data['proposal_number'] = extract_proposal_number(text)
    #     proposal_data['client_name'] = extract_client_name(text)
    #     proposal_data['project_name'] = extract_project_name(text)
    #     proposal_data['project_description'] = extract_project_description(text)
    #     proposal_data['scope_of_work'] = extract_scope_of_work(text)
    #     proposal_data['total_cost'] = extract_total_cost(text)
    #     return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())