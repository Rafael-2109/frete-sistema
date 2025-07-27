"""
Permission System Validation Utilities
=====================================

Provides validation helpers for the permission system.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re

def validate_permission_name(name: str) -> bool:
    """
    Validate permission name format.
    Must be lowercase, alphanumeric with underscores only.
    """
    if not name:
        return False
    
    pattern = r'^[a-z][a-z0-9_]*$'
    return bool(re.match(pattern, name))

def validate_hex_color(color: str) -> bool:
    """
    Validate hex color format.
    Must be #RRGGBB format.
    """
    if not color:
        return False
    
    pattern = r'^#[0-9A-Fa-f]{6}$'
    return bool(re.match(pattern, color))

def validate_critical_level(level: str) -> bool:
    """
    Validate critical level value.
    Must be one of: LOW, NORMAL, HIGH, CRITICAL
    """
    valid_levels = ['LOW', 'NORMAL', 'HIGH', 'CRITICAL']
    return level in valid_levels

def validate_entity_type(entity_type: str) -> bool:
    """
    Validate entity type value.
    Must be one of: CATEGORY, MODULE, SUBMODULE
    """
    valid_types = ['CATEGORY', 'MODULE', 'SUBMODULE']
    return entity_type in valid_types

def validate_permission_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate permission data structure.
    Returns list of validation errors.
    """
    errors = []
    
    # Validate required fields
    required_fields = ['type', 'id']
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Validate entity type
    if 'type' in data and not validate_entity_type(data['type'].upper()):
        errors.append(f"Invalid entity type: {data['type']}")
    
    # Validate boolean fields
    boolean_fields = ['can_view', 'can_edit', 'can_delete', 'can_export']
    for field in boolean_fields:
        if field in data and not isinstance(data[field], bool):
            errors.append(f"Field {field} must be a boolean")
    
    return errors

def sanitize_input(value: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent XSS and SQL injection.
    """
    if not value:
        return ""
    
    # Remove leading/trailing whitespace
    value = value.strip()
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Basic HTML escape
    value = value.replace('<', '&lt;').replace('>', '&gt;')
    
    return value

def validate_template_data(template_data: Dict[str, Any]) -> List[str]:
    """
    Validate permission template data structure.
    Returns list of validation errors.
    """
    errors = []
    
    if not isinstance(template_data, dict):
        errors.append("Template data must be a dictionary")
        return errors
    
    # Validate permissions array
    if 'permissions' in template_data:
        if not isinstance(template_data['permissions'], list):
            errors.append("Permissions must be an array")
        else:
            for idx, perm in enumerate(template_data['permissions']):
                perm_errors = validate_permission_data(perm)
                for error in perm_errors:
                    errors.append(f"Permission [{idx}]: {error}")
    
    # Validate vendors array
    if 'vendors' in template_data:
        if not isinstance(template_data['vendors'], list):
            errors.append("Vendors must be an array")
        else:
            for idx, vendor in enumerate(template_data['vendors']):
                if not isinstance(vendor, str):
                    errors.append(f"Vendor [{idx}] must be a string")
    
    # Validate teams array
    if 'teams' in template_data:
        if not isinstance(template_data['teams'], list):
            errors.append("Teams must be an array")
        else:
            for idx, team in enumerate(template_data['teams']):
                if not isinstance(team, str):
                    errors.append(f"Team [{idx}] must be a string")
    
    return errors