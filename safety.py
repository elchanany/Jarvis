"""
Jarvis Safety System - Confirmation for critical actions
"""

# Actions that require user confirmation
CRITICAL_ACTIONS = [
    "delete",
    "remove",
    "erase",
    "format",
    "shutdown",
    "restart",
    "uninstall",
    "move",  # Moving files can be dangerous
    "rename",
]

# Current pending confirmation
pending_confirmation = None

def is_critical_action(action_description: str) -> bool:
    """Check if an action requires confirmation."""
    action_lower = action_description.lower()
    return any(critical in action_lower for critical in CRITICAL_ACTIONS)

def request_confirmation(action: str, details: str = "") -> str:
    """Request user confirmation for a critical action."""
    global pending_confirmation
    
    pending_confirmation = {
        "action": action,
        "details": details,
    }
    
    return f"⚠️ אלחנן, אתה בטוח שאתה רוצה {action}? אמור 'כן' לאישור או 'לא' לביטול."

def check_confirmation(user_response: str) -> tuple:
    """
    Check user's confirmation response.
    Returns: (confirmed: bool, action_details: dict or None)
    """
    global pending_confirmation
    
    if pending_confirmation is None:
        return False, None
    
    response_lower = user_response.lower().strip()
    
    confirmed = response_lower in ["yes", "כן", "כ", "y", "ok", "אוקי", "בטח", "sure"]
    cancelled = response_lower in ["no", "לא", "ל", "n", "cancel", "ביטול", "עזוב"]
    
    if confirmed:
        action = pending_confirmation
        pending_confirmation = None
        return True, action
    elif cancelled:
        pending_confirmation = None
        return False, None
    else:
        # Unclear response
        return False, None

def has_pending_confirmation() -> bool:
    """Check if there's a pending confirmation."""
    return pending_confirmation is not None

def cancel_confirmation():
    """Cancel any pending confirmation."""
    global pending_confirmation
    pending_confirmation = None

def get_pending_action() -> dict:
    """Get the pending action details."""
    return pending_confirmation
