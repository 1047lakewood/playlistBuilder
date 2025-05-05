import os
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def load_settings(settings_path: str, default_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Loads settings from the specified file. If the file does not exist or an error occurs,
    returns a copy of default_settings.
    """
    if not os.path.exists(settings_path):
        logger.info(f"Settings file '{settings_path}' does not exist. Using default settings.")
        return default_settings.copy()
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading settings from '{settings_path}': {e}")
        return default_settings.copy()

def save_settings(settings_path: str, settings: Dict[str, Any]) -> bool:
    """
    Saves the settings dictionary to the specified file in JSON format.
    Returns True if successful, False otherwise.
    """
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        logger.info(f"Settings saved to '{settings_path}'.")
        return True
    except Exception as e:
        logger.error(f"Error saving settings to '{settings_path}': {e}")
        return False

def save_profile(current_settings: Dict[str, Any], profile_name: str, profile_data: Dict[str, Any]) -> None:
    """
    Saves the given profile_data under profile_name in the current_settings dict.
    Updates last_profile and persists settings file.
    """
    if "profiles" not in current_settings:
        current_settings["profiles"] = {}
    current_settings["profiles"][profile_name] = profile_data
    current_settings["last_profile"] = profile_name
    logger.info(f"Profile '{profile_name}' saved in settings.")

def delete_profile(current_settings: Dict[str, Any], profile_name: str) -> bool:
    """
    Deletes the profile with the given name from current_settings.
    Returns True if deleted, False if not found.
    """
    profiles = current_settings.get("profiles", {})
    if profile_name in profiles:
        del profiles[profile_name]
        if current_settings.get("last_profile") == profile_name:
            current_settings["last_profile"] = None
        logger.info(f"Profile '{profile_name}' deleted.")
        return True
    return False

def load_profile(current_settings: Dict[str, Any], profile_name: str) -> Dict[str, Any]:
    """
    Loads the profile data for the given profile_name from current_settings.
    Returns the profile data dict, or an empty dict if not found.
    """
    return current_settings.get("profiles", {}).get(profile_name, {})
