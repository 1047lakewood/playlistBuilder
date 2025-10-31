import json
import os
from datetime import datetime
import logging
import threading

class ConfigManager:
    """Manages loading, saving, and accessing configuration from JSON with dual-station support."""

    def __init__(self, config_file='config.json', backup_prefix='config_backup_'):
        self.config_file = config_file
        self.backup_prefix = backup_prefix
        self.config = self.load_config()

        # Thread safety lock
        self._lock = threading.RLock()

        # Station IDs
        self.STATION_1047 = 'station_1047'
        self.STATION_887 = 'station_887'
        self.STATIONS = [self.STATION_1047, self.STATION_887]

    def load_config(self):
        """Loads the JSON configuration or returns a default structure if file doesn't exist."""
        # Try new config.json first
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logging.info(f"Configuration loaded from {self.config_file}.")
                return config
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON from {self.config_file}: {e}")
                return self._default_config()
        
        # Try legacy messages.json for backward compatibility
        legacy_file = 'messages.json'
        if os.path.exists(legacy_file):
            try:
                logging.info(f"Migrating from legacy {legacy_file} to {self.config_file}")
                with open(legacy_file, 'r', encoding='utf-8') as f:
                    legacy_config = json.load(f)
                # Migrate to new format
                migrated_config = self._migrate_legacy_config(legacy_config)
                # Save as new config
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(migrated_config, f, indent=4)
                logging.info(f"Migration complete. Configuration saved to {self.config_file}.")
                return migrated_config
            except Exception as e:
                logging.error(f"Error migrating from {legacy_file}: {e}")
                return self._default_config()
        
        logging.warning(f"Config file {self.config_file} not found. Using default configuration.")
        return self._default_config()

    def _migrate_legacy_config(self, legacy_config):
        """Migrate old single-station config to new dual-station format."""
        return {
            "stations": {
                "station_1047": {
                    "name": "104.7 FM",
                    "Messages": legacy_config.get('Messages', []),
                    "Ads": legacy_config.get('Ads', []),
                    "settings": legacy_config.get('settings', {})
                },
                "station_887": {
                    "name": "88.7 FM",
                    "Messages": [],
                    "Ads": [],
                    "settings": {
                        "rds": {
                            "ip": "192.168.1.100",
                            "port": 10002,
                            "now_playing_xml": r"G:\To_RDS\nowplaying_887.xml",
                            "default_message": "88.7 FM"
                        },
                        "intro_loader": {
                            "now_playing_xml": r"G:\To_RDS\nowplaying_887.xml",
                            "mp3_directory": r"G:\Shiurim\introsCleanedUp",
                            "missing_artists_log": r"missing_artists_887.log",
                            "schedule_url": "http://192.168.1.100:9000/?pass=password&action=schedule&type=run&id=INTRO"
                        },
                        "ad_inserter": {
                            "insertion_url": "http://192.168.1.100:8000/insert",
                            "instant_url": "http://192.168.1.100:8000/play",
                            "output_mp3": r"G:\Ads\adRoll_887.mp3"
                        }
                    }
                }
            },
            "shared": {
                "Whitelist": legacy_config.get('Whitelist', []),
                "Blacklist": legacy_config.get('Blacklist', []),
                "playlist_presets": legacy_config.get('playlist_presets', {}),
                "debug": {
                    "enable_debug_logs": False
                }
            }
        }

    def _default_config(self):
        """Returns the default configuration structure."""
        return {
            "stations": {
                "station_1047": {
                    "name": "104.7 FM",
                    "Messages": [],
                    "Ads": [],
                    "settings": {
                        "rds": {
                            "ip": "50.208.125.83",
                            "port": 10001,
                            "now_playing_xml": r"G:\To_RDS\nowplaying.xml",
                            "default_message": "732.901.7777 to SUPPORT and hear this program!"
                        },
                        "intro_loader": {
                            "now_playing_xml": r"G:\To_RDS\nowplaying.xml",
                            "mp3_directory": r"G:\Shiurim\introsCleanedUp",
                            "missing_artists_log": r"missing_artists_1047.log",
                            "schedule_url": "http://192.168.3.11:9000/?pass=bmas220&action=schedule&type=run&id=TBACFNBGJKOMETDYSQYR",
                            "current_artist_filename": "currentArtist_1047.mp3",
                            "actual_current_artist_filename": "actualCurrentArtist_1047.mp3",
                            "blank_mp3_filename": "blank_1047.mp3",
                            "silent_mp3_filename": "near_silent_1047.mp3"
                        },
                        "ad_inserter": {
                            "insertion_url": "http://localhost:8000/insert",
                            "instant_url": "http://localhost:8000/play",
                            "output_mp3": r"G:\Ads\adRoll_1047.mp3"
                        }
                    }
                },
                "station_887": {
                    "name": "88.7 FM",
                    "Messages": [],
                    "Ads": [],
                    "settings": {
                        "rds": {
                            "ip": "192.168.1.100",
                            "port": 10002,
                            "now_playing_xml": r"G:\To_RDS\nowplaying_887.xml",
                            "default_message": "88.7 FM"
                        },
                        "intro_loader": {
                            "now_playing_xml": r"G:\To_RDS\nowplaying_887.xml",
                            "mp3_directory": r"G:\Shiurim\introsCleanedUp",
                            "missing_artists_log": r"missing_artists_887.log",
                            "schedule_url": "http://192.168.1.100:9000/?pass=password&action=schedule&type=run&id=INTRO",
                            "current_artist_filename": "currentArtist_887.mp3",
                            "actual_current_artist_filename": "actualCurrentArtist_887.mp3",
                            "blank_mp3_filename": "blank_887.mp3",
                            "silent_mp3_filename": "near_silent_887.mp3"
                        },
                        "ad_inserter": {
                            "insertion_url": "http://192.168.1.100:8000/insert",
                            "instant_url": "http://192.168.1.100:8000/play",
                            "output_mp3": r"G:\Ads\adRoll_887.mp3"
                        }
                    }
                }
            },
            "shared": {
                "Whitelist": [],
                "Blacklist": [],
                "playlist_presets": {},
                "debug": {
                    "enable_debug_logs": False
                }
            }
        }

    def save_config(self, make_backup=False):
        """Saves the current configuration to JSON, optionally creating a backup."""
        with self._lock:
            if make_backup:
                self._backup_config()

            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4)
                logging.info(f"Configuration saved to {self.config_file}.")
            except Exception as e:
                logging.error(f"Error saving configuration to {self.config_file}: {e}")

    def _backup_config(self):
        """Creates a timestamped backup of the current config file."""
        if os.path.exists(self.config_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{self.backup_prefix}{timestamp}.json"
            try:
                os.rename(self.config_file, backup_file)
                logging.info(f"Backup created: {backup_file}")
            except OSError as e:
                logging.error(f"Error creating backup {backup_file}: {e}")

    # ==================== STATION-SPECIFIC METHODS ====================
    
    def get_station_messages(self, station_id):
        """Returns the list of messages for a specific station."""
        return self.config.get('stations', {}).get(station_id, {}).get('Messages', [])

    def set_station_messages(self, station_id, messages):
        """Sets the list of messages for a specific station."""
        if 'stations' not in self.config:
            self.config['stations'] = {}
        if station_id not in self.config['stations']:
            self.config['stations'][station_id] = {}
        self.config['stations'][station_id]['Messages'] = messages

    def get_station_ads(self, station_id):
        """Returns the list of ads for a specific station."""
        return self.config.get('stations', {}).get(station_id, {}).get('Ads', [])

    def set_station_ads(self, station_id, ads):
        """Sets the list of ads for a specific station."""
        with self._lock:
            if 'stations' not in self.config:
                self.config['stations'] = {}
            if station_id not in self.config['stations']:
                self.config['stations'][station_id] = {}
            self.config['stations'][station_id]['Ads'] = ads

    def get_station_name(self, station_id):
        """Returns the display name for a station."""
        return self.config.get('stations', {}).get(station_id, {}).get('name', station_id)

    def get_station_setting(self, station_id, key, default=None):
        """Get a setting for a specific station using dot notation."""
        try:
            keys = key.split('.')
            # Always look under the settings key, but handle 'settings.' prefix for backward compatibility
            value = self.config.get('stations', {}).get(station_id, {}).get('settings', {})
            if keys[0] == 'settings':
                keys = keys[1:]  # Remove 'settings' from the path

            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            logging.warning(f"Setting '{key}' not found for station '{station_id}'. Returning default: {default}")
            return default

    def update_station_setting(self, station_id, key, value):
        """Update a setting for a specific station using dot notation."""
        try:
            if 'stations' not in self.config:
                self.config['stations'] = {}
            if station_id not in self.config['stations']:
                self.config['stations'][station_id] = {}
            if 'settings' not in self.config['stations'][station_id]:
                self.config['stations'][station_id]['settings'] = {}
            
            keys = key.split('.')
            d = self.config['stations'][station_id]['settings']
            for k in keys[:-1]:
                if k not in d:
                    d[k] = {}
                d = d[k]
            d[keys[-1]] = value
            logging.info(f"Updated station '{station_id}' setting '{key}' to {value}")
        except Exception as e:
            logging.error(f"Error updating station '{station_id}' setting '{key}': {e}")

    # ==================== SHARED METHODS ====================
    
    def get_whitelist(self):
        """Returns the shared whitelist."""
        return self.config.get('shared', {}).get('Whitelist', [])
    
    def get_shared_whitelist(self):
        """Returns the shared whitelist (alias for get_whitelist)."""
        return self.get_whitelist()

    def set_whitelist(self, whitelist):
        """Sets the shared whitelist."""
        if 'shared' not in self.config:
            self.config['shared'] = {}
        self.config['shared']['Whitelist'] = whitelist
    
    def set_shared_whitelist(self, whitelist):
        """Sets the shared whitelist (alias for set_whitelist)."""
        self.set_whitelist(whitelist)

    def get_blacklist(self):
        """Returns the shared blacklist."""
        return self.config.get('shared', {}).get('Blacklist', [])
    
    def get_shared_blacklist(self):
        """Returns the shared blacklist (alias for get_blacklist)."""
        return self.get_blacklist()

    def set_blacklist(self, blacklist):
        """Sets the shared blacklist."""
        if 'shared' not in self.config:
            self.config['shared'] = {}
        self.config['shared']['Blacklist'] = blacklist
    
    def set_shared_blacklist(self, blacklist):
        """Sets the shared blacklist (alias for set_blacklist)."""
        self.set_blacklist(blacklist)

    def get_playlist_presets(self):
        """Returns the shared playlist presets dictionary."""
        return self.config.get('shared', {}).get('playlist_presets', {})

    def set_playlist_presets(self, presets):
        """Sets the shared playlist presets dictionary."""
        if 'shared' not in self.config:
            self.config['shared'] = {}
        self.config['shared']['playlist_presets'] = presets

    def get_shared_setting(self, key, default=None):
        """Get a shared setting using dot notation."""
        try:
            keys = key.split('.')
            value = self.config.get('shared', {})
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            logging.warning(f"Shared setting '{key}' not found. Returning default: {default}")
            return default

    def update_shared_setting(self, key, value):
        """Update a shared setting using dot notation."""
        try:
            if 'shared' not in self.config:
                self.config['shared'] = {}
            
            keys = key.split('.')
            d = self.config['shared']
            for k in keys[:-1]:
                if k not in d:
                    d[k] = {}
                d = d[k]
            d[keys[-1]] = value
            logging.info(f"Updated shared setting '{key}' to {value}")
        except Exception as e:
            logging.error(f"Error updating shared setting '{key}': {e}")

    # ==================== BACKWARD COMPATIBILITY METHODS ====================
    # These maintain compatibility with existing code that doesn't specify station
    
    def get_messages(self):
        """Returns messages for station 1047 (backward compatibility)."""
        return self.get_station_messages(self.STATION_1047)

    def set_messages(self, messages):
        """Sets messages for station 1047 (backward compatibility)."""
        self.set_station_messages(self.STATION_1047, messages)

    def get_ads(self):
        """Returns ads for station 1047 (backward compatibility)."""
        return self.get_station_ads(self.STATION_1047)

    def set_ads(self, ads):
        """Sets ads for station 1047 (backward compatibility)."""
        self.set_station_ads(self.STATION_1047, ads)

    def get_setting(self, key, default=None):
        """Get a setting (tries shared first, then station 1047 for backward compatibility)."""
        # Try shared settings first
        try:
            if key.startswith('settings.'):
                # Station-specific setting, use station 1047
                station_key = key.replace('settings.', '')
                return self.get_station_setting(self.STATION_1047, station_key, default)
            else:
                # Try shared settings
                return self.get_shared_setting(key, default)
        except:
            return default

    def update_setting(self, key, value):
        """Update a setting (uses station 1047 for backward compatibility)."""
        if key.startswith('settings.'):
            # Station-specific setting
            station_key = key.replace('settings.', '')
            self.update_station_setting(self.STATION_1047, station_key, value)
        else:
            # Shared setting
            self.update_shared_setting(key, value)

if __name__ == "__main__":
    print("This script defines the ConfigManager class.")
