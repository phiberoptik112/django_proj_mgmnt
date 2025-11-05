# Expanded Pattern Matching for PIF Parser

## What Was Added

Extended the PATTERNS list to capture all Client Information fields that were previously not being matched.

## New Patterns Added

### Client Information Section Fields

| Pattern | Maps To Field | Example Value |
|---------|---------------|---------------|
| "name (firm or individual)" | client_name | Company name or person name |
| "firm or individual" | client_name | (alternative pattern) |
| "contact" | billing_contact | Jeffrey Mori |
| "client code" | client_code | Client reference code |
| "billing address line 1" | billing_address_line_1 | Arthur Mori & Associates, Inc |
| "address line 1" | billing_address_line_1 | (alternative pattern) |
| "billing address line 2" | billing_address_line_2 | 1314 South King Street, Suite 955 |
| "address line 2" | billing_address_line_2 | (alternative pattern) |
| "zip" | billing_zip | 96819 |
| "fax" | fax | Fax number |
| "email" | billing_contact_email | ama@aymori.com |

### Pattern Ordering

**Important**: Patterns are ordered from most specific to least specific because the matching uses `if needle in lower`. This ensures:

- "secondary contact email" matches before "contact"
- "billing contact" matches before "contact"
- "billing address line 1" matches before "address line 1"

## Expected Auto-Mapped Fields

After this update, the Auto-Mapped Fields section should now show:

### Top Section (Mode 1)
- Project Number → 24-107
- Project Name → Medical Laboratory
- City → Kailua
- State → HI
- Originator → Jake Pfitsch
- Date Entered → 2024-06-19
- Office → Office

### Client Information Section (Mode 2)
- Client Information - Name (Firm or Individual) → (value if present)
- Client Information - Contact → Jeffrey Mori
- Client Information - Client Code → (value if present)
- Client Information - Purchase Order Number → (value if present)
- Client Information - Billing Address Line 1 → Arthur Mori & Associates, Inc
- Client Information - Billing Address Line 2 → 1314 South King Street, Suite 955
- Client Information - City → Honolulu
- Client Information - State → HI
- Client Information - Zip → 96819
- Client Information - Phone → 808.429.5231
- Client Information - Fax → (value if present)
- Client Information - Email → ama@aymori.com

### Project Manager Section (Mode 3)
- Project Manager → Jake Pfitsch
- Project Start Date → 2024-06-18
- Fee (Contract Amount) → 8800
- Type of Contract → Lump Sum
- Expenses → Included
- Retainer Received → Yes

## How to Test

1. **Re-scan a PIF file** or navigate to an existing scan result
2. The Auto-Mapped Fields section should now show **many more fields**
3. All Client Information sub-fields should appear with "Client Information -" prefix
4. Field count should increase from 14 to approximately 20-25 fields

## What Changed in the Code

**File**: `consultingmanager/billing/utils/pif_parser.py` (lines 255-273)

Added 11 new patterns specifically for Client Information fields:
- "name (firm or individual)"
- "firm or individual"
- "contact"
- "client code"
- "billing address line 1"
- "address line 1"
- "billing address line 2"
- "address line 2"
- "zip"
- "fax"
- "email"

Reordered patterns to ensure more specific patterns match before general ones.

## Notes

- Empty fields will show as "-" in the display but will still appear in Auto-Mapped Fields
- The mode-aware extraction (from previous enhancement) ensures values are read from the correct columns
- Section concatenation applies to all Client Information fields automatically

