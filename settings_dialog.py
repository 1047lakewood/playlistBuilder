"""Settings Dialog for Playlist Builder
Allows editing of user-configurable settings stored in ``config.json``.
The dialog is split into two panes:
1. Category list on the left.
2. Editor pane on the right with grouped settings fields.

Currently exposes settings for:
- Fonts (family, base size)
- Colors (various UI colors)
- Treeview (row height)

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
from tkinter import ttk, messagebox, colorchooser, filedialog
from tkinter import font as tkfont
from copy import deepcopy

import font_config
import app_config
import theme_manager

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

logger = logging.getLogger(__name__)

# Default configuration fallback
DEFAULT_CONFIG: dict = {
    "fonts": {
        "base_size": 13,
        "family": "Segoe UI",
    },
    "theme": {
        "name": "Light",
        "overrides": {}
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
        # Migrate old colors format if needed
        theme_manager.migrate_old_colors(config)
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
    CATEGORY_COLORS = "Colors"
    CATEGORY_TREEVIEW = "Treeview"
    CATEGORY_PATHS_NET = "Paths & Network"
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
        for cat in (self.CATEGORY_FONTS, self.CATEGORY_COLORS, self.CATEGORY_TREEVIEW, self.CATEGORY_PATHS_NET, self.CATEGORY_MIGRATION):
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
        elif category == self.CATEGORY_COLORS:
            self._build_colors_editor()
        elif category == self.CATEGORY_TREEVIEW:
            self._build_treeview_editor()
        elif category == self.CATEGORY_PATHS_NET:
            self._build_paths_network_editor()
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

    def _build_colors_editor(self):
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Theme selection at the top
        theme_frame = ttk.LabelFrame(frm, text="Theme Selection", padding=10)
        theme_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(theme_frame, text="Select Theme:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        theme_var = self._get_setting_var(("theme", "name"), tk.StringVar, default=theme_manager.DEFAULT_THEME)
        theme_combo = ttk.Combobox(
            theme_frame, 
            values=theme_manager.get_available_themes(), 
            textvariable=theme_var, 
            state="readonly",
            width=20
        )
        theme_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Preview button
        def preview_theme():
            self._apply_theme_preview(theme_var.get())
        
        ttk.Button(theme_frame, text="Preview", command=preview_theme).grid(row=0, column=2, padx=5)
        
        # Description label
        desc_label = ttk.Label(theme_frame, text="Select a theme and click Preview to see changes", 
                              foreground="gray")
        desc_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 0))
        
        # Color overrides section
        override_frame = ttk.LabelFrame(frm, text="Color Overrides (Optional)", padding=10)
        override_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create a scrollable frame for color overrides
        canvas = tk.Canvas(override_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(override_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Helper to create color override row
        def make_color_row(row: int, label: str, color_key: str):
            var = self._get_setting_var(("theme", "overrides", color_key), tk.StringVar, 
                                       default=theme_manager.THEMES[theme_manager.DEFAULT_THEME].get(color_key, "#ffffff"))
            
            ttk.Label(scrollable_frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
            ent = ttk.Entry(scrollable_frame, textvariable=var, width=12)
            ent.grid(row=row, column=1, sticky=tk.W, pady=3, padx=5)
            
            # Color preview square
            preview_label = tk.Label(scrollable_frame, text="   ", bg=var.get(), 
                                    relief="solid", borderwidth=1, width=3)
            preview_label.grid(row=row, column=2, pady=3, padx=2)
            
            def pick_color():
                initial_color = var.get()
                color = colorchooser.askcolor(color=initial_color, parent=self)[1]
                if color:
                    var.set(color)
                    preview_label.config(bg=color)
            
            ttk.Button(scrollable_frame, text="...", width=3, command=pick_color).grid(row=row, column=3, sticky=tk.W, padx=2)
            
            # Reset button to revert to theme default
            def reset_to_theme():
                current_theme = theme_var.get()
                default_color = theme_manager.THEMES.get(current_theme, {}).get(color_key, "#ffffff")
                var.set(default_color)
                preview_label.config(bg=default_color)
            
            ttk.Button(scrollable_frame, text="↺", width=2, command=reset_to_theme).grid(row=row, column=4, sticky=tk.W, padx=2)
        
        # Color override settings organized by category
        color_settings = [
            # Notebook/Tabs
            ("Notebook Background", "notebook_bg"),
            ("Tab Background", "tab_bg"),
            ("Tab Foreground", "tab_fg"),
            ("Selected Tab Background", "selected_tab_bg"),
            ("Selected Tab Foreground", "selected_tab_fg"),
            ("Active Tab Background", "active_tab_bg"),
            ("Active Tab Foreground", "active_tab_fg"),
            # Treeview
            ("Treeview Even Row", "treeview_even"),
            ("Treeview Odd Row", "treeview_odd"),
            ("Treeview Missing File", "treeview_missing"),
            ("Treeview Search Match", "treeview_search_match"),
            ("Treeview Search Current", "treeview_search_current"),
            ("Treeview Playing Track", "treeview_playing"),
            # Search Frame
            ("Search Frame Background", "search_frame_bg"),
            ("Search Frame Foreground", "search_frame_fg"),
            ("Search Entry Background", "search_entry_bg"),
            ("Search Entry Highlight", "search_entry_highlight"),
            ("Search Entry Border", "search_entry_border"),
            # Prelisten
            ("Prelisten Background", "prelisten_bg"),
            ("Prelisten Control Background", "prelisten_control_bg"),
            # Currently Playing
            ("Currently Playing Background", "currently_playing_bg"),
            ("Currently Playing Foreground", "currently_playing_fg"),
            ("Currently Playing Hover", "currently_playing_hover"),
        ]
        
        for idx, (lbl, key) in enumerate(color_settings):
            make_color_row(idx, lbl, key)
        
        scrollable_frame.columnconfigure(1, weight=1)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def _apply_theme_preview(self, theme_name: str):
        """Apply theme preview by temporarily loading the theme."""
        try:
            # Temporarily save and apply the theme
            current_config = self.config_data.copy()
            if "theme" not in current_config:
                current_config["theme"] = {}
            current_config["theme"]["name"] = theme_name
            
            # Save temporarily
            save_config(current_config)
            
            # Reload and apply
            theme_manager.reload_theme()
            font_config.configure_ttk_styles()
            
            messagebox.showinfo("Preview Applied", 
                              f"Theme '{theme_name}' has been previewed. Click Apply or OK to save changes.")
        except Exception as exc:
            logger.exception("Failed to preview theme")
            messagebox.showerror("Preview Error", f"Failed to preview theme:\n{exc}")

    def _build_paths_network_editor(self):
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True)

        playlists_dir = self._get_setting_var(("paths","playlists_dir"), tk.StringVar, default="")
        intros_dir = self._get_setting_var(("paths","intros_dir"), tk.StringVar, default="")
        api_url = self._get_setting_var(("network","api_url_base"), tk.StringVar, default="")

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
        make_row(2,"API URL",api_url,browse=False,is_dir=False)
        frm.columnconfigure(1,weight=1)

    def _build_treeview_editor(self):
        frm = ttk.Frame(self.editor_frame_container)
        frm.pack(fill=tk.BOTH, expand=True)

        row_height = self._get_setting_var(("treeview", "row_height"), tk.IntVar, default=30)

        ttk.Label(frm, text="Row Height:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Spinbox(frm, from_=10, to=100, textvariable=row_height, width=5).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        frm.columnconfigure(1, weight=1)

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

    # -----------------
    # Button callbacks
    # -----------------
    URL_REGEX = re.compile(r"^https?://.+", re.IGNORECASE)
    COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")

    def _validate_before_save(self) -> bool:
        """Return True if all fields are valid, else show error and return False."""
        # Validate colors (both old format and new theme overrides)
        for path in self._vars:
            if path[0] == "colors" or (len(path) > 1 and path[0] == "theme" and path[1] == "overrides"):
                val = self._vars[path].get()
                if val and not self.COLOR_REGEX.match(val):
                    messagebox.showerror("Invalid Color", f"{val} is not a valid hex color (e.g. #RRGGBB)")
                    return False
            if path == ("treeview", "row_height"):
                try:
                    if int(self._vars[path].get()) <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Invalid Row Height", "Row height must be a positive integer")
                    return False
            if path == ("network","api_url_base"):
                val = self._vars[path].get()
                if val and not self.URL_REGEX.match(val):
                    messagebox.showerror("Invalid URL", f"{val} is not a valid http/https URL")
                    return False
        return True

    def apply_clicked(self):
        if not self._validate_before_save():
            return
        self._update_config_from_vars()
        
        # Migrate old colors to theme structure if needed
        theme_manager.migrate_old_colors(self.config_data)
        
        save_config(self.config_data)
        # Reload the config in memory so app_config.get() returns updated values
        app_config.reload_config()
        # Reload theme
        theme_manager.reload_theme()
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
        if messagebox.askyesno("Reset Defaults", "Reset all settings to factory defaults?"):
            self.config_data = deepcopy(DEFAULT_CONFIG)
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
            for item in os.listdir(source_path):
                item_path = os.path.join(source_path, item)
                # Skip __pycache__ directories
                if item == "__pycache__":
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
