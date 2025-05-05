from django import template
import json
from itertools import groupby
from typing import Any, Dict, List, Optional, Tuple

register = template.Library()

@register.filter
def from_json(value: Any) -> Optional[Any]:
    """Convert a JSON string to a Python object."""
    if not value:
        return None
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value
    except (ValueError, TypeError):
        return None

@register.filter
def groupby_filter(items: List[Dict], key: str) -> List[Tuple[str, List[Dict]]]:
    """
    Group a list of dictionaries by a key.
    Usage: {% for group, items in list|groupby_filter:"key" %}
    """
    if not items or not isinstance(items, list):
        return []
    
    try:
        # Convert items to list if it's a QuerySet
        items_list = list(items)
        # Filter out any non-dict items and ensure key exists
        valid_items = [item for item in items_list if isinstance(item, dict) and key in item]
        # Sort and group
        sorted_items = sorted(valid_items, key=lambda x: str(x.get(key, '')))
        return [(k, list(g)) for k, g in groupby(sorted_items, key=lambda x: str(x.get(key, '')))]
    except (AttributeError, TypeError):
        return [] 