"""Settings Dialog for Playlist Builder
Allows editing of user-configurable settings stored in ``config.json``.
The dialog is split into two panes:
1. Category list on the left.
2. Editor pane on the right with grouped settings fields.

Currently exposes settings for:
- Fonts (family, base size)
- Treeview (row height)
- Paths & Network
- Migration

On Apply / OK the ``config.json`` file is rewritten and the application styles
are updated at runtime by calling ``font_config.configure_ttk_styles``.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from copy import deepcopy

import font_config
import app_config

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

logger = logging.getLogger(__name__)

# Default configuration fallback
DEFAULT_CONFIG: dict = {
    "fonts": {
        "base_size": 13,
        "family": "Segoe UI",
    },
    "treeview": {
        "row_height": 30,
        "heading_padding_x": 5,
        "heading_padding_y": 5,
    },
}


def load_config() -> dict:
    """Load the JSON configuration file, returning an empty dict on failure."""
    if not os.path.exists(CONFIG_PATH):
        logger.warning("Config file not found at %s; using defaults.", CONFIG_PATH)
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as exc:
        logger.exception("Failed to load config.json: %s", exc)
        messagebox.showerror("Settings Error", f"Failed to load settings file:\n{exc}")
        return {}


def save_config(data: dict) -> None:
    """Persist *data* as JSON to ``config.json`` with indentation."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as exc:
        logger.exception("Failed to save config.json: %s", exc)
        messagebox.showerror("Settings Error", f"Failed to save settings file:\n{exc}")
        raise


