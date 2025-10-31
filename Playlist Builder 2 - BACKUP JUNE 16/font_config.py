"""
Font configuration for the Playlist Builder application.
This module provides centralized font settings that can be used across the application.
"""
import tkinter as tk
from tkinter.font import Font

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
    """Configure ttk styles with the application fonts"""
    # Initialize font objects first
    initialize_fonts()
    
    style = tk.ttk.Style()
    
    # Configure Treeview to use the default font and increase row height
    style.configure("Treeview", 
                   font=DEFAULT_FONT_TUPLE, 
                   rowheight=30)  # Increased row height for better spacing
    
    style.configure("Treeview.Heading", 
                   font=BOLD_FONT_TUPLE,  # Make headings bold
                   padding=(5, 5))  # Add padding to headings
    
    # Configure Notebook (tabs) with modern styling
    style.configure("TNotebook", 
                   padding=(0, 0),
                   background="#f5f5f5",
                   borderwidth=0)
    
    # Style for the notebook tabs
    style.configure("TNotebook.Tab", 
                   font=(DEFAULT_FONT_FAMILY, BASE_FONT_SIZE),
                   padding=(5, 5),  # Wider tabs with more vertical padding
                   background="#e8e8e8",
                   foreground="#606060",
                   borderwidth=0,
                   relief="flat")
    
    # Style for selected tab
    style.map("TNotebook.Tab",
             background=[('selected', '#ffffff'), ('active', '#f0f0f0')],
             foreground=[('selected', '#303030'), ('active', '#404040')],
             expand=[('selected', [1, 1, 1, 0])],
             font=[('selected', (DEFAULT_FONT_FAMILY, BASE_FONT_SIZE, 'bold'))],
             borderwidth=[('selected', 0)])
             
    # Add a custom style for the notebook frame
    style.configure("NotebookFrame.TFrame", 
                   background="#f5f5f5",
                   borderwidth=0,
                   relief="flat")
    
    # Configure other ttk widgets
    style.configure("TButton", font=DEFAULT_FONT_TUPLE, padding=(10, 5))
    style.configure("TLabel", font=DEFAULT_FONT_TUPLE)
    style.configure("TEntry", font=DEFAULT_FONT_TUPLE)
    style.configure("TCombobox", font=DEFAULT_FONT_TUPLE)
    style.configure("TCheckbutton", font=DEFAULT_FONT_TUPLE)
    style.configure("TRadiobutton", font=DEFAULT_FONT_TUPLE)
