
import persistence
import logging
from utils import DEFAULT_COLUMNS
logger = logging.getLogger(__name__)

# --- Model ---
class PlaylistManagerModel:
    def __init__(self):
        self._settings_file_path = "playlist_editor_settings.json" # Default, can be overridden by loaded settings
        self.current_settings = {
            "columns": list(DEFAULT_COLUMNS), # Ensure it's a mutable list copy
            "profiles": {},
            "last_profile": None,
            "audio_device": None,
            "open_tabs": [],
            "column_widths": {},
            "volume": 0.8, # Default volume
            "settings_file_path": self._settings_file_path # Store the path within settings too
        }
        self.clipboard = []
        self.pygame_initialized = False
        
        # Playback state
        self.currently_playing_path = None
        self.is_paused = False
        self.playback_start_time = 0
        self.paused_position = 0
        self.current_track_duration = 0
        
        # Column widths are also stored in current_settings, _column_widths is for quick access
        self._column_widths = {} 

        self.load_initial_settings() # Load settings, which might update _settings_file_path

    def get_actual_settings_file_path(self):
        # This ensures we use the path defined *inside* the settings if it exists,
        # otherwise the default path.
        return self.current_settings.get("settings_file_path", self._settings_file_path)

    def load_initial_settings(self):
        # First, try to load from the default path to see if a custom path is specified inside
        temp_settings = persistence.load_settings(self._settings_file_path, self.current_settings.copy())
        
        # If temp_settings (from default path) has a custom path, update _settings_file_path
        if temp_settings and temp_settings.get("settings_file_path"):
            self._settings_file_path = temp_settings["settings_file_path"]
            # Now, load settings from the (potentially new) _settings_file_path
            self.current_settings = persistence.load_settings(self._settings_file_path, self.current_settings.copy())
        else:
            # If no custom path in default settings, then temp_settings are the ones to use
            self.current_settings = temp_settings

        # Ensure 'columns' is a list and not a tuple from JSON
        if isinstance(self.current_settings.get('columns'), tuple):
            self.current_settings['columns'] = list(self.current_settings['columns'])
        elif not isinstance(self.current_settings.get('columns'), list):
             self.current_settings['columns'] = list(DEFAULT_COLUMNS)


        # Defensive checks for critical settings
        if not isinstance(self.current_settings.get('open_tabs'), list):
            self.current_settings['open_tabs'] = []
        self.current_settings['open_tabs'] = [
            fp if isinstance(fp, (str, type(None))) else None 
            for fp in self.current_settings['open_tabs']
        ]
        if 'column_widths' not in self.current_settings or not isinstance(self.current_settings['column_widths'], dict):
            self.current_settings['column_widths'] = {}
        self._column_widths = self.current_settings['column_widths']

        if 'volume' not in self.current_settings or not isinstance(self.current_settings['volume'], (float, int)):
            self.current_settings['volume'] = 0.8
        
        # Ensure the settings_file_path itself is correctly stored
        self.current_settings["settings_file_path"] = self._settings_file_path


    def save_all_settings(self):
        # Ensure the path we save to is the one we intend (could be custom)
        target_path = self.get_actual_settings_file_path()
        self.current_settings["settings_file_path"] = target_path # Ensure it's saved for next load
        persistence.save_settings(target_path, self.current_settings)
        logger.info(f"Settings saved to {target_path}")

    def get_column_widths(self):
        return self._column_widths.copy()

    def set_column_widths(self, new_widths):
        self._column_widths = new_widths.copy()
        self.current_settings['column_widths'] = new_widths.copy()

    def save_profile_data(self, profile_name, profile_data):
        persistence.save_profile(self.current_settings, profile_name, profile_data)
        self.current_settings["last_profile"] = profile_name
        self.save_all_settings() # Persist the new profile list and last_profile

    def delete_profile_data(self, profile_name):
        persistence.delete_profile(self.current_settings, profile_name)
        self.save_all_settings() # Persist the change

    def update_volume_setting(self, volume):
        self.current_settings['volume'] = volume
        # No need to call save_all_settings here, usually done on quit or explicit save.
        # However, if you want volume to persist immediately: self.save_all_settings()