class SettingsDialog(tk.Toplevel):
    """A modal dialog that lets the user edit application settings."""

    CATEGORY_FONTS = "Fonts"
    CATEGORY_TREEVIEW = "Treeview"
    CATEGORY_PATHS = "Paths"
    CATEGORY_REMOTE_SOURCES = "Remote Sources"
    CATEGORY_MIGRATION = "Migration"

    def __init__(self, master: tk.Tk, on_apply=None):
        super().__init__(master)
        self.title("Settings")
        self.geometry("850x600")
        # Allow resizing so users can adjust if needed
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()  # Make modal

        # Center relative to master
        x = master.winfo_x() + (master.winfo_width() // 2) - (850 // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        self.on_apply = on_apply

        # Load configuration
        self.config_data = load_config()

        # Main layout
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left: category list
        self.category_list = tk.Listbox(paned, exportselection=False)
        for cat in (self.CATEGORY_FONTS, self.CATEGORY_TREEVIEW, self.CATEGORY_PATHS, self.CATEGORY_REMOTE_SOURCES, self.CATEGORY_MIGRATION):
            self.category_list.insert(tk.END, cat)
        self.category_list.bind("<<ListboxSelect>>", self._on_category_selected)
        paned.add(self.category_list, weight=1)
        # Optionally set minimum size via paneconfigure if supported
        try:
            paned.paneconfig(self.category_list, minsize=120)
        except tk.TclError:
            # Some Tk versions don't support minsize; ignore
            pass

        # Right: frame that will contain setting editors
        self.editor_frame_container = ttk.Frame(paned)
        paned.add(self.editor_frame_container, weight=3)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="Reset Defaults", command=self.reset_defaults_clicked).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Apply", command=self.apply_clicked).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="OK", command=self.ok_clicked).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        # Keep mapping from setting path tuple -> Tk variable
        self._vars: dict[tuple[str, ...], tk.Variable] = {}

        # Select first category by default
        self.category_list.selection_set(0)
        self._on_category_selected()

    # -----------------
    # Category Handling
    # -----------------
    def _clear_editor(self):
        for child in self.editor_frame_container.winfo_children():
            child.destroy()
        self._vars.clear()

    def _on_category_selected(self, _event=None):
        selection = self.category_list.curselection()
        if not selection:
            return
        category = self.category_list.get(selection[0])
        self._clear_editor()
        if category == self.CATEGORY_FONTS:
            self._build_fonts_editor()
        elif category == self.CATEGORY_TREEVIEW:
            self._build_treeview_editor()
        elif category == self.CATEGORY_PATHS:
            self._build_paths_editor()
        elif category == self.CATEGORY_REMOTE_SOURCES:
            self._build_remote_sources_editor()
        elif category == self.CATEGORY_MIGRATION:
            self._build_migration_editor()

    # -----------------
    # Editor Builders
    # -----------------
    def _build_fonts_editor(self):
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True)

        family = self._get_setting_var(("fonts", "family"), tk.StringVar, default="Segoe UI")
        size = self._get_setting_var(("fonts", "base_size"), tk.IntVar, default=13)

        ttk.Label(frm, text="Font Family:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        font_families = sorted(set(tkfont.families()))
        ttk.Combobox(frm, values=font_families, textvariable=family, state="readonly").grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)

        ttk.Label(frm, text="Base Size:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Spinbox(frm, from_=6, to=72, textvariable=size, width=5).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        frm.columnconfigure(1, weight=1)

    def _build_paths_editor(self):
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True)

        playlists_dir = self._get_setting_var(("paths","playlists_dir"), tk.StringVar, default="")
        intros_dir = self._get_setting_var(("paths","intros_dir"), tk.StringVar, default="")

        # Helper row builder
        def make_row(row:int, label:str, var:tk.StringVar, browse:bool=False, is_dir:bool=True):
            ttk.Label(frm,text=label).grid(row=row,column=0,sticky=tk.W,pady=3,padx=5)
            entry = ttk.Entry(frm,textvariable=var,width=50)
            entry.grid(row=row,column=1,sticky=tk.EW,pady=3,padx=5)
            if browse:
                def choose():
                    from tkinter import filedialog
                    path = filedialog.askdirectory() if is_dir else filedialog.askopenfilename()
                    if path:
                        var.set(path)
                ttk.Button(frm,text="...",command=choose,width=3).grid(row=row,column=2,sticky=tk.W)
        make_row(0,"Playlists Directory",playlists_dir,browse=True,is_dir=True)
        make_row(1,"Intros Directory",intros_dir,browse=True,is_dir=True)

        # Note about remote sources
        note = ttk.Label(frm, text="Note: Remote station URLs are now configured in the 'Remote Sources' category.",
                        font=("Segoe UI", 9, "italic"))
        note.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(15, 5), padx=5)

        frm.columnconfigure(1,weight=1)

    def _build_treeview_editor(self):
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True)

        row_height = self._get_setting_var(("treeview", "row_height"), tk.IntVar, default=30)

        ttk.Label(frm, text="Row Height:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Spinbox(frm, from_=10, to=100, textvariable=row_height, width=5).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        frm.columnconfigure(1, weight=1)

    def _build_remote_sources_editor(self):
        """Build editor for remote sources configuration."""
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True)

        # Scrollable frame for sources
        self._remote_sources_canvas = tk.Canvas(frm, bg=self.cget("bg"))
        scrollbar = ttk.Scrollbar(frm, orient="vertical", command=self._remote_sources_canvas.yview)
        self._remote_sources_scrollable = ttk.Frame(self._remote_sources_canvas)

        self._remote_sources_scrollable.bind(
            "<Configure>",
            lambda e: self._remote_sources_canvas.configure(scrollregion=self._remote_sources_canvas.bbox("all"))
        )

        self._remote_sources_canvas.create_window((0, 0), window=self._remote_sources_scrollable, anchor="nw")
        self._remote_sources_canvas.configure(yscrollcommand=scrollbar.set)

        self._remote_sources_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Store source data for management (list of dicts with vars and widgets)
        self._source_frames = []
        self._source_widgets = []

        # Build the UI
        self._rebuild_sources_ui()

    def _rebuild_sources_ui(self):
        """Rebuild the remote sources UI from current data."""
        # Clear existing widgets
        for widget in self._remote_sources_scrollable.winfo_children():
            widget.destroy()

        scrollable_frame = self._remote_sources_scrollable

        # Header
        ttk.Label(scrollable_frame, text="Remote Sources", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=5, sticky=tk.W, pady=(0, 10), padx=5)

        # Column headers
        ttk.Label(scrollable_frame, text="Source ID", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=2, padx=5)
        ttk.Label(scrollable_frame, text="Display Name", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=1, sticky=tk.W, pady=2, padx=5)
        ttk.Label(scrollable_frame, text="URL/IP Address", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=2, sticky=tk.W, pady=2, padx=5)
        ttk.Label(scrollable_frame, text="Enabled", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=3, sticky=tk.W, pady=2, padx=5)

        # If no source data yet, load from config
        if not self._source_frames:
            remote_sources = self.config_data.get("network", {}).get("remote_sources", {})
            for source_id, source_config in remote_sources.items():
                self._source_frames.append({
                    "id": source_id,
                    "name": source_config.get("name", ""),
                    "url": source_config.get("url", ""),
                    "enabled": source_config.get("enabled", True)
                })

        # Add source rows
        row = 2
        for idx, source_data in enumerate(self._source_frames):
            self._create_source_row(scrollable_frame, row, idx, source_data)
            row += 1

        # Add new source button
        ttk.Button(scrollable_frame, text="+ Add New Source", command=self._add_new_source).grid(
            row=row, column=0, columnspan=5, sticky=tk.EW, pady=10, padx=5)
        row += 1

        # Instructions
        instructions = ttk.Label(scrollable_frame, text=(
            "Configure remote playlist sources. Each source needs a unique ID, display name, and URL.\n"
            "URL format: http://ip:port/?pass=password\n"
            "Changes take effect after applying settings and restarting the application."
        ), wraplength=600, justify=tk.LEFT)
        instructions.grid(row=row, column=0, columnspan=5, sticky=tk.W, pady=(10, 5), padx=5)

        # Update canvas scroll region
        scrollable_frame.update_idletasks()
        self._remote_sources_canvas.configure(scrollregion=self._remote_sources_canvas.bbox("all"))

    def _create_source_row(self, parent, row, idx, source_data):
        """Create a row for a remote source."""
        # Source ID entry
        id_var = tk.StringVar(value=source_data.get("id", ""))
        id_entry = ttk.Entry(parent, textvariable=id_var, width=12)
        id_entry.grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)

        # Name entry
        name_var = tk.StringVar(value=source_data.get("name", ""))
        name_entry = ttk.Entry(parent, textvariable=name_var, width=20)
        name_entry.grid(row=row, column=1, sticky=tk.W, pady=2, padx=5)

        # URL entry
        url_var = tk.StringVar(value=source_data.get("url", ""))
        url_entry = ttk.Entry(parent, textvariable=url_var, width=35)
        url_entry.grid(row=row, column=2, sticky=tk.W, pady=2, padx=5)

        # Enabled checkbox
        enabled_var = tk.BooleanVar(value=source_data.get("enabled", True))
        enabled_check = ttk.Checkbutton(parent, variable=enabled_var)
        enabled_check.grid(row=row, column=3, sticky=tk.W, pady=2, padx=5)

        # Remove button
        remove_btn = ttk.Button(parent, text="Remove", command=lambda i=idx: self._remove_source(i), width=8)
        remove_btn.grid(row=row, column=4, sticky=tk.W, pady=2, padx=5)

        # Update source_data with vars for later retrieval
        source_data["id_var"] = id_var
        source_data["name_var"] = name_var
        source_data["url_var"] = url_var
        source_data["enabled_var"] = enabled_var

    def _add_new_source(self):
        """Add a new source."""
        # Save current values from UI before rebuilding
        self._sync_source_data_from_ui()
        
        # Add new source data
        new_id = f"source_{len(self._source_frames) + 1}"
        self._source_frames.append({
            "id": new_id,
            "name": "",
            "url": "http://",
            "enabled": True
        })
        
        # Rebuild UI
        self._rebuild_sources_ui()

    def _remove_source(self, idx):
        """Remove a source by index."""
        # Save current values from UI before removing
        self._sync_source_data_from_ui()
        
        if 0 <= idx < len(self._source_frames):
            del self._source_frames[idx]
        
        # Rebuild UI
        self._rebuild_sources_ui()

    def _sync_source_data_from_ui(self):
        """Sync source data from UI variables."""
        for source_data in self._source_frames:
            if "id_var" in source_data:
                source_data["id"] = source_data["id_var"].get()
            if "name_var" in source_data:
                source_data["name"] = source_data["name_var"].get()
            if "url_var" in source_data:
                source_data["url"] = source_data["url_var"].get()
            if "enabled_var" in source_data:
                source_data["enabled"] = source_data["enabled_var"].get()

    def _build_migration_editor(self):
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Deployment path field
        deployment_dir = self._get_setting_var(("paths", "deployment_dir"), tk.StringVar, default=r"g:\work\playlist builder 2")
        
        ttk.Label(frm, text="Deployment Path:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        entry = ttk.Entry(frm, textvariable=deployment_dir, width=50)
        entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=5)
        
        def browse_deployment():
            path = filedialog.askdirectory(initialdir=deployment_dir.get() if deployment_dir.get() else os.path.expanduser("~"))
            if path:
                deployment_dir.set(path)
        
        ttk.Button(frm, text="...", command=browse_deployment, width=3).grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # Buttons frame
        btn_frm = ttk.Frame(frm)
        btn_frm.grid(row=1, column=0, columnspan=3, pady=20, sticky=tk.EW)
        
        ttk.Button(btn_frm, text="Import Config Files", command=self._import_config_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frm, text="Export Config Files", command=self._export_config_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frm, text="Full Deployment", command=self._full_deployment).pack(side=tk.LEFT, padx=5)
        
        frm.columnconfigure(1, weight=1)

    # -----------------
    # Helpers
    # -----------------
    def _get_setting_var(self, path: tuple[str, ...], var_cls, default=None):
        """Return a Tk Variable bound to *path* in self.config_data."""
        if path in self._vars:
            return self._vars[path]
        # Drill down config dict to get current value or default
        node = self.config_data
        for key in path[:-1]:
            node = node.setdefault(key, {})
        leaf_key = path[-1]
        if leaf_key not in node:
            node[leaf_key] = default
        value = node[leaf_key]
        var = var_cls(value=value, master=self)
        self._vars[path] = var
        return var

    def _update_config_from_vars(self):
        for path, var in self._vars.items():
            node = self.config_data
            for key in path[:-1]:
                node = node.setdefault(key, {})
            node[path[-1]] = var.get()

        # Handle remote sources
        if hasattr(self, '_source_frames') and self._source_frames:
            # Sync data from UI first
            self._sync_source_data_from_ui()
            
            remote_sources = {}
            for source_data in self._source_frames:
                source_id = source_data.get("id", "").strip()
                if source_id:  # Skip empty/invalid sources
                    remote_sources[source_id] = {
                        "name": source_data.get("name", "").strip(),
                        "url": source_data.get("url", "").strip(),
                        "enabled": source_data.get("enabled", True)
                    }

            # Ensure network section exists
            network_node = self.config_data.setdefault("network", {})
            network_node["remote_sources"] = remote_sources

    # -----------------
    # Button callbacks
    # -----------------
    URL_REGEX = re.compile(r"^https?://.+", re.IGNORECASE)

    def _validate_before_save(self) -> bool:
        """Return True if all fields are valid, else show error and return False."""
        for path in self._vars:
            if path == ("treeview", "row_height"):
                try:
                    if int(self._vars[path].get()) <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Invalid Row Height", "Row height must be a positive integer")
                    return False

        # Validate remote sources
        if hasattr(self, '_source_frames') and self._source_frames:
            # Sync data from UI first
            self._sync_source_data_from_ui()
            
            seen_ids = set()
            for source_data in self._source_frames:
                source_id = source_data.get("id", "").strip()
                name = source_data.get("name", "").strip()
                url = source_data.get("url", "").strip()

                # Check for empty fields
                if not source_id:
                    messagebox.showerror("Invalid Remote Source", "Source ID cannot be empty")
                    return False
                if not name:
                    messagebox.showerror("Invalid Remote Source", f"Display name cannot be empty for source '{source_id}'")
                    return False
                if not url:
                    messagebox.showerror("Invalid Remote Source", f"URL cannot be empty for source '{source_id}'")
                    return False

                # Check for duplicate IDs
                if source_id in seen_ids:
                    messagebox.showerror("Invalid Remote Source", f"Duplicate source ID: '{source_id}'")
                    return False
                seen_ids.add(source_id)

                # Validate URL format
                if not self.URL_REGEX.match(url):
                    messagebox.showerror("Invalid Remote Source", f"Invalid URL format for source '{source_id}': {url}")
                    return False

        return True

    def apply_clicked(self):
        if not self._validate_before_save():
            return
        self._update_config_from_vars()
        
        save_config(self.config_data)
        # Reload the config in memory so app_config.get() returns updated values
        app_config.reload_config()

        # Reload remote sources registry if it exists
        try:
            from PlaylistService.api_playlist_manager import RemotePlaylistRegistry
            RemotePlaylistRegistry().reload()
        except ImportError:
            pass  # RemotePlaylistRegistry may not be available during initial setup

        try:
            font_config.configure_ttk_styles()
        except Exception:
            # Capture but still keep dialog open
            logger.exception("Failed to reconfigure ttk styles after settings apply")
        # Notify caller if provided
        if callable(self.on_apply):
            try:
                self.on_apply()
            except Exception:  # noqa: broad-except
                logger.exception("on_apply callback raised an exception")

    def reset_defaults_clicked(self):
        if messagebox.askyesno("Reset Defaults", "Reset all settings to factory defaults? This will not affect remote sources configuration."):
            # Preserve remote sources before resetting
            remote_sources = self.config_data.get("network", {}).get("remote_sources", {})

            self.config_data = deepcopy(DEFAULT_CONFIG)

            # Restore remote sources
            if remote_sources:
                self.config_data.setdefault("network", {})["remote_sources"] = remote_sources

            # Rebuild current editor and other UI
            self._on_category_selected()

    def ok_clicked(self):
        self.apply_clicked()
        self.destroy()
        # Reload config one more time to ensure it's current
        app_config.reload_config()

    # -----------------
    # Migration methods
    # -----------------
    def _get_deployment_path(self) -> str:
        """Get the deployment path from UI variable or config, with default fallback."""
        path_key = ("paths", "deployment_dir")
        if path_key in self._vars:
            path = self._vars[path_key].get()
            if path:
                return path
        # Fallback to config data or default
        node = self.config_data.get("paths", {})
        return node.get("deployment_dir", r"g:\work\playlist builder 2")

    def _import_config_files(self):
        """Import config.json and settings.json from deployment location."""
        try:
            deployment_path = self._get_deployment_path()
            if not os.path.exists(deployment_path):
                messagebox.showerror("Error", f"Deployment directory does not exist:\n{deployment_path}")
                return

            source_config = os.path.join(deployment_path, "config.json")
            source_settings = os.path.join(deployment_path, "settings.json")
            
            if os.path.exists(source_config):
                shutil.copy2(source_config, CONFIG_PATH)
            else:
                messagebox.showerror("Error", f"config.json not found in deployment directory:\n{deployment_path}")
                return
            
            settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
            if os.path.exists(source_settings):
                shutil.copy2(source_settings, settings_path)
            
            # Reload config after import
            self.config_data = load_config()
            app_config.reload_config()
        except Exception as exc:
            logger.exception("Failed to import config files")
            messagebox.showerror("Error", f"Failed to import config files:\n{exc}")

    def _export_config_files(self):
        """Export config.json and settings.json to deployment location."""
        try:
            deployment_path = self._get_deployment_path()
            
            # Create deployment directory if it doesn't exist
            if not os.path.exists(deployment_path):
                os.makedirs(deployment_path, exist_ok=True)

            # Save current config before exporting
            self._update_config_from_vars()
            save_config(self.config_data)
            
            target_config = os.path.join(deployment_path, "config.json")
            target_settings = os.path.join(deployment_path, "settings.json")
            
            if os.path.exists(CONFIG_PATH):
                shutil.copy2(CONFIG_PATH, target_config)
            
            settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
            if os.path.exists(settings_path):
                shutil.copy2(settings_path, target_settings)
        except Exception as exc:
            logger.exception("Failed to export config files")
            messagebox.showerror("Error", f"Failed to export config files:\n{exc}")

    def _full_deployment(self):
        """Copy all files from current directory to deployment location."""
        try:
            deployment_path = self._get_deployment_path()
            source_path = os.path.dirname(__file__)
            
            if not os.path.exists(source_path):
                messagebox.showerror("Error", f"Source directory does not exist:\n{source_path}")
                return
            
            # Create deployment directory if it doesn't exist
            if not os.path.exists(deployment_path):
                os.makedirs(deployment_path, exist_ok=True)

            # Save current config before deploying
            self._update_config_from_vars()
            save_config(self.config_data)

            # Get list of all files and directories to copy
            items_to_copy = []
            # Directories to skip during deployment
            skip_items = {"__pycache__", ".git", ".vscode", ".idea", "docs", "venv", ".env"}
            for item in os.listdir(source_path):
                item_path = os.path.join(source_path, item)
                # Skip development directories
                if item in skip_items:
                    continue
                items_to_copy.append(item)

            # Copy files and directories
            for item in items_to_copy:
                source_item = os.path.join(source_path, item)
                dest_item = os.path.join(deployment_path, item)
                
                if os.path.isdir(source_item):
                    if os.path.exists(dest_item):
                        shutil.rmtree(dest_item)
                    shutil.copytree(source_item, dest_item, ignore=shutil.ignore_patterns("__pycache__"))
                else:
                    shutil.copy2(source_item, dest_item)
                    
        except Exception as exc:
            logger.exception("Failed to deploy files")
            messagebox.showerror("Error", f"Failed to deploy files:\n{exc}")
