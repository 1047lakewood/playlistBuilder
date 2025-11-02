"""Theme Manager for Playlist Builder.
Centralizes theme definitions, provides accessors for colors, and handles
theme selection with optional per-color overrides.

Usage:
    1. Initialize at app startup:
       theme_manager.initialize(config_path)
    
    2. Get colors in widgets:
       bg_color = theme_manager.get_color("notebook_bg", "#f5f5f5")
    
    3. Change theme (from settings dialog):
       theme_manager.save_theme("Dark", overrides={})
    
    4. Register callback for theme changes:
       theme_manager.register_theme_change_callback(my_refresh_function)

Config structure in config.json:
    {
        "theme": {
            "name": "Light",  # One of: Light, Dark, Blue, Warm, High Contrast
            "overrides": {
                "notebook_bg": "#custom_color"  # Optional per-color overrides
            }
        }
    }
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Built-in theme palettes
THEMES = {
    "Light": {
        "notebook_bg": "#f5f5f5",
        "tab_bg": "#e8e8e8",
        "tab_fg": "#606060",
        "selected_tab_bg": "#ffffff",
        "selected_tab_fg": "#303030",
        "active_tab_bg": "#f0f0f0",
        "active_tab_fg": "#404040",
        "treeview_even": "#F9F9F9",
        "treeview_odd": "#FFFFFF",
        "treeview_missing": "#FF3B30",
        "treeview_search_match": "#E8F0FE",
        "treeview_search_current": "#BBDEFB",
        "treeview_playing": "#E0FFE0",
        "search_frame_bg": "#F0F0F0",
        "search_frame_fg": "#505050",
        "search_entry_bg": "#FFFFFF",
        "search_entry_highlight": "#0078D7",
        "search_entry_border": "#E0E0E0",
        "prelisten_bg": "#f0f0f0",
        "prelisten_control_bg": "#e0e0e0",
        "currently_playing_bg": "#d4edda",
        "currently_playing_fg": "#155724",
        "currently_playing_hover": "#0f5132",
    },
    "Dark": {
        "notebook_bg": "#2b2b2b",
        "tab_bg": "#3c3c3c",
        "tab_fg": "#cccccc",
        "selected_tab_bg": "#1e1e1e",
        "selected_tab_fg": "#ffffff",
        "active_tab_bg": "#505050",
        "active_tab_fg": "#e0e0e0",
        "treeview_even": "#2b2b2b",
        "treeview_odd": "#323232",
        "treeview_missing": "#ff6b6b",
        "treeview_search_match": "#3a5a7a",
        "treeview_search_current": "#4a6a8a",
        "treeview_playing": "#2d4a2d",
        "search_frame_bg": "#3c3c3c",
        "search_frame_fg": "#cccccc",
        "search_entry_bg": "#2b2b2b",
        "search_entry_highlight": "#0078D7",
        "search_entry_border": "#555555",
        "prelisten_bg": "#2b2b2b",
        "prelisten_control_bg": "#3c3c3c",
        "currently_playing_bg": "#2d4a2d",
        "currently_playing_fg": "#a8d5a8",
        "currently_playing_hover": "#70b070",
    },
    "Blue": {
        "notebook_bg": "#e6f2ff",
        "tab_bg": "#cce5ff",
        "tab_fg": "#004080",
        "selected_tab_bg": "#ffffff",
        "selected_tab_fg": "#001a33",
        "active_tab_bg": "#b3d9ff",
        "active_tab_fg": "#002952",
        "treeview_even": "#f0f7ff",
        "treeview_odd": "#ffffff",
        "treeview_missing": "#cc0000",
        "treeview_search_match": "#d1e7ff",
        "treeview_search_current": "#99ccff",
        "treeview_playing": "#d4f4dd",
        "search_frame_bg": "#cce5ff",
        "search_frame_fg": "#004080",
        "search_entry_bg": "#ffffff",
        "search_entry_highlight": "#0066cc",
        "search_entry_border": "#99ccff",
        "prelisten_bg": "#e6f2ff",
        "prelisten_control_bg": "#cce5ff",
        "currently_playing_bg": "#d4f4dd",
        "currently_playing_fg": "#006600",
        "currently_playing_hover": "#004d00",
    },
    "Warm": {
        "notebook_bg": "#fff5e6",
        "tab_bg": "#ffe6cc",
        "tab_fg": "#804000",
        "selected_tab_bg": "#ffffff",
        "selected_tab_fg": "#331a00",
        "active_tab_bg": "#ffd9b3",
        "active_tab_fg": "#522900",
        "treeview_even": "#fffaf5",
        "treeview_odd": "#ffffff",
        "treeview_missing": "#cc3300",
        "treeview_search_match": "#ffe7d1",
        "treeview_search_current": "#ffcc99",
        "treeview_playing": "#e6ffe6",
        "search_frame_bg": "#ffe6cc",
        "search_frame_fg": "#804000",
        "search_entry_bg": "#ffffff",
        "search_entry_highlight": "#cc6600",
        "search_entry_border": "#ffcc99",
        "prelisten_bg": "#fff5e6",
        "prelisten_control_bg": "#ffe6cc",
        "currently_playing_bg": "#e6ffe6",
        "currently_playing_fg": "#006600",
        "currently_playing_hover": "#004d00",
    },
    "High Contrast": {
        "notebook_bg": "#000000",
        "tab_bg": "#1a1a1a",
        "tab_fg": "#ffffff",
        "selected_tab_bg": "#ffffff",
        "selected_tab_fg": "#000000",
        "active_tab_bg": "#333333",
        "active_tab_fg": "#ffffff",
        "treeview_even": "#000000",
        "treeview_odd": "#1a1a1a",
        "treeview_missing": "#ff0000",
        "treeview_search_match": "#0066cc",
        "treeview_search_current": "#0099ff",
        "treeview_playing": "#006600",
        "search_frame_bg": "#1a1a1a",
        "search_frame_fg": "#ffffff",
        "search_entry_bg": "#000000",
        "search_entry_highlight": "#00ff00",
        "search_entry_border": "#666666",
        "prelisten_bg": "#000000",
        "prelisten_control_bg": "#1a1a1a",
        "currently_playing_bg": "#006600",
        "currently_playing_fg": "#00ff00",
        "currently_playing_hover": "#00cc00",
    },
}

# Default theme name
DEFAULT_THEME = "Light"

# Global cache for current theme
_current_theme_name: str | None = None
_current_colors: dict[str, str] = {}
_config_path: str = ""
_theme_change_callbacks: list = []


def initialize(config_path: str) -> None:
    """Initialize the theme manager with the config file path."""
    global _config_path
    _config_path = config_path
    reload_theme()


def reload_theme() -> None:
    """Load theme from config.json and apply overrides."""
    global _current_theme_name, _current_colors
    
    if not os.path.exists(_config_path):
        logger.warning("Config file not found; using default theme.")
        _current_theme_name = DEFAULT_THEME
        _current_colors = THEMES[DEFAULT_THEME].copy()
        return
    
    try:
        with open(_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as exc:
        logger.exception("Failed to load config.json: %s", exc)
        _current_theme_name = DEFAULT_THEME
        _current_colors = THEMES[DEFAULT_THEME].copy()
        return
    
    # Get theme name from config
    theme_name = config.get("theme", {}).get("name", DEFAULT_THEME)
    
    # Validate theme name
    if theme_name not in THEMES:
        logger.warning("Unknown theme '%s'; falling back to default.", theme_name)
        theme_name = DEFAULT_THEME
    
    _current_theme_name = theme_name
    _current_colors = THEMES[theme_name].copy()
    
    # Apply any per-color overrides
    overrides = config.get("theme", {}).get("overrides", {})
    for key, value in overrides.items():
        if key in _current_colors:
            _current_colors[key] = value
    
    # Notify callbacks of theme change
    for callback in _theme_change_callbacks:
        try:
            callback()
        except Exception as exc:
            logger.exception("Theme change callback failed: %s", exc)


def get_color(key: str, default: str = "#ffffff") -> str:
    """Get a color value by key."""
    return _current_colors.get(key, default)


def get_theme_name() -> str:
    """Get the current theme name."""
    return _current_theme_name or DEFAULT_THEME


def get_all_colors() -> dict[str, str]:
    """Get all current colors (theme + overrides)."""
    return _current_colors.copy()


def get_available_themes() -> list[str]:
    """Get list of available theme names."""
    return list(THEMES.keys())


def save_theme(theme_name: str, overrides: dict[str, str] | None = None) -> None:
    """Save theme selection and overrides to config.json."""
    if theme_name not in THEMES:
        raise ValueError(f"Unknown theme: {theme_name}")
    
    if not os.path.exists(_config_path):
        config = {}
    else:
        try:
            with open(_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:
            logger.exception("Failed to load config.json: %s", exc)
            config = {}
    
    # Update theme section
    config["theme"] = {
        "name": theme_name,
        "overrides": overrides or {}
    }
    
    # Write back to disk
    try:
        with open(_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as exc:
        logger.exception("Failed to save config.json: %s", exc)
        raise
    
    # Reload theme in memory
    reload_theme()


def register_theme_change_callback(callback) -> None:
    """Register a callback to be called when theme changes."""
    if callback not in _theme_change_callbacks:
        _theme_change_callbacks.append(callback)


def unregister_theme_change_callback(callback) -> None:
    """Unregister a theme change callback."""
    if callback in _theme_change_callbacks:
        _theme_change_callbacks.remove(callback)


def migrate_old_colors(config: dict) -> None:
    """Migrate old 'colors' config to new 'theme' structure.
    Converts the old hardcoded colors to overrides on the Light theme.
    """
    if "colors" in config and "theme" not in config:
        old_colors = config.pop("colors")
        
        # Map old color keys to new keys
        mapping = {
            "notebook_bg": "notebook_bg",
            "tab_bg": "tab_bg",
            "tab_fg": "tab_fg",
            "selected_tab_bg": "selected_tab_bg",
            "selected_tab_fg": "selected_tab_fg",
            "active_tab_bg": "active_tab_bg",
            "active_tab_fg": "active_tab_fg",
        }
        
        overrides = {}
        for old_key, new_key in mapping.items():
            if old_key in old_colors:
                overrides[new_key] = old_colors[old_key]
        
        config["theme"] = {
            "name": "Light",
            "overrides": overrides
        }
        
        logger.info("Migrated old 'colors' config to new 'theme' structure")

