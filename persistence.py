import json
import os
from models.playlist import Playlist
from version import VERSION, APP_NAME

class Persistence:
    
    def __init__(self, controller):
        self.controller = controller
        self.profile_path = "settings.json"
        self.profile = None
        self.load_settings()
        

        
        # Convert profiles list to dictionary if needed
        if "profiles" in self.profile and isinstance(self.profile["profiles"], list):
            profile_list = self.profile["profiles"]
            self.profile["profiles"] = {}
            for profile_name in profile_list:
                self.profile["profiles"][profile_name] = []
        
        # Ensure profiles dictionary exists
        if "profiles" not in self.profile:
            self.profile["profiles"] = {}
        
        # Set current profile name from settings
        # write this shorter 
        self.current_profile_name = self.profile["current_profile"] 

        

        # Save any changes made during initialization
        self.save_settings(self.profile)
    
    def load_settings(self):
        if not os.path.exists(self.profile_path):
            self.profile = {"current_profile": "default", "profiles": {"default": []}}
            self.save_settings(self.profile)
        else:
            with open(self.profile_path, "r") as f:
                self.profile = json.load(f)
        return self.profile

    def save_settings(self, settings):
        self.profile = settings
        with open(self.profile_path, "w") as f:
            json.dump(self.profile, f)
        return self.profile

    def get_profile_names(self):
        """Get a list of all profile names"""
        return list(self.profile["profiles"].keys())

    def get_current_profile_name(self):
        """Get the name of the currently active profile"""
        return self.current_profile_name

    def set_current_profile(self, profile_name):
        """Set the current profile"""
        if profile_name in self.profile["profiles"]:
            self.current_profile_name = profile_name
            self.profile["current_profile"] = profile_name
            self.save_settings(self.profile)
            self.controller.root.title(f"{APP_NAME}    v{VERSION} - {profile_name}")
            return True
        return False

    def create_profile(self, profile_name):
        """Create a new profile"""
        if profile_name not in self.profile["profiles"]:
            self.profile["profiles"][profile_name] = []
            self.save_settings(self.profile)
            return True
        return False

    def delete_profile(self, profile_name):
        """Delete a profile"""
        if profile_name in self.profile["profiles"]:
            del self.profile["profiles"][profile_name]
            self.save_settings(self.profile)
            return True
        return False

    def load_profile_settings(self, profile_name=None):
        """Load playlists from the specified profile or current profile"""
        settings = self.load_settings()
        profile_to_load = profile_name if profile_name else self.current_profile_name
        
        if profile_to_load in settings["profiles"]:
            return settings["profiles"][profile_to_load]
        return []

    def save_profile_settings(self, playlists, profile_name=None):
        """Save playlists to the specified profile or current profile"""
        settings = self.load_settings()
        profile_to_save = profile_name if profile_name else self.current_profile_name

        if profile_to_save not in settings["profiles"]:
            settings["profiles"][profile_to_save] = []

        settings["profiles"][profile_to_save] = playlists
        self.save_settings(settings)
        return playlists

    def save_window_geometry(self, geometry: str):
        """Save window geometry (e.g., '1400x800+100+50')"""
        settings = self.load_settings()
        settings["window_geometry"] = geometry
        self.save_settings(settings)

    def get_window_geometry(self) -> str | None:
        """Get saved window geometry, or None if not set"""
        settings = self.load_settings()
        return settings.get("window_geometry")