"""
PIF Excel parser utilities.

Attempts to read the PIF spreadsheet and extract key fields that map to
`billing.models.ProjectInformationForm` and a few Project fields (budget).

Heuristic-based to be resilient to form layout changes.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional

import pandas as pd


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
    try:
        df = pd.read_excel(file_path, engine='openpyxl', header=None)
    except Exception:
        return {}

    # Build a list of (row, col, text)
    cells = []
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            val = df.iat[r, c]
            if pd.isna(val):
                continue
            text = str(val).strip()
            if text:
                cells.append((r, c, text))

    # Helper to get neighbor cell to the right or below
    def neighbor_value(r: int, c: int) -> Optional[str]:
        # Prefer right cell
        if c + 1 < df.shape[1]:
            right = df.iat[r, c + 1]
            if not pd.isna(right) and str(right).strip():
                return str(right).strip()
        # Fallback: below
        if r + 1 < df.shape[0]:
            below = df.iat[r + 1, c]
            if not pd.isna(below) and str(below).strip():
                return str(below).strip()
        return None

    # Patterns to look for -> output field
    PATTERNS = [
        ("project number", "project_number"),
        ("project name", "project_name"),
        ("dlaa office", "dlaa_office"),
        ("office", "dlaa_office"),
        ("city", "project_location_city"),
        ("state", "project_location_state"),
        ("originator", "originator"),
        ("date entered", "date_entered"),
        ("client name", "client_name"),
        ("billing contact email", "billing_contact_email"),
        ("billing contact", "billing_contact"),
        ("client project name", "client_project_name"),
        ("purchase order", "purchase_order_number"),
        ("po number", "purchase_order_number"),
        ("phone", "phone"),
        ("secondary contact email", "secondary_contact_email"),
        ("secondary contact", "secondary_contact"),
        ("project manager", "project_manager"),
        ("project start", "project_start_date"),
        ("fee contract amount", "fee_contract_amount"),
        ("contract amount", "fee_contract_amount"),
        ("fee amount", "fee_contract_amount"),
        ("type of contract", "type_of_contract"),
        ("expenses", "expenses"),
        ("special negotiated rates", "special_negotiated_rates"),
        ("special invoice instructions", "special_invoice_instructions"),
        ("retainer received", "retainer_received"),
        ("additional comments", "additional_comments"),
    ]

    result: Dict[str, Any] = {}
    used_keys = set()

    for r, c, text in cells:
        lower = text.lower()
        for needle, field_name in PATTERNS:
            if needle in lower and field_name not in used_keys:
                val = neighbor_value(r, c)
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
                else:
                    result[field_name] = val
                used_keys.add(field_name)

    return result


