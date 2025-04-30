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

# Import PlaylistTab at the module level to avoid circular imports
PlaylistTab = main.PlaylistTab

class PlaylistManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1000x700")
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
        self.main_menu = tk.Menu(self)
        self.config(menu=self.main_menu)

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

        # --- Main Area ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", side="top", padx=5, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.notebook.bind("<Button-3>", self.on_tab_right_click)

        # --- Pre-listen Controls ---
        self.prelisten_frame = ttk.Frame(self)
        self.prelisten_frame.pack(fill="x", side="bottom", padx=5, pady=(0, 5))

        self.play_pause_button = ttk.Button(self.prelisten_frame, text="▶ Play", command=self.toggle_play_pause, width=8)
        self.play_pause_button.pack(side="left", padx=(0,5))
        self.stop_button = ttk.Button(self.prelisten_frame, text="■ Stop", command=self.stop_playback, width=8)
        self.stop_button.pack(side="left", padx=(0,5))

        self.prelisten_label = ttk.Label(self.prelisten_frame, text="No track selected.", anchor="w", width=60)
        self.prelisten_label.pack(side="left", padx=5, fill="x", expand=True)

        # Speed control (simple placeholder - real speed control is complex)
        self.speed_label = ttk.Label(self.prelisten_frame, text="Speed:")
        self.speed_label.pack(side="left", padx=(10, 2))
        self.speed_var = tk.StringVar(value="1.0x")
        self.speed_combobox = ttk.Combobox(self.prelisten_frame, textvariable=self.speed_var,
                                           values=["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"],
                                           width=5, state="readonly") # Readonly for now, as changing speed mid-play isn't implemented simply with pygame.mixer.music
        self.speed_combobox.pack(side="left", padx=(0,5))
        self.speed_combobox.bind("<<ComboboxSelected>>", self.apply_speed_change_on_next_play) # Just note the change

        self.progress_label = ttk.Label(self.prelisten_frame, text="00:00 / 00:00", width=15, anchor='e')
        self.progress_label.pack(side="right", padx=5)

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
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        # --- Pygame Mixer Init ---
        self._auto_init_audio()

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

    # --- Profile Management ---

    def save_profile(self):
        """Saves the current state (open tabs, columns) as a named profile."""
        profile_name = simpledialog.askstring("Save Profile", "Enter a name for this profile:", parent=self)
        if not profile_name:
            return

        open_tabs_paths = []
        for tab_id in self.notebook.tabs():
            widget = self.nametowidget(tab_id)
            if isinstance(widget, PlaylistTab) and widget.filepath:
                open_tabs_paths.append(widget.filepath)
            else:
                self.set_status(f"Warning: Untitled playlist '{widget.get_display_name()}' was not saved in the profile.")

        profile_data = {
            "tabs": open_tabs_paths,
            "columns": self.current_settings['columns']
            # Add other settings here if needed, e.g., window size/pos
        }

        self.current_settings["profiles"][profile_name] = profile_data
        self.current_settings["last_profile"] = profile_name # Set as last loaded
        self.save_settings()
        self.update_load_profile_menu()
        self.set_status(f"Profile '{profile_name}' saved.")

    def load_profile(self, profile_name, startup=False):
        """Loads a saved profile, closing current tabs and opening saved ones."""
        if profile_name not in self.current_settings["profiles"]:
            messagebox.showerror("Load Error", f"Profile '{profile_name}' not found.")
            if startup: # If failed on startup, clear last profile setting and restore open tabs
                self.current_settings["last_profile"] = None
                self.save_settings()
                self.restore_open_tabs()
                if not self.notebook.tabs():
                    self.add_new_tab("Untitled Playlist")
                return
            return
        profile_data = self.current_settings["profiles"][profile_name]

        # 1. Close all existing tabs (prompting for save)
        all_tabs_closed = True
        # Iterate backwards because closing modifies the list of tabs
        for tab_id in reversed(self.notebook.tabs()):
             self.notebook.select(tab_id) # Select tab to make close_current_tab work
             tab_widget = self.nametowidget(tab_id)
             if not self.close_current_tab():
                  all_tabs_closed = False
                  # Don't break, let user decide for others, but report failure
                  messagebox.showwarning("Save Failed", f"Could not save '{tab_widget.get_display_name()}'. Exiting anyway?", parent=self)
                  # Or could force exit cancellation:
                  # self.set_status("Exit cancelled due to save failure.")
                  # return
        # If save_all is False (No), proceed to exit without saving

        # 2. Stop audio gracefully
        if hasattr(self, 'pygame_initialized') and getattr(self, 'pygame_initialized', False):
            self.stop_playback()
            pygame.mixer.quit()
            print("Pygame mixer quit.")

        # 3. Save settings (like last loaded profile)
        self.save_settings()

        # 4. Destroy window
        if not startup:
            self.destroy()
        # If called during __init__, prevent further initialization
        if startup:
            raise SystemExit

    def update_load_profile_menu(self):
        """Updates the dynamic 'Load Profile' menu."""
        self.load_profile_menu.delete(0, tk.END) # Clear existing items
        profiles = self.current_settings.get("profiles", {})
        if not profiles:
            self.load_profile_menu.add_command(label="(No profiles saved)", state="disabled")
        else:
            # Sort profile names alphabetically for consistency
            for name in sorted(profiles.keys()):
                # Use lambda with default argument to capture the current name
                self.load_profile_menu.add_command(label=name, command=lambda n=name: self.load_profile(n))
            self.load_profile_menu.add_separator()
            self.load_profile_menu.add_command(label="Delete Profile...", command=self.delete_profile)


    def delete_profile(self):
        profiles = list(self.current_settings.get("profiles", {}).keys())
        if not profiles:
             messagebox.showinfo("Delete Profile", "There are no profiles to delete.")
             return

        # Simple dialog to choose profile to delete (could be improved with a listbox)
        choice = simpledialog.askstring("Delete Profile", "Enter the exact name of the profile to delete:", parent=self)

        if choice and choice in self.current_settings["profiles"]:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the profile '{choice}'?", parent=self):
                del self.current_settings["profiles"][choice]
                if self.current_settings.get("last_profile") == choice:
                    self.current_settings["last_profile"] = None # Clear last profile if it was the deleted one
                self.save_settings()
                self.update_load_profile_menu()
                self.set_status(f"Profile '{choice}' deleted.")
        elif choice:
             messagebox.showerror("Delete Error", f"Profile '{choice}' not found.", parent=self)


    # --- Settings Persistence ---

    def save_settings(self):
        """Saves current settings to SETTINGS_FILE, including open tabs."""
        # Save open tabs (filepaths or None for untitled tabs)
        open_tabs = []
        for tab_id in self.notebook.tabs():
            widget = self.nametowidget(tab_id)
            if hasattr(widget, 'filepath') and widget.filepath:
                open_tabs.append(widget.filepath)
            else:
                open_tabs.append(None)
        self.current_settings['open_tabs'] = open_tabs
        # Save as before
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, indent=2)
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
        # Remove all tabs safely
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        if open_tabs:
            for filepath in open_tabs:
                if filepath:
                    tab = self.add_new_tab(title=os.path.basename(filepath), filepath=filepath)
                    if hasattr(tab, 'load_playlist_from_file'):
                        tab.load_playlist_from_file(filepath)
                else:
                    self.add_new_tab("Untitled Playlist")

    # --- Pre-listening ---

    def toggle_play_pause(self):
        if not self.pygame_initialized:
            messagebox.showwarning("Audio Error", "Audio system not initialized. Cannot play.")
            return

        if self.currently_playing_path:
            if self.is_paused:
                # Resume
                try:
                    pygame.mixer.music.unpause()
                    self.is_paused = False
                    self.play_pause_button.config(text="❚❚ Pause")
                    self.set_status(f"Resumed: {os.path.basename(self.currently_playing_path)}")
                    # Restart progress updater from paused position
                    self.playback_start_time = time.time() - self.paused_position
                    self._update_playback_progress()
                except Exception as e:
                    messagebox.showerror("Playback Error", f"Could not resume playback: {e}")
                    self.stop_playback() # Stop fully if error
            else:
                # Pause
                try:
                    pygame.mixer.music.pause()
                    self.is_paused = True
                    self.play_pause_button.config(text="▶ Play")
                    self.set_status(f"Paused: {os.path.basename(self.currently_playing_path)}")
                    # Record position and stop updater
                    self.paused_position = time.time() - self.playback_start_time
                    if self.playback_update_job:
                        self.after_cancel(self.playback_update_job)
                        self.playback_update_job = None
                except Exception as e:
                    messagebox.showerror("Playback Error", f"Could not pause playback: {e}")
                    self.stop_playback() # Stop fully if error
        else:
            # Start playing selected track
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

            self.start_playback(track_data)

    def start_playback(self, track_data):
        """Starts playback of the given track data dictionary."""
        # Robust check: ensure mixer is actually initialized in pygame, not just our flag
        try:
            if pygame.mixer.get_init() is None:
                print("[WARN] Mixer not actually initialized at playback time. Attempting re-init.")
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                print("[INFO] Mixer re-initialized at playback time.")
                self.pygame_initialized = True
        except Exception as e:
            print(f"[ERROR] Failed to re-initialize mixer at playback time: {e}")
            self.set_status(f"Audio Error: Could not initialize mixer for playback: {e}")
            return
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
            self.current_track_duration = track_data.get('duration') or 0 # Get duration from track data
            self.play_pause_button.config(text="❚❚ Pause")
            self.update_prelisten_info(track_data)
            self.set_status(f"Playing: {os.path.basename(path)}")

            # Start progress updates
            self.playback_start_time = time.time()
            self._update_playback_progress()

        except Exception as e:
            print(f"[ERROR] Exception during playback: {e}")
            self.set_status(f"Audio Error: {e}")
            return

    def stop_playback(self):
        if not self.pygame_initialized: return

        if self.playback_update_job:
            self.after_cancel(self.playback_update_job)
            self.playback_update_job = None

        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload() # Free up the file handle
            except AttributeError:
                # Fallback for older pygame versions without unload
                pass
        except pygame.error as e:
            # Ignore errors on stop usually, maybe file was already gone?
            print(f"Pygame error during stop/unload: {e}")


        was_playing = self.currently_playing_path is not None
        self.currently_playing_path = None
        self.is_paused = False
        self.paused_position = 0
        self.play_pause_button.config(text="▶ Play")
        if was_playing:
            self.set_status("Playback stopped.")
            # Don't reset the label immediately, keep showing last track info until new selection/action
            self.progress_label.config(text=f"00:00 / {format_duration(self.current_track_duration)}")


    def _update_playback_progress(self):
        """Internal function to update the playback progress label."""
        if self.currently_playing_path and not self.is_paused and pygame.mixer.music.get_busy():
            # Using time.time() is more reliable than get_pos() for elapsed time after seeks/pauses
            elapsed_time = time.time() - self.playback_start_time

            # Cap elapsed time at duration if known
            if self.current_track_duration > 0:
                elapsed_time = min(elapsed_time, self.current_track_duration)

            self.progress_label.config(text=f"{format_duration(elapsed_time)} / {format_duration(self.current_track_duration)}")

            # Schedule next update
            self.playback_update_job = self.after(250, self._update_playback_progress) # Update 4 times a second
        elif self.currently_playing_path and not self.is_paused:
             # Music stopped naturally (finished)
             self.stop_playback() # Clean up state


    def update_prelisten_info(self, track_data):
         """Updates the pre-listen display area with track details."""
         if track_data:
             title = track_data.get('title', 'Unknown Title')
             artist = track_data.get('artist', 'Unknown Artist')
             duration_str = format_duration(track_data.get('duration'))
             self.prelisten_label.config(text=f"{artist} - {title}")
             # Only reset progress if not currently playing THIS track
             if track_data.get('path') != self.currently_playing_path:
                 self.progress_label.config(text=f"00:00 / {duration_str}")
                 self.current_track_duration = track_data.get('duration', 0) # Store duration for playback
         else:
             self.reset_prelisten_ui()

    def reset_prelisten_ui(self):
        self.prelisten_label.config(text="No track selected.")
        self.progress_label.config(text="00:00 / 00:00")
        self.play_pause_button.config(text="▶ Play")
        # Don't stop playback here, only reset UI text

    def apply_speed_change_on_next_play(self, event=None):
        # Currently just acknowledges the change. Real implementation is complex.
        speed = self.speed_var.get()
        self.set_status(f"Playback speed set to {speed} (will apply on next play if supported).")
        # In a real implementation, you might need to stop, reload with speed modification (if lib supports), and play.


    # --- Application Exit ---

    def quit_app(self):
        """Handles application closing, prompts for saving profiles/playlists."""
        # 1. Check unsaved playlists across all tabs
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
            if save_all is None: # Cancel exit
                return
            elif save_all is True: # Save All
                all_saved = True
                for tab_id in self.notebook.tabs():
                     self.notebook.select(tab_id) # Select tab to make close_current_tab work
                     tab_widget = self.nametowidget(tab_id)
                     if not self.close_current_tab():
                          all_saved = False
                          # Don't break, let user decide for others, but report failure
                          messagebox.showwarning("Save Failed", f"Could not save '{tab_widget.get_display_name()}'. Exiting anyway?", parent=self)
                          # Or could force exit cancellation:
                          # self.set_status("Exit cancelled due to save failure.")
                          # return
        # If save_all is False (No), proceed to exit without saving

        # 2. Stop audio gracefully
        if hasattr(self, 'pygame_initialized') and getattr(self, 'pygame_initialized', False):
            self.stop_playback()
            pygame.mixer.quit()
            print("Pygame mixer quit.")

        # 3. Save settings (like last loaded profile)
        self.save_settings()

        # 4. Destroy window
        self.destroy()

    def toggle_filter_bar(self):
        tab = self.get_current_tab()
        if tab:
            tab.show_filter_bar()

    def _auto_init_audio(self):
        """Tries to initialize pygame mixer with retry logic, silently."""
        self.pygame_initialized = False
        max_attempts = 5
        delay_ms = 500 # Delay between retries in milliseconds

        def attempt_init(attempt_num):
            if attempt_num > max_attempts:
                print("[ERROR] Audio could not be initialized after retries. Pre-listening disabled.")
                self.set_status("Audio not available: Mixer not initialized after retries.")
                return
            try:
                pygame.mixer.quit()
            except Exception:
                pass # Ignore errors during quit
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

        # Start the first attempt
        attempt_init(1)

    def on_tab_right_click(self, event):
        """Show context menu for renaming tab on right-click of notebook tab."""
        x, y = event.x, event.y
        elem = self.notebook.identify(event.x, event.y)
        if elem == 'label':
            tab_id = self.notebook.index(f"@{x},{y}")
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Rename Tab", command=lambda: self.rename_notebook_tab(tab_id))
            menu.tk_popup(event.x_root, event.y_root)

    def rename_notebook_tab(self, tab_id):
        """Prompt user to rename the tab at tab_id."""
        current_title = self.notebook.tab(tab_id, "text")
        new_title = simpledialog.askstring("Rename Tab", "Enter new tab name:", initialvalue=current_title, parent=self)
        if new_title and new_title.strip():
            self.notebook.tab(tab_id, text=new_title.strip())
            # Also update PlaylistTab's tab_display_name if possible
            widget = self.nametowidget(self.notebook.tabs()[tab_id])
            if hasattr(widget, 'tab_display_name'):
                widget.tab_display_name = new_title.strip()
