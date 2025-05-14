import pdfplumber
import re
from datetime import datetime
from projects.models import Project
from files.models import Proposal

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

def parse_proposal_text(text):
    # Example regexes (customize for your format)
    date_match = re.search(r'(\w+ \d{1,2}, \d{4})', text)
    date = datetime.strptime(date_match.group(1), "%B %d, %Y") if date_match else None

    recipient_match = re.search(r'([A-Za-z ]+)\n([A-Za-z, ]+)\n([\d\w ,#\-]+)\n([\w ,]+)', text)
    recipient_name, recipient_company, recipient_address = None, None, None
    if recipient_match:
        recipient_name = recipient_match.group(1).strip()
        recipient_company = recipient_match.group(2).strip()
        recipient_address = f"{recipient_match.group(3).strip()}, {recipient_match.group(4).strip()}"

    # Extract sections by headings
    basic_services = extract_section(text, "BASIC SERVICES")
    additional_services = extract_section(text, "ADDITIONAL SERVICES")
    compensation = extract_section(text, "COMPENSATION")

    # ...more parsing as needed...

    return {
        "date": date,
        "recipient_name": recipient_name,
        "recipient_company": recipient_company,
        "recipient_address": recipient_address,
        "basic_services": parse_services(basic_services),
        "additional_services": parse_services(additional_services),
        "compensation": parse_compensation(compensation),
        # ...other fields...
    }

def extract_section(text, start_heading, end_heading=None):
    pattern = rf"{start_heading}(.*?){end_heading if end_heading else '$'}"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

def parse_services(section_text):
    # Example: split by numbered list
    return [item.strip() for item in re.split(r'\d+\.', section_text) if item.strip()]

def parse_compensation(section_text):
    # Custom logic to extract fee, terms, etc.
    return {"raw": section_text}

def extract_proposal_data(text):
    """Extract data from the proposal text."""
    proposal_data = {}
    proposal_data['proposal_date'] = extract_date(text)
    proposal_data['proposal_number'] = extract_proposal_number(text)
    proposal_data['client_name'] = extract_client_name(text)
    proposal_data['project_name'] = extract_project_name(text)
    proposal_data['project_description'] = extract_project_description(text)
    proposal_data['scope_of_work'] = extract_scope_of_work(text)
    proposal_data['total_cost'] = extract_total_cost(text)
    return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())