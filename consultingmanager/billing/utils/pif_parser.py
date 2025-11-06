"""
PIF Excel parser utilities.

Attempts to read the PIF spreadsheet and extract key fields that map to
`billing.models.ProjectInformationForm` and a few Project fields (budget).

Heuristic-based to be resilient to form layout changes.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List, Tuple
import logging
import re
from pathlib import Path

import pandas as pd

from .volume_access import diagnose_file_access, check_volume_accessible, refresh_volume_access

logger = logging.getLogger(__name__)

# Layout modes for different PIF sections
MODE_DEFAULT = 1  # Column 0 = label, Column 1 = value
MODE_CLIENT_SECTION = 2  # Column 0 = header, Column 1 = label, Column 2 = value
MODE_PROJECT_SECTION = 3  # Column 0 = label, Column 1 = value (after Project Manager)
MODE_TABLE = 4  # Table structure with column headers


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        # pandas often gives floats; convert safely
        s = str(value).strip().replace(',', '')
        if not s:
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _to_date(value: Any):
    if value is None or str(value).strip() == '':
        return None
    try:
        dt = pd.to_datetime(value, errors='coerce')
        if pd.isna(dt):
            return None
        # return a date object for Django DateField
        return dt.date()
    except Exception:
        return None


def _is_likely_label(text: str) -> bool:
    """
    Detect if text looks like a label rather than a value.
    This helps prevent extracting labels as values in the PIF parsing.
    """
    if not text or len(text) > 100:
        return False
    
    lower = text.lower().strip()
    
    # Common label keywords that appear in PIF form labels
    label_keywords = [
        'name', 'contact', 'address', 'city', 'state', 'zip', 
        'phone', 'fax', 'email', 'date', 'number', 'amount',
        'manager', 'project', 'client', 'billing', 'purchase',
        'information', 'order', 'type', 'contract', 'expenses',
        'invoice', 'retainer', 'instructions', 'received', 'line',
        'folder', 'originator', 'entered', 'code', 'phase',
        'design', 'development', 'construction', 'documents',
        'bidding', 'negotiation', 'administration', 'general',
        'special', 'max', 'total', 'professional', 'services'
    ]
    
    # Label patterns
    if lower.endswith(':'):
        return True
    
    # Check if it contains label keywords
    if any(keyword in lower for keyword in label_keywords):
        word_count = len(lower.split())
        # Short phrases (4 words or less) with label keywords are likely labels
        if word_count <= 4:
            return True
    
    # Check for common label patterns like "Line 1", "Line 2"
    if re.match(r'^line\s+\d+$', lower):
        return True
    
    return False


def _detect_mode_transition(text: str, column: int, current_mode: int) -> int:
    """
    Detect if we're transitioning to a new layout mode.
    Returns the new mode or current mode if no change.
    
    The PIF form has different column layouts:
    - Mode 1 (DEFAULT): Column 0 = label, Column 1 = value
    - Mode 2 (CLIENT_SECTION): Column 0 = section header, Column 1 = label, Column 2 = value
    - Mode 3 (PROJECT_SECTION): Column 0 = label, Column 1 = value (after "Project Manager")
    - Mode 4 (TABLE): Table structure for Billing Phases
    """
    lower = text.lower().strip()
    
    # Mode 2: Client Information sections
    client_section_indicators = [
        "client information",
        "address if different"
    ]
    if column == 0 and any(ind in lower for ind in client_section_indicators):
        logger.debug(f"Detected CLIENT_SECTION mode at column {column}: {text}")
        return MODE_CLIENT_SECTION
    
    # Mode 3: Project section (starts with Project Manager)
    # This switches back from CLIENT_SECTION to standard layout
    if column == 0 and "project manager" in lower and current_mode == MODE_CLIENT_SECTION:
        logger.debug(f"Detected PROJECT_SECTION mode at column {column}: {text}")
        return MODE_PROJECT_SECTION
    
    # Mode 4: Billing Phases table
    if "billing phases" in lower and "lump sum" in lower:
        logger.debug(f"Detected TABLE mode: {text}")
        return MODE_TABLE
    
    return current_mode


def parse_pif_excel(file_path: str, use_second_sheet_only: bool = True) -> Dict[str, Any]:
    """
    Parse a PIF Excel file and return a dict of extracted fields.

    Returns keys matching `ProjectInformationForm` where possible:
    - project_number, project_name, dlaa_office,
      project_location_city, project_location_state, originator, date_entered,
      client_name, billing_contact, billing_contact_email, client_project_name,
      purchase_order_number, phone, secondary_contact, secondary_contact_email,
      project_manager, project_start_date, fee_contract_amount,
      type_of_contract, expenses, special_negotiated_rates,
      special_invoice_instructions, retainer_received, additional_comments

    And also: project_budget (Decimal) as a suggested Project.budget value.

    Args:
        file_path: Path to the Excel file
        use_second_sheet_only: If True, only parse the second sheet for project data (default True)
    """
    logger.info(f"Parsing PIF Excel file: {file_path}")
    
    # Check file accessibility first (especially for network volumes)
    file_check = check_volume_accessible(file_path)
    
    if not file_check.get('exists'):
        # Attempt to refresh volume access if it's a network volume
        if file_check.get('volume_name'):
            logger.warning(f"File not found at {file_path}. Attempting to refresh volume access...")
            refresh_result = refresh_volume_access(file_check['volume_name'])
            logger.info(f"Volume refresh result: {refresh_result['message']}")
            
            # Re-check after refresh attempt
            file_check = check_volume_accessible(file_path)
        
        if not file_check.get('exists'):
            # Provide comprehensive diagnostics
            diagnosis = diagnose_file_access(file_path)
            logger.error(f"File does not exist: {file_path}")
            logger.error(f"Volume check: {file_check}")
            if diagnosis.get('suggestions'):
                for suggestion in diagnosis['suggestions']:
                    logger.error(f"  Suggestion: {suggestion}")
            return {}
    
    if not file_check.get('readable'):
        logger.error(f"File exists but is not readable: {file_path}")
        logger.error(f"File check details: {file_check}")
        if file_check.get('volume_name'):
            diagnosis = diagnose_file_access(file_path)
            if diagnosis.get('suggestions'):
                for suggestion in diagnosis['suggestions']:
                    logger.error(f"  Suggestion: {suggestion}")
        return {}
    
    try:
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        logger.info(f"Successfully opened Excel file with {len(xls.sheet_names)} sheets: {xls.sheet_names}")
    except FileNotFoundError as e:
        # Even though we checked, sometimes the file can disappear between checks
        logger.error(f"File not found when opening Excel file {file_path}: {e}")
        if file_check.get('volume_name'):
            diagnosis = diagnose_file_access(file_path)
            logger.error(f"Diagnosis: {diagnosis}")
        return {}
    except PermissionError as e:
        logger.error(f"Permission denied opening Excel file {file_path}: {e}")
        logger.error(f"File check details: {file_check}")
        return {}
    except Exception as e:
        logger.error(f"Failed to open Excel file {file_path}: {e}")
        logger.error(f"File check details: {file_check}")
        # Include error type for better debugging
        logger.error(f"Error type: {type(e).__name__}")
        return {}

    def build_cells(df: pd.DataFrame) -> List[Tuple[int, int, str]]:
        out = []
        for r in range(df.shape[0]):
            for c in range(df.shape[1]):
                val = df.iat[r, c]
                if pd.isna(val):
                    continue
                text = str(val).strip()
                if text:
                    out.append((r, c, text))
        return out

    def neighbor_value(df: pd.DataFrame, r: int, c: int, label_text: str = "", mode: int = MODE_DEFAULT) -> Optional[str]:
        """
        Extract value for a label based on current layout mode.
        
        Mode-specific column mappings:
        - MODE_DEFAULT/PROJECT_SECTION: Column 0 = label, Column 1 = value
        - MODE_CLIENT_SECTION: Column 1 = label, Column 2 = value
        
        Validates that extracted values don't look like labels themselves.
        """
        
        # Mode-specific extraction logic
        if mode == MODE_CLIENT_SECTION:
            # In client sections: label in col 1, value in col 2
            if c == 1:  # Label is in column 1
                if 2 < df.shape[1]:
                    val = df.iat[r, 2]
                    if not pd.isna(val):
                        val_str = str(val).strip()
                        if val_str and not _is_likely_label(val_str):
                            logger.debug(f"MODE_CLIENT_SECTION: Found value in col 2 for label '{label_text}': {val_str}")
                            return val_str
        
        elif mode in (MODE_DEFAULT, MODE_PROJECT_SECTION):
            # Standard mode: label in col 0, value in col 1
            if c == 0:  # Label is in column 0
                if 1 < df.shape[1]:
                    val = df.iat[r, 1]
                    if not pd.isna(val):
                        val_str = str(val).strip()
                        if val_str and not _is_likely_label(val_str):
                            logger.debug(f"MODE_DEFAULT: Found value in col 1 for label '{label_text}': {val_str}")
                            return val_str
        
        # Fallback: try general column search (for flexibility)
        # First, try columns 2-5 on the same row
        value_columns = [2, 3, 4, 5]
        for vc in value_columns:
            if vc >= df.shape[1]:
                continue
            val = df.iat[r, vc]
            if not pd.isna(val):
                val_str = str(val).strip()
                if val_str and not _is_likely_label(val_str):
                    logger.debug(f"Fallback: Found value in col {vc} for label '{label_text}': {val_str}")
                    return val_str
        
        # Try 1-2 cells to the right if label is in later columns
        for dc in range(1, 3):
            if c + dc >= df.shape[1]:
                break
            right = df.iat[r, c + dc]
            if not pd.isna(right):
                val_str = str(right).strip()
                if val_str and not _is_likely_label(val_str):
                    logger.debug(f"Fallback: Found value {dc} cells right for label '{label_text}': {val_str}")
                    return val_str
        
        # Last resort: try 1 cell below (for wrapped labels)
        if r + 1 < df.shape[0]:
            below = df.iat[r + 1, c]
            if not pd.isna(below):
                val_str = str(below).strip()
                if val_str and not _is_likely_label(val_str):
                    logger.debug(f"Fallback: Found value below for label '{label_text}': {val_str}")
                    return val_str
        
        return None

    # Patterns to look for -> output field
    PATTERNS = [
        ("project number", "project_number"),
        ("project no", "project_number"),
        ("project #", "project_number"),
        ("proj no", "project_number"),
        ("project name", "project_name"),
        ("project title", "project_name"),
        ("dlaa office", "dlaa_office"),
        ("office", "dlaa_office"),
        ("city", "project_location_city"),
        ("state", "project_location_state"),
        ("originator", "originator"),
        ("date entered", "date_entered"),
        ("date", "date_entered"),
        
        # Client Information fields (more specific patterns first)
        ("name (firm or individual)", "client_name"),
        ("firm or individual", "client_name"),
        ("client name", "client_name"),
        ("billing contact email", "billing_contact_email"),
        ("secondary contact email", "secondary_contact_email"),
        ("billing email", "billing_contact_email"),
        ("billing contact", "billing_contact"),
        ("secondary contact", "secondary_contact"),
        ("contact", "billing_contact"),  # General "Contact" - must come after specific contact patterns
        ("client code", "client_code"),
        ("billing address line 1", "billing_address_line_1"),
        ("billing address line 2", "billing_address_line_2"),
        ("address line 1", "billing_address_line_1"),
        ("address line 2", "billing_address_line_2"),
        ("zip", "billing_zip"),
        ("phone", "phone"),
        ("fax", "fax"),
        ("email", "billing_contact_email"),  # General "Email" - must come after specific email patterns
        
        ("client project name", "client_project_name"),
        ("purchase order number", "purchase_order_number"),
        ("purchase order", "purchase_order_number"),
        ("po number", "purchase_order_number"),
        ("po #", "purchase_order_number"),
        ("project manager", "project_manager"),
        ("manager", "project_manager"),
        ("pm", "project_manager"),
        ("project start date", "project_start_date"),
        ("project start", "project_start_date"),
        ("start date", "project_start_date"),
        ("fee (contract amount)", "fee_contract_amount"),
        ("fee contract amount", "fee_contract_amount"),
        ("contract amount", "fee_contract_amount"),
        ("contract value", "fee_contract_amount"),
        ("total fee", "fee_contract_amount"),
        ("fee amount", "fee_contract_amount"),
        ("type of contract", "type_of_contract"),
        ("contract type", "type_of_contract"),
        ("expenses", "expenses"),
        ("special negotiated rates", "special_negotiated_rates"),
        ("special invoice instructions", "special_invoice_instructions"),
        ("retainer received", "retainer_received"),
        ("additional comments", "additional_comments"),
        ("tax", "tax_locations"),
    ]

    result: Dict[str, Any] = {}
    used_keys = set()
    raw_pairs: List[Tuple[str, str]] = []
    field_mappings: List[Dict[str, Any]] = []  # Track all potential field mappings with confidence
    all_labels_seen = set()  # Track all labels to detect label-as-value issues

    # Determine which sheets to parse
    sheets_to_parse = []
    if use_second_sheet_only and len(xls.sheet_names) >= 2:
        sheets_to_parse = [xls.sheet_names[1]]  # Use only the second sheet (index 1)
        logger.info(f"Using second sheet only: {sheets_to_parse[0]}")
    else:
        sheets_to_parse = xls.sheet_names
        logger.info(f"Using all sheets: {sheets_to_parse}")

    # Iterate sheets and extract
    for sheet_name in sheets_to_parse:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            continue

        cells = build_cells(df)
        current_section = None  # Track hierarchical section headers
        current_mode = MODE_DEFAULT  # Track current parsing mode
        
        for r, c, text in cells:
            lower = text.lower()
            all_labels_seen.add(lower)
            
            # Detect mode transitions
            new_mode = _detect_mode_transition(text, c, current_mode)
            if new_mode != current_mode:
                logger.info(f"Mode transition: {current_mode} -> {new_mode} at row {r}, col {c}, text: '{text}'")
                current_mode = new_mode
                
                # Set section header when entering CLIENT_SECTION mode
                if current_mode == MODE_CLIENT_SECTION:
                    current_section = text
                    logger.info(f"Set section header: {current_section}")
                # Clear section header when leaving CLIENT_SECTION mode
                elif current_mode == MODE_PROJECT_SECTION:
                    logger.info(f"Cleared section header (was: {current_section})")
                    current_section = None
            
            for needle, field_name in PATTERNS:
                if needle in lower:
                    val = neighbor_value(df, r, c, text, mode=current_mode)
                    # If no neighbor, try inline "Label: value" in same cell
                    if val is None and ":" in text:
                        candidate = text.split(":", 1)[1].strip()
                        if candidate and not _is_likely_label(candidate):
                            val = candidate
                    if val is None:
                        continue

                    # Calculate confidence score
                    confidence = 0.0
                    if needle == lower:
                        confidence = 1.0  # Exact match
                    elif lower.startswith(needle):
                        confidence = 0.9  # Starts with
                    elif needle in lower:
                        confidence = 0.7  # Contains

                    # Only use this mapping if we haven't seen this field yet
                    if field_name not in used_keys:
                        # Build label with section prefix - only in CLIENT_SECTION mode
                        display_label = text
                        if current_mode == MODE_CLIENT_SECTION and current_section:
                            # Only add section prefix if label is in column 1 (sub-field)
                            if c == 1 and current_section.lower() not in lower:
                                display_label = f"{current_section} - {text}"
                        
                        # Convert some fields
                        converted_val = val
                        if field_name in ("fee_contract_amount", "expenses"):
                            dec = _to_decimal(val)
                            if dec is not None:
                                converted_val = dec
                                result[field_name] = dec
                                if field_name == "fee_contract_amount":
                                    result["project_budget"] = dec
                        elif field_name in ("date_entered", "project_start_date"):
                            dt = _to_date(val)
                            if dt is not None:
                                converted_val = dt
                                result[field_name] = dt
                        elif field_name == "tax_locations":
                            parts = [p.strip() for p in str(val).replace(";", ",").split(",") if p.strip()]
                            if parts:
                                converted_val = parts
                                result[field_name] = parts
                        else:
                            result[field_name] = val

                        used_keys.add(field_name)
                        field_mappings.append({
                            "label": display_label,
                            "value": str(val),
                            "converted_value": converted_val,
                            "field_name": field_name,
                            "confidence": confidence,
                            "sheet": sheet_name,
                            "auto_mapped": True
                        })

            # Collect generic raw pairs even if not mapped
            val2 = neighbor_value(df, r, c, text, mode=current_mode)
            if val2 is None and ":" in text:
                right = text.split(":", 1)
                if len(right) == 2 and right[1].strip():
                    candidate_val = right[1].strip()
                    if not _is_likely_label(candidate_val):
                        val2 = candidate_val
                        label = right[0].strip()
                        # Add section prefix only in CLIENT_SECTION mode
                        if current_mode == MODE_CLIENT_SECTION and current_section:
                            if c == 1 and current_section.lower() not in label.lower():
                                label = f"{current_section} - {label}"
                        raw_pairs.append((label, str(val2)))
            elif val2 is not None:
                # Add section prefix only in CLIENT_SECTION mode
                label = text
                if current_mode == MODE_CLIENT_SECTION and current_section:
                    if c == 1 and current_section.lower() not in label.lower():
                        label = f"{current_section} - {text}"
                raw_pairs.append((label, str(val2)))

    # Deduplicate raw pairs preserving order - fix the duplicate issue
    seen = set()
    deduped = []
    for k, v in raw_pairs:
        # More strict deduplication: use both label and value, case-insensitive
        key = (k.lower().strip(), str(v).strip())
        if key in seen:
            continue
        
        # Skip if value looks like a label
        if _is_likely_label(str(v)):
            logger.debug(f"Skipping raw pair - value looks like label: {k} = {v}")
            continue
        
        # Skip if value matches a known label (case-insensitive)
        if str(v).lower().strip() in all_labels_seen:
            logger.debug(f"Skipping raw pair - value matches seen label: {k} = {v}")
            continue
        
        # Skip if value is empty or just whitespace
        if not str(v).strip():
            continue
        
        seen.add(key)
        deduped.append((k, v))

    result["raw_pairs"] = deduped[:150]
    result["field_mappings"] = field_mappings
    
    # Build CSV-style previews for ALL sheets with content
    csv_previews = []
    logger.info(f"Building CSV previews from {len(xls.sheet_names)} sheets")
    try:
        # Process each sheet to create previews
        for sheet_name in xls.sheet_names:
            try:
                # Read without headers first to get raw data
                df0 = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                logger.info(f"Read sheet '{sheet_name}': {df0.shape[0]} rows, {df0.shape[1]} columns")
            except Exception as e:
                logger.error(f"Error reading sheet {sheet_name}: {e}")
                continue
                
            if df0.empty:
                logger.info(f"Sheet '{sheet_name}' is empty, skipping")
                continue
                
            # Find non-empty columns (any column with at least one non-null value)
            non_empty_cols = []
            for col_idx in range(df0.shape[1]):
                if df0.iloc[:, col_idx].notna().any():
                    non_empty_cols.append(col_idx)
            
            if len(non_empty_cols) == 0:
                logger.info(f"Sheet '{sheet_name}' has no non-empty columns, skipping")
                continue
                
            # Limit to first 30 rows and 30 columns for performance
            max_rows = min(30, df0.shape[0])
            max_cols = min(30, len(non_empty_cols))
            
            # Create headers (use column indices if no meaningful headers)
            headers = [f"Col_{i+1}" for i in non_empty_cols[:max_cols]]
            
            # Extract rows
            rows = []
            for row_idx in range(max_rows):
                row = []
                for col_idx in non_empty_cols[:max_cols]:
                    cell_value = df0.iloc[row_idx, col_idx]
                    if pd.isna(cell_value):
                        row.append("")
                    else:
                        # Convert to string and limit length for display
                        cell_str = str(cell_value)
                        if len(cell_str) > 100:
                            cell_str = cell_str[:97] + "..."
                        row.append(cell_str)
                rows.append(row)
            
            # Only create preview if we have actual data
            if rows and any(any(cell.strip() for cell in row) for row in rows):
                sheet_preview = {
                    "sheet_name": sheet_name,
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "total_rows_in_sheet": df0.shape[0],
                    "total_cols_in_sheet": df0.shape[1],
                    "non_empty_cols": len(non_empty_cols),
                }
                csv_previews.append(sheet_preview)
                logger.info(f"Created CSV preview from sheet '{sheet_name}': {len(rows)} rows, {len(headers)} columns")
                
    except Exception as e:
        logger.error(f"Error creating CSV previews: {e}")
        csv_previews = []

    # Store all sheet previews
    if csv_previews:
        result["csv_previews"] = csv_previews
        result["total_sheets"] = len(xls.sheet_names)
        result["sheets_with_data"] = len(csv_previews)
        # Keep the first sheet as the primary preview for backward compatibility
        result["csv_preview"] = csv_previews[0]
        logger.info(f"Created {len(csv_previews)} sheet previews out of {len(xls.sheet_names)} total sheets")
    else:
        # If no preview could be created, add debug info
        error_preview = {
            "sheet_name": "No data found",
            "headers": ["Error"],
            "rows": [["Unable to read Excel file or no data found"]],
            "row_count": 1,
            "error": "No readable data found in any sheet"
        }
        result["csv_preview"] = error_preview
        result["csv_previews"] = [error_preview]
        result["total_sheets"] = len(xls.sheet_names) if 'xls' in locals() else 0
        result["sheets_with_data"] = 0
    
    return result


