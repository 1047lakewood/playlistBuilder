import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.font import Font


class MenuBar(tk.Menu):
    
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.callbacks = {}
        
        # Track which remote sources are shown (by source_id)
        self._remote_source_vars: dict[str, tk.BooleanVar] = {}
        self._remote_source_menu: tk.Menu = None
        
        # Legacy variable for backwards compatibility
        self.show_api_playlist = tk.BooleanVar()
        self.show_api_playlist.set(False)

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
        
        # Profile submenu
        profile_menu = tk.Menu(file_menu, tearoff=0)
        
        if "save_profile" in self.callbacks:
            profile_menu.add_command(label=f"Save Profile", command=self.callbacks["save_profile"], accelerator=display_names.get("save_profile", ""))
        if "load_profile" in self.callbacks:
            profile_menu.add_command(label=f"Load Profile", command=self.callbacks["load_profile"], accelerator=display_names.get("load_profile", ""))
        if "manage_profiles" in self.callbacks:
            profile_menu.add_command(label=f"Manage Profiles", command=self.callbacks["manage_profiles"], accelerator=display_names.get("manage_profiles", ""))
        file_menu.add_separator()
        file_menu.add_cascade(label="Profiles", menu=profile_menu)

        # Add separator then Settings at end of File menu
        if "settings" in self.callbacks:
            file_menu.add_separator()
            file_menu.add_command(label="Settings", command=self.callbacks["settings"], accelerator="")
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
        
        # Playlist Menu (NEW - for remote sources)
        playlist_menu = tk.Menu(self, tearoff=0)
        
        # Remote Sources submenu
        self._remote_source_menu = tk.Menu(playlist_menu, tearoff=0)
        playlist_menu.add_cascade(label="Remote Sources", menu=self._remote_source_menu)
        
        # Separator and refresh option
        playlist_menu.add_separator()
        if "reload_api_playlist" in self.callbacks:
            playlist_menu.add_command(
                label="Refresh Active Remote", 
                command=self.callbacks["reload_api_playlist"],
                accelerator=display_names.get("reload_api_playlist", "")
            )
        
        if "disconnect_all_remotes" in self.callbacks:
            playlist_menu.add_command(
                label="Disconnect All", 
                command=self.callbacks["disconnect_all_remotes"]
            )
        
        self.add_cascade(label="Playlist", menu=playlist_menu)
        
        # View Menu
        view_menu = tk.Menu(self, tearoff=0)
        # Legacy toggle - kept for backwards compatibility
        if "toggle_api_playlist" in self.callbacks:
            view_menu.add_checkbutton(
                label="Show Remote Playlist (Legacy)", 
                variable=self.show_api_playlist, 
                command=self.callbacks["toggle_api_playlist"], 
                accelerator=display_names.get("toggle_api_playlist", "")
            )
        self.add_cascade(label="View", menu=view_menu)
        
        # Help Menu
        help_menu = tk.Menu(self, tearoff=0)
        if "about" in self.callbacks:
            help_menu.add_command(label="About", command=self.callbacks["about"])
        self.add_cascade(label="Help", menu=help_menu)
    
    def populate_remote_sources(self, sources: list, toggle_callback):
        """Populate the remote sources submenu with available sources.
        
        Args:
            sources: List of (source_id, name) tuples
            toggle_callback: Function to call when a source is toggled, 
                           receives (source_id, show: bool)
        """
        # Clear existing items
        self._remote_source_menu.delete(0, tk.END)
        self._remote_source_vars.clear()
        
        if not sources:
            self._remote_source_menu.add_command(label="No sources configured", state=tk.DISABLED)
            return
        
        for source_id, name in sources:
            var = tk.BooleanVar(value=False)
            self._remote_source_vars[source_id] = var
            
            self._remote_source_menu.add_checkbutton(
                label=name,
                variable=var,
                command=lambda sid=source_id, v=var: toggle_callback(sid, v.get())
            )
        
        # Add separator and "Connect All" / "Disconnect All" options
        self._remote_source_menu.add_separator()
        self._remote_source_menu.add_command(
            label="Connect All",
            command=lambda: self._connect_all_sources(toggle_callback)
        )
        self._remote_source_menu.add_command(
            label="Disconnect All",
            command=lambda: self._disconnect_all_sources(toggle_callback)
        )
    
    def _connect_all_sources(self, toggle_callback):
        """Connect all remote sources."""
        for source_id, var in self._remote_source_vars.items():
            if not var.get():
                var.set(True)
                toggle_callback(source_id, True)
    
    def _disconnect_all_sources(self, toggle_callback):
        """Disconnect all remote sources."""
        for source_id, var in self._remote_source_vars.items():
            if var.get():
                var.set(False)
                toggle_callback(source_id, False)
    
    def set_source_connected(self, source_id: str, connected: bool):
        """Update the checkbox state for a source."""
        if source_id in self._remote_source_vars:
            self._remote_source_vars[source_id].set(connected)
    
    def is_source_shown(self, source_id: str) -> bool:
        """Check if a source is currently shown."""
        if source_id in self._remote_source_vars:
            return self._remote_source_vars[source_id].get()
        return False
