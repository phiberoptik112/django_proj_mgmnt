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

import pandas as pd

logger = logging.getLogger(__name__)


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


def parse_pif_excel(file_path: str) -> Dict[str, Any]:
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
    """
    logger.info(f"Parsing PIF Excel file: {file_path}")
    try:
        xls = pd.ExcelFile(file_path, engine='openpyxl')
        logger.info(f"Successfully opened Excel file with {len(xls.sheet_names)} sheets: {xls.sheet_names}")
    except Exception as e:
        logger.error(f"Failed to open Excel file {file_path}: {e}")
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

    def neighbor_value(df: pd.DataFrame, r: int, c: int) -> Optional[str]:
        # Scan up to 5 cells to the right for first non-empty
        for dc in range(1, 6):
            if c + dc >= df.shape[1]:
                break
            right = df.iat[r, c + dc]
            if not pd.isna(right) and str(right).strip():
                return str(right).strip()
        # Then scan up to 3 cells below in same column
        for dr in range(1, 4):
            if r + dr >= df.shape[0]:
                break
            below = df.iat[r + dr, c]
            if not pd.isna(below) and str(below).strip():
                return str(below).strip()
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
        ("client name", "client_name"),
        ("client", "client_name"),
        ("billing contact email", "billing_contact_email"),
        ("billing email", "billing_contact_email"),
        ("billing contact", "billing_contact"),
        ("client project name", "client_project_name"),
        ("purchase order", "purchase_order_number"),
        ("po number", "purchase_order_number"),
        ("po #", "purchase_order_number"),
        ("phone", "phone"),
        ("secondary contact email", "secondary_contact_email"),
        ("secondary contact", "secondary_contact"),
        ("project manager", "project_manager"),
        ("manager", "project_manager"),
        ("pm", "project_manager"),
        ("project start", "project_start_date"),
        ("start date", "project_start_date"),
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

    # Iterate sheets and extract
    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            continue

        cells = build_cells(df)
        for r, c, text in cells:
            lower = text.lower()
            for needle, field_name in PATTERNS:
                if needle in lower and field_name not in used_keys:
                    val = neighbor_value(df, r, c)
                    # If no neighbor, try inline "Label: value" in same cell
                    if val is None and ":" in text:
                        candidate = text.split(":", 1)[1].strip()
                        if candidate:
                            val = candidate
                    if val is None:
                        continue
                    # Convert some fields
                    if field_name in ("fee_contract_amount", "expenses"):
                        dec = _to_decimal(val)
                        if dec is not None:
                            result[field_name] = dec
                            if field_name == "fee_contract_amount":
                                result["project_budget"] = dec
                    elif field_name in ("date_entered", "project_start_date"):
                        dt = _to_date(val)
                        if dt is not None:
                            result[field_name] = dt
                    elif field_name == "tax_locations":
                        parts = [p.strip() for p in str(val).replace(";", ",").split(",") if p.strip()]
                        if parts:
                            result[field_name] = parts
                    else:
                        result[field_name] = val
                    used_keys.add(field_name)
                    raw_pairs.append((needle, str(val)))

            # Collect generic raw pairs even if not mapped
            val2 = neighbor_value(df, r, c)
            if val2 is None and ":" in text:
                right = text.split(":", 1)
                if len(right) == 2 and right[1].strip():
                    val2 = right[1].strip()
                    label = right[0].strip()
                    raw_pairs.append((label, str(val2)))
            elif val2 is not None:
                raw_pairs.append((text, str(val2)))

    # Deduplicate raw pairs preserving order
    seen = set()
    deduped = []
    for k, v in raw_pairs:
        key = (k.lower(), str(v))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((k, v))

    result["raw_pairs"] = deduped[:150]
    
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


