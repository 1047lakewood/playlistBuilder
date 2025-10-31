from gc import callbacks
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.font import Font

class MenuBar(tk.Menu):
    
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.callbacks = {}
        self.show_api_playlist = tk.BooleanVar()
        self.show_api_playlist.set(False) # Default to not showing

    def create_menu_bar(self, callbacks, display_names):
        self.callbacks = callbacks
        # File Menu
        file_menu = tk.Menu(self, tearoff=0)
        if "open" in self.callbacks:
            file_menu.add_command(label=f"Open", command=self.callbacks["open"], accelerator=display_names["open"])
        if "save" in self.callbacks:
            file_menu.add_command(label=f"Save", command=self.callbacks["save"], accelerator=display_names["save"])
        if "save_as" in self.callbacks:
            file_menu.add_command(label=f"Save As", command=self.callbacks["save_as"], accelerator=display_names["save_as"])
        # Add separator before profile options
        file_menu.add_separator()
        
        # Profile submenu
        profile_menu = tk.Menu(file_menu, tearoff=0)
        
        if "save_profile" in self.callbacks:
            profile_menu.add_command(label=f"Save Profile", command=self.callbacks["save_profile"], accelerator=display_names.get("save_profile", ""))
        if "load_profile" in self.callbacks:
            profile_menu.add_command(label=f"Load Profile", command=self.callbacks["load_profile"], accelerator=display_names.get("load_profile", ""))
        if "manage_profiles" in self.callbacks:
            profile_menu.add_command(label=f"Manage Profiles", command=self.callbacks["manage_profiles"], accelerator=display_names.get("manage_profiles", ""))
            
        file_menu.add_cascade(label="Profiles", menu=profile_menu)
        self.add_cascade(label="File", menu=file_menu)
        
        # Edit Menu
        edit_menu = tk.Menu(self, tearoff=0)
        if "copy" in self.callbacks:
            edit_menu.add_command(label="Copy", command=self.callbacks["copy"], accelerator=display_names.get("copy", ""))
        if "cut" in self.callbacks:
            edit_menu.add_command(label="Cut", command=self.callbacks["cut"], accelerator=display_names.get("cut", ""))
        if "paste" in self.callbacks:
            edit_menu.add_command(label="Paste", command=self.callbacks["paste"], accelerator=display_names.get("paste", ""))
        if "delete" in self.callbacks:
            edit_menu.add_command(label="Delete", command=self.callbacks["delete"], accelerator=display_names.get("delete", ""))
        
        # Add separator before find option
        edit_menu.add_separator()
        
        if "search" in self.callbacks:
            edit_menu.add_command(label="Find", command=self.callbacks["search"], accelerator=display_names.get("search", ""))
        
        self.add_cascade(label="Edit", menu=edit_menu)
        
        # View Menu
        view_menu = tk.Menu(self, tearoff=0)
        if "toggle_api_playlist" in self.callbacks:
            view_menu.add_checkbutton(label="Show Remote Playlist", variable=self.show_api_playlist, 
                                     command=self.callbacks["toggle_api_playlist"], 
                                     accelerator=display_names.get("toggle_api_playlist", ""))
        self.add_cascade(label="View", menu=view_menu)
        
        # Help Menu
        help_menu = tk.Menu(self, tearoff=0)
        if "about" in self.callbacks:
            help_menu.add_command(label="About", command=self.callbacks["about"])
        self.add_cascade(label="Help", menu=help_menu)
