"""
Font configuration for the Playlist Builder application.
This module provides centralized font settings that can be used across the application.
"""
import tkinter as tk
from tkinter.font import Font
import json, os, logging
import theme_manager

# Base font size - can be adjusted to make all text bigger or smaller
BASE_FONT_SIZE = 13

# Default font family - using a more modern font
DEFAULT_FONT_FAMILY = "Segoe UI"  # More modern font (Windows default)

# Font configurations as tuples for widgets that don't accept Font objects
DEFAULT_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE)
BOLD_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE, "bold")
SMALL_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE-2)
LARGE_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE+2)
HEADER_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE+2, "bold")

# Font objects will be initialized when configure_fonts is called
DEFAULT_FONT = None
BOLD_FONT = None
SMALL_FONT = None
LARGE_FONT = None
HEADER_FONT = None

def initialize_fonts():
    """Initialize font objects after Tkinter root is created"""
    global DEFAULT_FONT, BOLD_FONT, SMALL_FONT, LARGE_FONT, HEADER_FONT
    
    # Create font objects for different uses
    DEFAULT_FONT = Font(family=DEFAULT_FONT_FAMILY, size=BASE_FONT_SIZE)
    BOLD_FONT = Font(family=DEFAULT_FONT_FAMILY, size=BASE_FONT_SIZE, weight="bold")
    SMALL_FONT = Font(family=DEFAULT_FONT_FAMILY, size=BASE_FONT_SIZE-2)
    LARGE_FONT = Font(family=DEFAULT_FONT_FAMILY, size=BASE_FONT_SIZE+2)
    HEADER_FONT = Font(family=DEFAULT_FONT_FAMILY, size=BASE_FONT_SIZE+2, weight="bold")

def configure_ttk_styles():
    """Configure ttk styles using values from ``config.json``.
    This can be called repeatedly (e.g. after SettingsDialog → Apply) to
    refresh fonts, colors, and geometry across the application.
    """
    from tkinter import ttk

    # Load configuration
    try:
        cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception as exc:  # noqa: broad-except
        logging.warning("font_config: failed to read config.json – using defaults (%s)", exc)
        cfg = {}

    fonts_cfg = cfg.get("fonts", {})
    tree_cfg = cfg.get("treeview", {})
    
    # Reload theme colors
    theme_manager.reload_theme()

    # Update globals so other modules see new font values
    global BASE_FONT_SIZE, DEFAULT_FONT_FAMILY
    global DEFAULT_FONT_TUPLE, BOLD_FONT_TUPLE, SMALL_FONT_TUPLE, LARGE_FONT_TUPLE, HEADER_FONT_TUPLE

    BASE_FONT_SIZE = fonts_cfg.get("base_size", BASE_FONT_SIZE)
    DEFAULT_FONT_FAMILY = fonts_cfg.get("family", DEFAULT_FONT_FAMILY)

    DEFAULT_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE)
    BOLD_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE, "bold")
    SMALL_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE - 2)
    LARGE_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE + 2)
    HEADER_FONT_TUPLE = (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE + 2, "bold")

    # Recreate Font objects with new parameters
    initialize_fonts()

    style = ttk.Style()

    # Treeview configuration
    style.configure(
        "Treeview",
        font=DEFAULT_FONT_TUPLE,
        rowheight=tree_cfg.get("row_height", 30),
    )
    style.configure(
        "Treeview.Heading",
        font=BOLD_FONT_TUPLE,
        padding=(
            tree_cfg.get("heading_padding_x", 5),
            tree_cfg.get("heading_padding_y", 5),
        ),
    )

    # Notebook (tabs) styling
    style.configure(
        "TNotebook",
        padding=(0, 0),
        background=theme_manager.get_color("notebook_bg", "#f5f5f5"),
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        font=(DEFAULT_FONT_FAMILY, BASE_FONT_SIZE),
        padding=(5, 5),
        background=theme_manager.get_color("tab_bg", "#e8e8e8"),
        foreground=theme_manager.get_color("tab_fg", "#606060"),
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", theme_manager.get_color("selected_tab_bg", "#ffffff")),
            ("active", theme_manager.get_color("active_tab_bg", "#f0f0f0")),
        ],
        foreground=[
            ("selected", theme_manager.get_color("selected_tab_fg", "#303030")),
            ("active", theme_manager.get_color("active_tab_fg", "#404040")),
        ],
        font=[("selected", (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE, "bold"))],
        borderwidth=[("selected", 0)],
    )

    # Notebook frame background
    style.configure(
        "NotebookFrame.TFrame",
        background=theme_manager.get_color("notebook_bg", "#f5f5f5"),
        borderwidth=0,
        relief="flat",
    )

    # Generic widget fonts
    style.configure("TButton", font=DEFAULT_FONT_TUPLE, padding=(10, 5))
    style.configure("TLabel", font=DEFAULT_FONT_TUPLE)
    style.configure("TEntry", font=DEFAULT_FONT_TUPLE)
    style.configure("TCombobox", font=DEFAULT_FONT_TUPLE)
    style.configure("TCheckbutton", font=DEFAULT_FONT_TUPLE)
    style.configure("TRadiobutton", font=DEFAULT_FONT_TUPLE)
