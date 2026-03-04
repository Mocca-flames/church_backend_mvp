"""
Application configuration settings.
These can be controlled via environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Signup settings
# Set ALLOW_SIGNUPS=false in .env to disable new user registrations
ALLOW_SIGNUPS = os.getenv("ALLOW_SIGNUPS", "true").lower() in ("true", "1", "yes", "on")

# In-memory override for runtime toggling (useful for admin endpoints)
_signups_enabled = None

def are_signups_allowed() -> bool:
    """
    Check if new user signups are currently allowed.
    Returns True if signups are enabled, False otherwise.
    Priority: runtime override > environment variable > default (True)
    """
    global _signups_enabled
    if _signups_enabled is not None:
        return _signups_enabled
    return ALLOW_SIGNUPS

def set_signups_allowed(enabled: bool) -> None:
    """
    Enable or disable new user signups at runtime.
    This is a temporary in-memory setting that doesn't persist across restarts.
    To make it permanent, update the ALLOW_SIGNUPS environment variable.
    
    Args:
        enabled: True to allow signups, False to disable
    """
    global _signups_enabled
    _signups_enabled = enabled

def get_signup_status() -> dict:
    """
    Get the current signup configuration status.
    
    Returns:
        dict with 'allowed' (bool), 'env_default' (bool), and 'runtime_override' (bool or None)
    """
    global _signups_enabled
    return {
        "allowed": are_signups_allowed(),
        "env_default": ALLOW_SIGNUPS,
        "runtime_override": _signups_enabled
    }
