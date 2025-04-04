import json
import os
import logging
from datetime import datetime

CONFIG_FILE_NAME = "messages.json"
CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Get the parent dir (CombinedRDSApp)
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

DEFAULT_CONFIG = {
    "Messages": [],
    "Whitelist": [],
    "Blacklist": []
}

class ConfigManager:
    def __init__(self, config_path=CONFIG_FILE_PATH):
        self.config_path = config_path
        self.config = self.load_config()
        self._ensure_keys_exist() # Ensure default keys are present

    def _ensure_keys_exist(self):
        """Ensures the default top-level keys exist in the loaded config."""
        changed = False
        for key, default_value in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = default_value
                changed = True
        if changed:
            logging.warning("Config file was missing default keys. Added them.")
            self.save_config() # Save immediately if keys were added

    def load_config(self):
        """Loads configuration from the JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding='utf-8') as file:
                    loaded_config = json.load(file)
                    # Basic validation: check if it's a dictionary
                    if not isinstance(loaded_config, dict):
                        logging.error(f"Config file {self.config_path} is not a valid JSON object. Creating backup and using default.")
                        self._backup_corrupted_config()
                        return DEFAULT_CONFIG.copy()
                    return loaded_config
            else:
                logging.info(f"Config file not found at {self.config_path}. Creating with default values.")
                # Create the directory if it doesn't exist
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                # Save default config to create the file
                default_copy = DEFAULT_CONFIG.copy()
                self._save_to_file(default_copy)
                return default_copy
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {self.config_path}. Creating backup and using default.")
            self._backup_corrupted_config()
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            logging.exception(f"Unexpected error loading config: {e}. Using default.")
            self._backup_corrupted_config() # Attempt backup on any load error
            return DEFAULT_CONFIG.copy()

    def _backup_corrupted_config(self):
        """Creates a timestamped backup of a potentially corrupted config file."""
        if not os.path.exists(self.config_path):
            return # No file to back up

        backup_name = f"{os.path.splitext(CONFIG_FILE_NAME)[0]}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(os.path.dirname(self.config_path), backup_name)
        try:
            os.rename(self.config_path, backup_path)
            logging.info(f"Backed up corrupted config to {backup_path}")
        except Exception as backup_e:
            logging.error(f"Failed to create backup of corrupted config: {backup_e}")

    def _save_to_file(self, data):
        """Internal function to write data to the config file."""
        try:
            # Create the directory if it doesn't exist (safety check)
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding='utf-8') as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            logging.exception(f"Failed to save configuration to {self.config_path}: {e}")
            raise # Re-raise the exception so the caller knows saving failed

    def save_config(self):
        """Saves the current configuration state to the JSON file."""
        logging.debug(f"Attempting to save config to {self.config_path}")
        try:
            self._save_to_file(self.config)
            logging.info(f"Configuration saved successfully to {self.config_path}")
        except Exception:
             # Error already logged in _save_to_file
             pass

    def get_messages(self):
        """Returns the list of messages."""
        return self.config.get("Messages", [])

    def set_messages(self, messages_list):
        """Sets the list of messages."""
        if isinstance(messages_list, list):
            self.config["Messages"] = messages_list
        else:
            logging.error("Attempted to set messages with non-list data.")

    def get_whitelist(self):
        """Returns the artist whitelist."""
        # Ensure it returns a list even if the key is missing or invalid
        whitelist = self.config.get("Whitelist", [])
        return whitelist if isinstance(whitelist, list) else []

    def set_whitelist(self, whitelist):
        """Sets the artist whitelist."""
        if isinstance(whitelist, list):
            self.config["Whitelist"] = whitelist
        else:
            logging.error("Attempted to set whitelist with non-list data.")

    def get_blacklist(self):
        """Returns the artist blacklist."""
        # Ensure it returns a list even if the key is missing or invalid
        blacklist = self.config.get("Blacklist", [])
        return blacklist if isinstance(blacklist, list) else []

    def set_blacklist(self, blacklist):
        """Sets the artist blacklist."""
        if isinstance(blacklist, list):
            self.config["Blacklist"] = blacklist
        else:
            logging.error("Attempted to set blacklist with non-list data.")

    # --- Generic Settings Methods ---
    def get_setting(self, key, default=None):
        """
        Retrieves a setting value for the given key.

        Args:
            key (str): The key of the setting to retrieve.
            default: The value to return if the key is not found. Defaults to None.

        Returns:
            The value of the setting, or the default value if not found.
        """
        return self.config.get(key, default)

    def update_setting(self, key, value):
        """
        Updates or adds a setting with the given key and value, then saves the config.

        Args:
            key (str): The key of the setting to update or add.
            value: The value to set for the key.
        """
        self.config[key] = value
        logging.debug(f"Updated setting '{key}' to '{value}'. Saving config.")
        self.save_config() # Save after updating a setting


# Example usage (for testing)
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Assume CombinedRDSApp/src structure for testing
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    test_config_path = os.path.join(project_root, "test_messages.json")

    print(f"Using test config path: {test_config_path}")

    # Clean up previous test file if exists
    if os.path.exists(test_config_path):
        os.remove(test_config_path)

    # Test loading non-existent file
    print("\n--- Testing Load (Non-existent) ---")
    manager = ConfigManager(config_path=test_config_path)
    print(f"Initial config: {manager.config}")
    assert manager.get_messages() == []
    assert manager.get_whitelist() == []
    assert manager.get_blacklist() == []
    assert os.path.exists(test_config_path) # File should be created

    # Test modifying and saving
    print("\n--- Testing Modify and Save ---")
    manager.set_messages([{"Text": "Test Message", "Enabled": True}])
    manager.set_whitelist(["Artist A"])
    manager.set_blacklist(["Artist B"])
    manager.save_config()

    # Test reloading
    print("\n--- Testing Reload ---")
    manager2 = ConfigManager(config_path=test_config_path)
    print(f"Reloaded config: {manager2.config}")
    assert len(manager2.get_messages()) == 1
    assert manager2.get_messages()[0]["Text"] == "Test Message"
    assert manager2.get_whitelist() == ["Artist A"]
    assert manager2.get_blacklist() == ["Artist B"]

    # Test generic settings
    print("\n--- Testing Generic Settings ---")
    assert manager2.get_setting("non_existent_key") is None
    assert manager2.get_setting("non_existent_key", default="default_val") == "default_val"
    manager2.update_setting("new_setting", {"a": 1, "b": 2})
    assert manager2.get_setting("new_setting") == {"a": 1, "b": 2}

    # Test reloading generic settings
    print("\n--- Testing Reload Generic Settings ---")
    manager_reloaded_generic = ConfigManager(config_path=test_config_path)
    assert manager_reloaded_generic.get_setting("new_setting") == {"a": 1, "b": 2}
    assert manager_reloaded_generic.get_messages()[0]["Text"] == "Test Message" # Ensure old settings still exist


    # Test loading corrupted file
    print("\n--- Testing Load (Corrupted) ---")
    with open(test_config_path, "w") as f:
        f.write("this is not json")
    manager3 = ConfigManager(config_path=test_config_path)
    print(f"Config after loading corrupted: {manager3.config}")
    assert manager3.get_messages() == [] # Should reset to default
    assert manager3.get_whitelist() == []
    assert manager3.get_blacklist() == []
    # Check if backup was created
    backup_found = any(f.startswith("test_messages_backup_") for f in os.listdir(project_root))
    assert backup_found
    print("Corrupted file test passed, backup created.")

    # Clean up test files
    if os.path.exists(test_config_path):
        os.remove(test_config_path)
    for f in os.listdir(project_root):
        if f.startswith("test_messages_backup_"):
            os.remove(os.path.join(project_root, f))

    print("\nConfigManager tests completed.")
