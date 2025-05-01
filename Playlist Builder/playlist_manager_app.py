import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import os
import sys
import json
import shutil
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
from mutagen.flac import FLACNoHeaderError
from mutagen.mp4 import MP4NoTrackError
from mutagen.oggvorbis import OggVorbisHeaderError
import pygame # For prelistening
import threading # For non-blocking prelisten update
import time
import tkinter.font as tkfont
from metadata_utils import load_audio_metadata, save_audio_metadata
import subprocess
from common_components import (APP_NAME, SETTINGS_FILE, DEFAULT_COLUMNS, AVAILABLE_COLUMNS, 
                             M3U_ENCODING, format_duration, open_file_location, ColumnChooserDialog)
import main # Import main module for PlaylistTab class
import logging
logger = logging.getLogger(__name__)

# Import PlaylistTab at the module level to avoid circular imports
PlaylistTab = main.PlaylistTab

class PlaylistManagerApp(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        if master is not None:
            master.title(APP_NAME)
            master.geometry("1600x900")
        self.current_settings = {
            "columns": DEFAULT_COLUMNS,
            "profiles": {},
            "last_profile": None,
            "audio_device": None, # Placeholder for future device selection
            "open_tabs": []
        }
        self.load_settings()

        # --- Data ---
        self.clipboard = [] # Simple list to hold track data dictionaries for copy/paste

        # --- UI Elements ---
        # Set modern, slightly larger font for the app
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=12, family="Segoe UI")
        self.option_add("*Font", default_font)
        self.option_add("*TCombobox*Listbox.font", default_font)
        self.option_add("*Treeview*Font", default_font)
        # Use a separate font object for headings/tabs
        heading_font = default_font.copy()
        heading_font.configure(weight="bold")
        self.option_add("*Treeview*Heading.Font", heading_font)
        self.option_add("*Menu.Font", default_font)
        # Make the top bar menu font larger
        menu_font = default_font.copy()
        menu_font.configure(size=12, family="Segoe UI")
        self.option_add("*Menu.Font", menu_font)
        self.option_add("*Button.Font", default_font)
        self.option_add("*Label.Font", default_font)
        self.option_add("*Entry.Font", default_font)
        self.option_add("*TEntry.Font", default_font)
        self.option_add("*TNotebook.Tab.Font", heading_font)


        # Modern theme
        style = ttk.Style(self)
        style.theme_use("clam")
        # SMALL font/padding for normal (unselected) tabs
        normal_tab_font = heading_font.copy()
        normal_tab_font.configure(size=9)
        #make the tabs look smaller with less padding
        style.configure("TNotebook.Tab", padding=[5, 2], font=normal_tab_font, background="#e0e0eb", foreground="#222")

        # LARGE font/padding for SELECTED tab (should look like previous unselected tabs)
        selected_tab_font = heading_font.copy()
        selected_tab_font.configure(size=35, weight="bold")


        style.map("TNotebook.Tab",
                  background=[("selected", "#f0f0f7"), ("!selected", "#e0e0eb")],
                  foreground=[("selected", "#222"), ("!selected", "#222")],
                  font=[("selected", selected_tab_font), ("!selected", normal_tab_font)])
        style.configure("TNotebook", background="#f0f0f7")
        style.configure("Treeview", rowheight=28, font=default_font, fieldbackground="#fff", background="#fff", height=22)
        style.configure("Treeview.Heading", font=heading_font, background="#e0e0eb", foreground="#222")
        style.configure("TLabel", font=default_font)
        style.configure("TButton", font=default_font)
        style.configure("TEntry", font=default_font)
        style.map("TButton", background=[("active", "#e0e0eb")])


        # --- Main Area ---
        self.notebook = ttk.Notebook(self)
        self.notebook.enable_traversal()
        self.notebook.bind("<ButtonPress-1>", self._on_tab_press)
        self.notebook.bind("<B1-Motion>", self._on_tab_drag)
        self.notebook.bind("<ButtonRelease-1>", self._on_tab_release)
        self._dragged_tab_index = None
        self._dragged_tab_id = None
        self.notebook.pack(expand=True, fill="both", side="top", padx=5, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.notebook.bind("<Button-3>", self._on_tab_right_click_context)

        # --- Restore Menu Bar (moved after font/theme setup to ensure it appears) ---
        self.main_menu = tk.Menu(self.master)
        self.master.config(menu=self.main_menu)

        # File Menu
        self.file_menu = tk.Menu(self.main_menu, tearoff=0)
        self.main_menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New Playlist Tab", command=self.add_new_tab)
        self.file_menu.add_command(label="Open Playlist(s)...", command=self.open_playlists)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save Current Playlist", command=self.save_current_playlist)
        self.file_menu.add_command(label="Save Current Playlist As...", command=lambda: self.save_current_playlist(save_as=True))
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save Profile...", command=self.save_profile)
        self.load_profile_menu = tk.Menu(self.main_menu, tearoff=0) # Dynamic menu
        self.file_menu.add_cascade(label="Load Profile", menu=self.load_profile_menu)
        self.update_load_profile_menu()
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Close Current Tab", command=self.close_current_tab)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit_app)

        # Edit Menu
        self.edit_menu = tk.Menu(self.main_menu, tearoff=0)
        self.main_menu.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Copy Selected", command=self.copy_selected)
        self.edit_menu.add_command(label="Cut Selected", command=self.cut_selected)
        self.edit_menu.add_command(label="Paste Tracks", command=self.paste_tracks)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Remove Selected", command=self.remove_selected_from_current)
        # Add more later: Select All, Find, etc.

        # View Menu
        self.view_menu = tk.Menu(self.main_menu, tearoff=0)
        self.main_menu.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_command(label="Customize Columns...", command=self.customize_columns)
        self.view_menu.add_command(label="Refresh Current Playlist View", command=self.refresh_current_tab_view)
        self.view_menu.add_separator()
        self.view_menu.add_command(label="Show Filter Bar", command=self.toggle_filter_bar)

        # --- Pre-listen Controls ---
        self.prelisten_frame = ttk.Frame(self)
        self.prelisten_frame.pack_forget() # Hide by default

        self.play_pause_button = ttk.Button(self.prelisten_frame, text="▶ Play", command=self.toggle_play_pause, width=8)
        self.play_pause_button.pack(side="left", padx=(0,5))
        self.stop_button = ttk.Button(self.prelisten_frame, text="■ Stop", command=self.stop_playback, width=8)
        self.stop_button.pack(side="left", padx=(0,5))

        # Song title label
        self.prelisten_label = ttk.Label(self.prelisten_frame, text="No track selected.", anchor="w", width=40)
        self.prelisten_label.pack(side="top", anchor="w", padx=5, pady=(0,2), fill="x")

        # Scrubber/progress bar (styled for a modern look, easier to drag)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_scale = ttk.Scale(self.prelisten_frame, from_=0, to=100, orient="horizontal", variable=self.progress_var, command=self.on_scrub, length=250)
        self.progress_scale.pack(side="top", fill="x", expand=True, padx=(5, 40), pady=(0,2))
        self.progress_scale.bind("<ButtonRelease-1>", self.on_scrub_release)
        self.progress_scale.configure(takefocus=True)

        # Volume slider (no label)
        self.volume_var = tk.DoubleVar(value=1.0)
        self.volume_scale = ttk.Scale(self.prelisten_frame, from_=0, to=1, orient="horizontal", variable=self.volume_var, command=self.on_volume_change, length=80)
        self.volume_scale.pack(side="left", padx=(5, 5), pady=(5,0))

        self.progress_label = ttk.Label(self.prelisten_frame, text="00:00 / 00:00", width=15, anchor='e')
        self.progress_label.pack(side="left", padx=5)

        # X button to hide player (moved to end)
        self.hide_player_button = ttk.Button(self.prelisten_frame, text="✖", width=3, command=self.hide_prelisten_player)
        self.hide_player_button.pack(side="right", padx=(5,5), pady=(0,0))
        self.hide_player_button.pack_forget()  # Hide by default

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side="bottom", fill=tk.X)
        self.set_status("Ready.")

        # --- Playback State ---
        self.currently_playing_path = None
        self.is_paused = False
        self.playback_start_time = 0
        self.paused_position = 0
        self.current_track_duration = 0
        self.playback_update_job = None # To store the after() job ID for progress updates

        # --- Load Last Profile ---
        if self.current_settings.get("last_profile"):
            self.load_profile(self.current_settings["last_profile"], startup=True)
        else:
            # Restore open tabs if present, else start with one empty tab
            self.restore_open_tabs()
            if not self.notebook.tabs():
                self.add_new_tab("Untitled Playlist")

        # --- Protocol Handlers ---
        if master is not None:
            self.master.protocol("WM_DELETE_WINDOW", self.quit_app)

        # --- Pygame Mixer Init ---
        self._auto_init_audio()

        # Initialize persistent column widths
        self._column_widths = self.current_settings.get('column_widths', {})

    # ... (rest of PlaylistManagerApp methods unchanged)

    def set_status(self, message):
        self.status_var.set(message)
        # print(message) # Also print to console for debugging

    def get_current_tab(self) -> 'PlaylistTab | None':
        """Gets the currently selected PlaylistTab instance."""
        try:
            selected_tab_id = self.notebook.select()
            if selected_tab_id:
                widget = self.nametowidget(selected_tab_id)
                # Ensure it's one of our PlaylistTab frames
                if isinstance(widget, PlaylistTab):
                    return widget
        except tk.TclError: # No tabs exist or selected
            pass
        return None

    def on_tab_change(self, event=None):
        """Called when the selected tab changes."""
        # Stop playback when switching tabs
        if self.currently_playing_path:
             self.stop_playback()

        current_tab = self.get_current_tab()
        if current_tab:
            self.set_status(f"Active Playlist: {current_tab.get_display_name()}")
            # Update prelisten label if a track is selected in the new tab
            selected_iid = current_tab.get_selected_item_id()
            if selected_iid:
                track_data = current_tab.get_track_data_by_iid(selected_iid)
                if track_data:
                    self.update_prelisten_info(track_data)
                else:
                    self.reset_prelisten_ui()
            else:
                 self.reset_prelisten_ui()
                 self.set_status("No playlist selected.")
        else:
             self.reset_prelisten_ui()
             self.set_status("No playlist selected.")

    # --- Playlist Management ---

    def add_new_tab(self, title="Untitled Playlist", filepath=None):
        """Adds a new empty playlist tab."""
        tab = PlaylistTab(self.notebook, self, filepath=filepath, initial_columns=self.current_settings['columns'])
        self.notebook.add(tab, text=title)
        self.notebook.select(tab) # Make the new tab active
        tab.update_tab_title() # Set initial '*' if needed
        self.set_status(f"Created new playlist: {title}")
        # After tab is created, apply column widths
        if hasattr(self, 'get_column_widths'):
            widths = self.get_column_widths()
            for col, width in widths.items():
                try:
                    tab.tree.column(col, width=width)
                except Exception:
                    pass
        return tab

    def open_playlists(self):
        """Opens one or more M3U/M3U8 files in new tabs."""
        filepaths = filedialog.askopenfilenames(
            title="Open Playlist(s)",
            filetypes=[("M3U Playlists", "*.m3u *.m3u8"), ("All Files", "*.*")]
        )
        if not filepaths:
            return

        loaded_count = 0
        for path in filepaths:
            try:
                # Check if already open
                is_open = False
                for tab in self.notebook.tabs():
                    widget = self.nametowidget(tab)
                    if isinstance(widget, PlaylistTab) and widget.filepath == path:
                        self.notebook.select(widget) # Switch to existing tab
                        self.set_status(f"Playlist '{os.path.basename(path)}' is already open.")
                        is_open = True
                        break
                if is_open:
                    continue
                # If current tab is empty, load into it
                current_tab = self.get_current_tab()
                if current_tab and not current_tab._track_data:
                    success = current_tab.load_playlist_from_file(path)
                    if success:
                        current_tab.filepath = path
                        current_tab.tab_display_name = os.path.basename(path)
                        current_tab.update_tab_title()
                        loaded_count += 1
                    else:
                        messagebox.showerror("Load Error", f"Failed to load playlist:\n{path}\nSee console for details.")
                        current_tab.is_dirty = False
                        current_tab.update_tab_title()
                    continue
                # Add new tab and load
                tab_title = os.path.basename(path)
                new_tab = self.add_new_tab(title=tab_title, filepath=path)
                success = new_tab.load_playlist_from_file(path)
                if success:
                    loaded_count += 1
                else:
                    messagebox.showerror("Load Error", f"Failed to load playlist:\n{path}\nSee console for details.")
                    new_tab.is_dirty = False
                    new_tab.update_tab_title()
            except Exception as e:
                messagebox.showerror("Error Opening Playlist", f"Could not open {os.path.basename(path)}:\n{e}")
                self.set_status(f"Error opening {os.path.basename(path)}")
        self.set_status(f"Opened {loaded_count} playlist(s).")

    def save_current_playlist(self, save_as=False):
        """Saves the playlist in the currently active tab."""
        current_tab = self.get_current_tab()
        if not current_tab:
            messagebox.showwarning("No Playlist", "No playlist tab is currently active.")
            return

        current_tab.save_playlist(force_save_as=save_as)

    def close_current_tab(self):
        """Closes the currently active tab, prompting to save if dirty."""
        current_tab = self.get_current_tab()
        if not current_tab:
            return

        if current_tab.is_dirty:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"Playlist '{current_tab.get_display_name()}' has unsaved changes.\nDo you want to save before closing?"
            )
            if response is None: # Cancel
                return False # Indicate closing was cancelled
            elif response is True: # Yes (Save)
                saved = current_tab.save_playlist()
                if not saved: # Saving was cancelled or failed
                    return False # Indicate closing was cancelled

        # If response was False (No) or save was successful, proceed to close
        tab_id = self.notebook.select()
        self.notebook.forget(tab_id)
        self.set_status(f"Closed tab: {current_tab.get_display_name()}")
        # If this was the last tab, the notebook might trigger on_tab_change, handle gracefully
        if not self.notebook.tabs():
             self.reset_prelisten_ui()
             self.set_status("Ready.")
        return True # Indicate successful close

    # --- Track Operations (delegated to current tab) ---

    def copy_selected(self):
        current_tab = self.get_current_tab()
        if current_tab:
            self.clipboard = current_tab.get_selected_track_data()
            if self.clipboard:
                self.set_status(f"Copied {len(self.clipboard)} track(s) to clipboard.")
            else:
                self.set_status("Select tracks to copy first.")

    def cut_selected(self):
        """Copy selected tracks to clipboard and remove them from the playlist."""
        current_tab = self.get_current_tab()
        if not current_tab:
            return
        selected_tracks = current_tab.get_selected_track_data()
        if not selected_tracks:
            return
        self.clipboard = [track.copy() for track in selected_tracks]
        current_tab.remove_selected_tracks()

    def paste_tracks(self):
        current_tab = self.get_current_tab()
        if not current_tab:
            messagebox.showwarning("Paste Error", "No active playlist tab to paste into.")
            return
        if not self.clipboard:
            messagebox.showwarning("Paste Error", "Clipboard is empty.")
            return

        current_tab.add_tracks(self.clipboard) # Add tracks takes list of dicts
        self.set_status(f"Pasted {len(self.clipboard)} track(s) into {current_tab.get_display_name()}.")

    def remove_selected_from_current(self):
        current_tab = self.get_current_tab()
        if current_tab:
            current_tab.remove_selected_tracks()

    def refresh_current_tab_view(self):
         current_tab = self.get_current_tab()
         if current_tab:
             current_tab.refresh_display()
             self.set_status(f"Refreshed view for {current_tab.get_display_name()}")

    # --- Column Customization ---

    def customize_columns(self):
        """Opens a dialog to choose visible columns."""
        dialog = ColumnChooserDialog(self, AVAILABLE_COLUMNS, self.current_settings['columns'])
        if dialog.result:
            self.current_settings['columns'] = dialog.result
            self.apply_column_settings_to_all_tabs()
            self.save_settings() # Persist column changes
            self.set_status("Column view updated.")

    def apply_column_settings_to_all_tabs(self):
        """Applies the current column settings to all open tabs."""
        for tab_id in self.notebook.tabs():
            widget = self.nametowidget(tab_id)
            if isinstance(widget, PlaylistTab):
                widget.update_columns(self.current_settings['columns'])

    def update_column_settings_for_all_tabs(self):
        """Applies the current column settings to all open PlaylistTab instances."""
        new_columns = self.current_settings.get('columns', DEFAULT_COLUMNS)
        logger.info(f"Applying column settings to all tabs: {new_columns}")
        if not hasattr(self, 'notebook'):
            logger.error("Notebook widget not found, cannot update tab columns.")
            return

        tabs = self.notebook.tabs()
        if not tabs:
            logger.info("No tabs open, skipping column update.")
            return

        for tab_id in tabs:
            try:
                widget = self.nametowidget(tab_id)
                # Check if the main module and PlaylistTab class exist before isinstance check
                if main and hasattr(main, 'PlaylistTab') and isinstance(widget, main.PlaylistTab):
                     logger.debug(f"Updating columns for tab: {widget.get_display_name()}")
                     widget.update_displayed_columns(new_columns)
                else:
                     logger.warning(f"Widget for tab ID {tab_id} is not a PlaylistTab instance (type: {type(widget).__name__}). Skipping column update.")
            except tk.TclError as e:
                logger.warning(f"TclError accessing widget for tab ID {tab_id}: {e} - Tab might have been destroyed.")
            except Exception as e:
                logger.error(f"Error updating columns for tab ID {tab_id}: {e}", exc_info=True)

    # --- Profile Management ---

    def save_profile(self):
        """Saves the current state (open tabs, columns) as a named profile, or to the currently opened profile."""
        profiles = list(self.current_settings.get("profiles", {}).keys())
        last_profile = self.current_settings.get("last_profile")
        options = []
        if last_profile:
            options.append(f"Overwrite current profile: {last_profile}")
        options.append("Save to new profile")
        # Ask user what they want to do
        dialog = tk.Toplevel(self)
        dialog.title("Save Profile")
        dialog.transient(self)
        dialog.grab_set()
        # Center the dialog on the display
        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        ws = dialog.winfo_screenwidth()
        hs = dialog.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        dialog.geometry(f"+{x}+{y}")
        tk.Label(dialog, text="Choose save option:").pack(padx=10, pady=10)
        var = tk.StringVar(value=options[0])
        for opt in options:
            tk.Radiobutton(dialog, text=opt, variable=var, value=opt).pack(anchor="w", padx=15)
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        result = {'option': None}
        def on_ok():
            result['option'] = var.get()
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        tk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        dialog.wait_window()
        choice = result['option']
        if choice is None:
            self.set_status("Profile save cancelled.")
            return

        if choice.startswith("Overwrite current profile") and last_profile:
            profile_name = last_profile
        else:
            # Ask for new profile name
            profile_name = simpledialog.askstring("Save Profile", "Enter a name for this profile:", parent=self)
            if not profile_name:
                print("[PROFILE] Save cancelled: No name provided.")
                return

        tabs_info = []
        for tab_id in self.notebook.tabs():
            widget = self.nametowidget(tab_id)
            if isinstance(widget, PlaylistTab) and widget.filepath:
                tabs_info.append({
                    "filepath": widget.filepath,
                    "display_name": widget.tab_display_name
                })

        profile_data = {
            "tabs_info": tabs_info,
            "columns": self.current_settings['columns']
        }

        if "profiles" not in self.current_settings:
            self.current_settings["profiles"] = {}
        self.current_settings["profiles"][profile_name] = profile_data
        self.current_settings["last_profile"] = profile_name
        self.save_settings()
        self.update_load_profile_menu()
        print(f"[PROFILE] Profile '{profile_name}' saved to settings.")
        self.set_status(f"Profile '{profile_name}' saved.")

    def delete_profile(self):
        profiles = list(self.current_settings.get("profiles", {}).keys())
        if not profiles:
             messagebox.showinfo("Delete Profile", "There are no profiles to delete.")
             return

        # Only allow selection from the list, no entry field for typing
        dialog = tk.Toplevel(self)
        dialog.title("Delete Profile")
        dialog.transient(self)
        dialog.grab_set()
        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        ws = dialog.winfo_screenwidth()
        hs = dialog.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        dialog.geometry(f"+{x}+{y}")
        tk.Label(dialog, text="Select a profile to delete:").pack(padx=10, pady=10)
        var = tk.StringVar(value=profiles[0] if profiles else "")
        listbox = tk.Listbox(dialog, listvariable=tk.StringVar(value=profiles), height=min(10, len(profiles)), exportselection=False)
        listbox.pack(padx=10, pady=5)
        listbox.selection_set(0)
        def on_select(event=None):
            sel = listbox.curselection()
            if sel:
                var.set(profiles[sel[0]])
        listbox.bind('<<ListboxSelect>>', on_select)
        result = {'profile': None}
        def on_ok():
            result['profile'] = var.get()
            dialog.destroy()
        def on_cancel():
            dialog.destroy()
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        dialog.wait_window()
        choice = result['profile']
        if choice and choice in self.current_settings["profiles"]:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the profile '{choice}'?", parent=self):
                del self.current_settings["profiles"][choice]
                if self.current_settings.get("last_profile") == choice:
                    self.current_settings["last_profile"] = None 
                self.save_settings()
                self.update_load_profile_menu()
                self.set_status(f"Profile '{choice}' deleted.")
        elif choice:
             messagebox.showerror("Delete Error", f"Profile '{choice}' not found.", parent=self)

    def _choose_profile_dialog(self, profiles, title, prompt):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        # Center the dialog on the display
        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        ws = dialog.winfo_screenwidth()
        hs = dialog.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        dialog.geometry(f"+{x}+{y}")
        tk.Label(dialog, text=prompt).pack(padx=10, pady=10)
        var = tk.StringVar(value=profiles[0] if profiles else "")
        listbox = tk.Listbox(dialog, listvariable=tk.StringVar(value=profiles), height=min(10, len(profiles)), exportselection=False)
        listbox.pack(padx=10, pady=5)
        listbox.selection_set(0)
        entry = tk.Entry(dialog, textvariable=var)
        entry.pack(padx=10, pady=5)
        entry.insert(0, profiles[0] if profiles else "")
        entry.focus_set()

        def on_select(event=None):
            sel = listbox.curselection()
            if sel:
                var.set(profiles[sel[0]])
                entry.delete(0, tk.END)
                entry.insert(0, profiles[sel[0]])

        listbox.bind('<<ListboxSelect>>', on_select)

        result = {'profile': None}

        def on_ok():
            result['profile'] = var.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        dialog.wait_window()
        return result['profile']

    def update_load_profile_menu(self):
        """Updates the dynamic 'Load Profile' menu."""
        self.load_profile_menu.delete(0, tk.END) 
        profiles = self.current_settings.get("profiles", {})
        if not profiles:
            self.load_profile_menu.add_command(label="(No profiles saved)", state="disabled")
        else:
            for name in sorted(profiles.keys()):
                self.load_profile_menu.add_command(label=name, command=lambda n=name: self.load_profile(n))
            self.load_profile_menu.add_separator()
            self.load_profile_menu.add_command(label="Delete Profile...", command=self.delete_profile)


    def load_profile(self, profile_name, startup=False):
        logger.info(f'Attempting to load profile: {profile_name} (startup={startup})') 
        try:
            if profile_name not in self.current_settings.get("profiles", {}): 
                logger.error(f"Profile '{profile_name}' not found in settings.")
                messagebox.showerror("Load Error", f"Profile '{profile_name}' not found.")
                if startup:
                    logger.warning("Profile not found during startup, clearing last_profile and restoring default/empty state.")
                    self.current_settings["last_profile"] = None
                    self.save_settings()
                    self.restore_open_tabs() 
                return

            logger.info(f"Found profile '{profile_name}'. Proceeding with load.")
            profile_data = self.current_settings["profiles"][profile_name]
            tabs_info = profile_data.get('tabs_info', []) 
            columns = profile_data.get('columns', self.current_settings.get('columns', DEFAULT_COLUMNS)) 

            logger.debug(f"Setting columns for profile '{profile_name}': {columns}")
            self.current_settings['columns'] = columns

            logger.info("Closing existing tabs before loading profile tabs.")
            open_tab_ids = list(self.notebook.tabs()) 
            for tab_id in open_tab_ids:
                try:
                    logger.debug(f"Closing tab with ID: {tab_id}")
                    self.notebook.forget(tab_id)
                except tk.TclError as e:
                    logger.warning(f"TclError closing tab {tab_id}: {e} - might already be closed.")
                except Exception as e:
                    logger.error(f"Unexpected error closing tab {tab_id}: {e}", exc_info=True)

            logger.info(f"Loading {len(tabs_info)} tabs specified in profile '{profile_name}'.")
            if not tabs_info:
                logger.warning(f"Profile '{profile_name}' has no tabs specified. Adding a default Untitled tab.")
                self.add_new_tab(title="Untitled Playlist") 
            else:
                for i, tab_info in enumerate(tabs_info):
                    filepath = tab_info.get('filepath')
                    display_name = tab_info.get('display_name', os.path.basename(filepath) if filepath else "Untitled Playlist")
                    logger.info(f"Processing tab {i+1}/{len(tabs_info)}: filepath='{filepath}', display_name='{display_name}'")

                    if filepath:
                        if os.path.exists(filepath):
                            logger.debug(f"Adding tab for existing file: {filepath}")
                            tab = self.add_new_tab(title=display_name, filepath=filepath)
                            if tab and display_name != os.path.basename(filepath):
                                logger.debug(f"Setting custom display name: '{display_name}'")
                                tab.tab_display_name = display_name
                                tab.update_tab_title()
                                
                            if tab and hasattr(tab, 'load_playlist_from_file'):
                                logger.info(f"Calling load_playlist_from_file for: {filepath}")
                                try:
                                    success = tab.load_playlist_from_file(filepath)
                                    logger.info(f"load_playlist_from_file result for '{filepath}': {success}")
                                    if not success:
                                        logger.error(f"Failed to load playlist content for: {filepath}")
                                        messagebox.showwarning("Load Warning", f"Could not fully load playlist:\n{filepath}\n\nIt might be corrupted or inaccessible.", parent=self)
                                except Exception as e:
                                    logger.error(f"Exception during load_playlist_from_file for {filepath}: {e}", exc_info=True)
                                    messagebox.showerror("Load Error", f"An error occurred loading playlist:\n{filepath}\n\nError: {e}", parent=self)
                        else:
                            logger.warning(f"File path from profile does not exist, skipping tab: {filepath}")
                            messagebox.showwarning("Load Warning", f"Playlist file not found:\n{filepath}\n\nThis tab was not loaded.", parent=self)
                    else:
                        logger.info("Adding an Untitled tab as specified in profile.")
                        self.add_new_tab(title=display_name or "Untitled Playlist") 

            if not self.notebook.tabs():
                logger.warning("No tabs were loaded or remained after profile load. Adding a default Untitled tab.")
                self.add_new_tab(title="Untitled Playlist")

            self.current_settings["last_profile"] = profile_name
            self.save_settings() 
            self.update_load_profile_menu() 
            self.update_column_settings_for_all_tabs() 
            self.set_status(f"Profile '{profile_name}' loaded.")
            logger.info(f"Profile '{profile_name}' loading complete.")
            if self.notebook.tabs():
                self.notebook.select(self.notebook.tabs()[0])
                self.on_tab_change() 

        except Exception as e:
            logger.error(f"CRITICAL ERROR loading profile '{profile_name}': {e}", exc_info=True)
            messagebox.showerror("Profile Load Error", f"A critical error occurred while loading profile '{profile_name}'.\nSee app.log for details.\n\nError: {e}", parent=self)
            logger.warning("Attempting to revert to empty state after profile load error.")
            self.current_settings["last_profile"] = None 
            self.restore_open_tabs() 

    # --- Settings Persistence ---

    def save_settings(self):
        """Saves current settings to SETTINGS_FILE, including open tabs."""
        open_tabs = []
        for tab_id in self.notebook.tabs():
            widget = self.nametowidget(tab_id)
            if hasattr(widget, 'filepath') and widget.filepath:
                open_tabs.append(widget.filepath)
            else:
                open_tabs.append(None)
        self.current_settings['open_tabs'] = open_tabs
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, indent=2)
            print(f"[SETTINGS] Saved to {SETTINGS_FILE}")
        except Exception as e:
            print(f"[ERROR] Saving settings: {e}")

    def load_settings(self):
        """Loads settings from SETTINGS_FILE, including open tabs."""
        if not os.path.exists(SETTINGS_FILE):
            self.current_settings = {
                "columns": DEFAULT_COLUMNS,
                "profiles": {},
                "last_profile": None,
                "audio_device": None
            }
            return
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                self.current_settings = json.load(f)
        except Exception as e:
            print(f"[ERROR] Loading settings: {e}")
            self.current_settings = {
                "columns": DEFAULT_COLUMNS,
                "profiles": {},
                "last_profile": None,
                "audio_device": None
            }

    def restore_open_tabs(self):
        """Restores open tabs from settings on startup and loads playlists."""
        open_tabs = self.current_settings.get('open_tabs', [])
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        if open_tabs:
            for filepath in open_tabs:
                if filepath:
                    tab = self.add_new_tab(title=os.path.basename(filepath), filepath=filepath)
                    if hasattr(tab, 'load_playlist_from_file'):
                        try:
                            tab.load_playlist_from_file(filepath)
                        except Exception as e:
                            print(f"[ERROR] Failed to load playlist from {filepath}: {e}")
                else:
                    self.add_new_tab("Untitled Playlist")

    # --- Pre-listening ---

    def toggle_play_pause(self):
        if not self.pygame_initialized:
            messagebox.showwarning("Audio Error", "Audio system not initialized. Cannot play.")
            return

        if self.currently_playing_path:
            if self.is_paused:
                try:
                    pygame.mixer.music.unpause()
                    self.is_paused = False
                    self.play_pause_button.config(text="❚❚ Pause")
                    self.set_status(f"Resumed: {os.path.basename(self.currently_playing_path)}")
                    self.playback_start_time = time.time() - self.paused_position
                    self._update_playback_progress()
                except Exception as e:
                    messagebox.showerror("Playback Error", f"Could not resume playback: {e}")
                    self.stop_playback() 
            else:
                try:
                    pygame.mixer.music.pause()
                    self.is_paused = True
                    self.play_pause_button.config(text="▶ Play")
                    self.set_status(f"Paused: {os.path.basename(self.currently_playing_path)}")
                    self.paused_position = time.time() - self.playback_start_time
                    if self.playback_update_job:
                        self.after_cancel(self.playback_update_job)
                        self.playback_update_job = None
                except Exception as e:
                    messagebox.showerror("Playback Error", f"Could not pause playback: {e}")
                    self.stop_playback() 
        else:
            current_tab = self.get_current_tab()
            if not current_tab:
                return

            iid = current_tab.get_selected_item_id()
            if not iid:
                messagebox.showinfo("Play Track", "Select a track in the list to play.")
                return

            track_data = current_tab.get_track_data_by_iid(iid)
            if not track_data or not track_data.get('exists'):
                messagebox.showwarning("Play Error", "Cannot play track: File does not exist or data missing.")
                return

            if not track_data['exists']:
                messagebox.showwarning("Play Error", "Cannot play track: File does not exist.")
                return

            self.start_playback(track_data)

    def start_playback(self, track_data):
        if pygame.mixer.get_init() is None:
            print("[WARN] Mixer not actually initialized at playback time. Attempting re-init.")
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            print("[INFO] Mixer re-initialized at playback time.")
            self.pygame_initialized = True
        print(f"[DEBUG] start_playback called for {track_data.get('path')}. Initialized: {self.pygame_initialized}")
        if not self.pygame_initialized:
            print("[ERROR] start_playback attempted but mixer not initialized.")
            self.set_status("Audio Error: Mixer not initialized. Cannot play.")
            return
        if not track_data or not track_data.get('path') or not track_data.get('exists'):
            self.set_status("Error: Cannot play missing or invalid file.")
            return
        if not track_data['exists']:
            self.set_status("Error: File does not exist.")
            return
        path = track_data['path']

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

            self.currently_playing_path = path
            self.is_paused = False
            self.paused_position = 0
            self.current_track_duration = track_data.get('duration') or 0 
            self.play_pause_button.config(text="❚❚ Pause")
            self.update_prelisten_info(track_data)
            self.show_prelisten_player()
            self.set_status(f"Playing: {os.path.basename(path)}")

            self.playback_start_time = time.time()
            self._update_playback_progress()

        except Exception as e:
            print(f"[ERROR] Exception during playback: {e}")
            self.set_status(f"Audio Error: {e}")
            return

    def stop_playback(self):
        if self.playback_update_job:
            self.after_cancel(self.playback_update_job)
            self.playback_update_job = None

        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload() 
            except AttributeError:
                pass
        except pygame.error as e:
            print(f"Pygame error during stop/unload: {e}")


        was_playing = self.currently_playing_path is not None
        self.currently_playing_path = None
        self.is_paused = False
        self.paused_position = 0
        self.play_pause_button.config(text="▶ Play")
        if was_playing:
            self.set_status("Playback stopped.")
            self.progress_label.config(text=f"00:00 / {format_duration(self.current_track_duration)}")
            self.hide_prelisten_player()

    def _update_playback_progress(self):
        if self.currently_playing_path and not self.is_paused and pygame.mixer.music.get_busy():
            elapsed_time = time.time() - self.playback_start_time

            if self.current_track_duration > 0:
                elapsed_time = min(elapsed_time, self.current_track_duration)
                self.progress_var.set(int((elapsed_time / self.current_track_duration) * 100))
                self.progress_label.config(text=f"{format_duration(elapsed_time)} / {format_duration(self.current_track_duration)}")
            else:
                self.progress_var.set(0)
                self.progress_label.config(text="00:00 / 00:00")

            self.playback_update_job = self.after(250, self._update_playback_progress) 
        elif self.currently_playing_path and not self.is_paused:
             self.stop_playback() 


    def update_prelisten_info(self, track_data):
         if track_data:
             title = track_data.get('title', 'Unknown Title')
             artist = track_data.get('artist', 'Unknown Artist')
             duration_str = format_duration(track_data.get('duration'))
             self.prelisten_label.config(text=f"{artist} - {title}")
             if track_data.get('path') != self.currently_playing_path:
                 self.progress_label.config(text=f"00:00 / {duration_str}")
                 self.current_track_duration = track_data.get('duration', 0) 
         else:
             self.reset_prelisten_ui()

    def reset_prelisten_ui(self):
        self.prelisten_label.config(text="No track selected.")
        self.progress_label.config(text="00:00 / 00:00")
        self.play_pause_button.config(text="▶ Play")
        self.hide_prelisten_player()

    def apply_speed_change_on_next_play(self, event=None):
        pass

    # --- Application Exit ---

    def quit_app(self):
        tabs_to_save = []
        for tab_id in self.notebook.tabs():
            widget = self.nametowidget(tab_id)
            if isinstance(widget, PlaylistTab) and widget.is_dirty:
                tabs_to_save.append(widget.get_display_name())

        if tabs_to_save:
            save_all = messagebox.askyesnocancel(
                "Unsaved Playlists",
                "There are unsaved playlists:\n- " + "\n- ".join(tabs_to_save) +
                "\n\nDo you want to save all changes before exiting?"
            )
            if save_all is None: 
                return
            elif save_all is True: 
                all_saved = True
                for tab_id in self.notebook.tabs():
                     self.notebook.select(tab_id) 
                     tab_widget = self.nametowidget(tab_id)
                     if not self.close_current_tab():
                          all_saved = False
                          messagebox.showwarning("Save Failed", f"Could not save '{tab_widget.get_display_name()}'. Exiting anyway?", parent=self)
        if hasattr(self, 'pygame_initialized') and getattr(self, 'pygame_initialized', False):
            self.stop_playback()
            pygame.mixer.quit()
            print("Pygame mixer quit.")

        self.save_settings()

        self.master.destroy()

    def toggle_filter_bar(self):
        tab = self.get_current_tab()
        if tab:
            tab.show_filter_bar()

    def _update_tab_styles(self, event=None):
        pass

    def _on_tab_right_click_context(self, event):
        x, y = event.x, event.y
        elem = self.notebook.identify(x, y)
        if elem == 'label':
            tab_index = self.notebook.index(f"@{x},{y}")
            tab_widget_id = self.notebook.tabs()[tab_index]
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Rename Tab", command=lambda: self.rename_notebook_tab(tab_index))
            menu.add_command(label="Delete Tab", command=lambda: self._delete_tab(tab_widget_id))
            menu.tk_popup(event.x_root, event.y_root)

    def _delete_tab(self, tab_widget_id):
        self.notebook.forget(tab_widget_id)

    def on_tab_right_click(self, event):
        x, y = event.x, event.y
        elem = self.notebook.identify(event.x, event.y)
        if elem == 'label':
            tab_id = self.notebook.index(f"@{x},{y}")
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Rename Tab", command=lambda: self.rename_notebook_tab(tab_id))
            menu.tk_popup(event.x_root, event.y_root)

    def rename_notebook_tab(self, tab_id):
        current_title = self.notebook.tab(tab_id, "text")
        new_title = simpledialog.askstring("Rename Tab", "Enter new tab name:", initialvalue=current_title, parent=self)
        if new_title and new_title.strip():
            self.notebook.tab(tab_id, text=new_title.strip())
            widget = self.nametowidget(self.notebook.tabs()[tab_id])
            if hasattr(widget, 'tab_display_name'):
                widget.tab_display_name = new_title.strip()

    def _on_tab_press(self, event):
        x, y = event.x, event.y
        elem = self.notebook.identify(x, y)
        if elem == 'label':
            self._dragged_tab_index = self.notebook.index(f"@{x},{y}")
            self._dragged_tab_id = self.notebook.tabs()[self._dragged_tab_index]
        else:
            self._dragged_tab_index = None
            self._dragged_tab_id = None

    def _on_tab_drag(self, event):
        if self._dragged_tab_index is None:
            return
        x, y = event.x, event.y
        target_index = self.notebook.index(f"@{x},{y}")
        if target_index != self._dragged_tab_index and 0 <= target_index < len(self.notebook.tabs()):
            self.notebook.insert(target_index, self._dragged_tab_id)
            self._dragged_tab_index = target_index

    def _on_tab_release(self, event):
        self._dragged_tab_index = None
        self._dragged_tab_id = None

    def _auto_init_audio(self):
        self.pygame_initialized = False
        max_attempts = 5
        delay_ms = 500 

        def attempt_init(attempt_num):
            if attempt_num > max_attempts:
                print("[ERROR] Audio could not be initialized after retries. Pre-listening disabled.")
                self.set_status("Audio not available: Mixer not initialized after retries.")
                return
            try:
                pygame.mixer.quit()
            except Exception:
                pass 
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self.pygame_initialized = True
                print("[DEBUG] self.pygame_initialized set to True")
                self.set_status("Audio initialized. Pre-listening enabled.")
                print(f"[INFO] Pygame mixer initialized (attempt {attempt_num}).")
            except Exception as e:
                self.pygame_initialized = False
                print(f"[WARN] Audio init attempt {attempt_num} failed: {e}")
                self.set_status(f"Audio not available (attempt {attempt_num}): {e}")
                self.after(delay_ms, lambda: attempt_init(attempt_num + 1))

        attempt_init(1)

    def hide_prelisten_player(self):
        self.stop_playback()  # Also stop playback
        self.prelisten_frame.pack_forget()
        self.currently_playing_path = None

    def show_prelisten_player(self):
        self.prelisten_frame.pack(fill="x", side="bottom", padx=5, pady=(0, 5))
        self.hide_player_button.pack(side="right", padx=(5,5))

    def on_scrub(self, value):
        # Update label while dragging
        if self.current_track_duration > 0:
            elapsed = float(value) * self.current_track_duration / 100
            self.progress_label.config(text=f"{format_duration(elapsed)} / {format_duration(self.current_track_duration)}")
        # Make scrubber easier to drag: set focus
        self.progress_scale.focus_set()
        # Only cancel update job if not already scrubbing
        if self.currently_playing_path and not self.is_paused and not getattr(self, '_scrubbing', False):
            if hasattr(self, 'playback_update_job') and self.playback_update_job:
                self.after_cancel(self.playback_update_job)
            self._scrubbing = True

    def on_scrub_release(self, event):
        # Seek to new position when user releases scrubber
        if self.current_track_duration > 0:
            percent = self.progress_var.get() / 100
            seek_time = percent * self.current_track_duration
            try:
                pygame.mixer.music.play(start=seek_time)
                pygame.mixer.music.set_volume(self.volume_var.get())
                self.playback_start_time = time.time() - seek_time
                self._scrubbing = False
                self._update_playback_progress()
            except Exception as e:
                print(f"[ERROR] Scrubbing failed: {e}")

    def on_volume_change(self, value):
        try:
            pygame.mixer.music.set_volume(float(value))
        except Exception as e:
            print(f"[ERROR] Volume change failed: {e}")

    def on_column_widths_changed(self, new_widths):
        """Callback from PlaylistTab when column widths change. Persist and update all tabs uniformly."""
        self._column_widths = new_widths.copy()
        self.current_settings['column_widths'] = new_widths.copy()
        self.save_settings()
        for tab_id in self.notebook.tabs():
            widget = self.nametowidget(tab_id)
            if hasattr(widget, 'tree'):
                for col, width in new_widths.items():
                    try:
                        widget.tree.column(col, width=width)
                    except Exception:
                        pass

    def get_column_widths(self):
        return getattr(self, '_column_widths', {})
