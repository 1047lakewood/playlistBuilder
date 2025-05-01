import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, simpledialog, messagebox
import os
import sys
import json
import shutil
import pygame # For prelistening
import threading # For non-blocking prelisten update
import time
import tkinter.font as tkfont
from metadata_utils import load_audio_metadata, save_audio_metadata
import subprocess
from common_components import (APP_NAME, SETTINGS_FILE, DEFAULT_COLUMNS, AVAILABLE_COLUMNS, 
                             M3U_ENCODING, format_duration, open_file_location, ColumnChooserDialog)
import tkinterdnd2 as tkdnd
import logging # Add logging import

def get_metadata(filepath):
    # Deprecated: Use load_audio_metadata from metadata_utils.py
    return load_audio_metadata(filepath)

# --- Playlist Tab Class ---

class PlaylistTab(ttk.Frame):
    def __init__(self, parent_notebook, app_controller, filepath=None, initial_columns=None):
        super().__init__(parent_notebook)
        self.notebook = parent_notebook
        self.app = app_controller
        self.filepath = filepath
        self.is_dirty = False
        self._track_data = [] # List of dictionaries holding track metadata
        self._iid_map = {} # Maps Treeview iid to index in _track_data for quick lookup
        self.tab_display_name = os.path.basename(filepath) if filepath else "Untitled Playlist"

        self.visible_columns = initial_columns if initial_columns else DEFAULT_COLUMNS

        # --- UI Elements ---
        # Toolbar Frame
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(side="top", fill="x", pady=(5,0), padx=5)

        # Restore original toolbar buttons
        self.add_files_button = ttk.Button(self.toolbar, text="Add Files...", command=self.add_files)
        self.add_files_button.pack(side="left", padx=(0,5))
        self.add_folder_button = ttk.Button(self.toolbar, text="Add Folder...", command=self.add_folder)
        self.add_folder_button.pack(side="left", padx=(0,5))
        self.remove_button = ttk.Button(self.toolbar, text="Remove Selected", command=self.remove_selected_tracks)
        self.remove_button.pack(side="left", padx=(0,5))
        self.move_up_button = ttk.Button(self.toolbar, text="Move Up", command=self.move_selected_up)
        self.move_up_button.pack(side="left", padx=(5,5))
        self.move_down_button = ttk.Button(self.toolbar, text="Move Down", command=self.move_selected_down)
        self.move_down_button.pack(side="left", padx=(0,5))

        # Find Area (replaces Filter)
        self.find_label = ttk.Label(self.toolbar, text="Find:")
        self.find_label.pack(side="left", padx=(15, 2))
        self.find_var = tk.StringVar()
        self.find_entry = ttk.Entry(self.toolbar, textvariable=self.find_var, width=30)
        self.find_entry.pack(side="left", padx=(0, 5))
        self.find_entry.bind('<Return>', self.find_next)
        self.clear_find_button2 = ttk.Button(self.toolbar, text="Clear", command=lambda: self.find_var.set(""), width=6)
        self.clear_find_button2.pack(side="left")
        self.find_prev_button = ttk.Button(self.toolbar, text="◀", width=2, command=lambda: self.find_next(reverse=True))
        self.find_prev_button.pack(side="left", padx=(2,0))
        self.find_next_button = ttk.Button(self.toolbar, text="▶", width=2, command=self.find_next)
        self.find_next_button.pack(side="left", padx=(0,5))
        self._find_matches = []
        self._find_index = -1

        # --- Find results count label ---
        self.find_count_var = tk.StringVar(value="")
        self.find_count_label = ttk.Label(self.toolbar, textvariable=self.find_count_var, width=14, anchor="w")
        self.find_count_label.pack(side="left", padx=(5, 0))

        # Filter moved to menu (View menu)
        self.filter_frame = None

        # Treeview Frame with Scrollbar
        self.tree_frame = ttk.Frame(self)
        self.tree_frame.pack(expand=True, fill="both", side="top", pady=5, padx=5)

        self.scrollbar_y = ttk.Scrollbar(self.tree_frame, orient="vertical")
        self.scrollbar_x = ttk.Scrollbar(self.tree_frame, orient="horizontal")

        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=AVAILABLE_COLUMNS, # Define all possible columns
            displaycolumns=self.visible_columns, # Show only the selected ones
            show="headings",
            yscrollcommand=self.scrollbar_y.set,
            xscrollcommand=self.scrollbar_x.set,
            selectmode="extended" # Allow multiple selections
        )

        self.scrollbar_y.config(command=self.tree.yview)
        self.scrollbar_x.config(command=self.tree.xview)

        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")
        self.tree.pack(expand=True, fill="both", side="left")

        self.setup_columns()

        # --- Treeview Tag Styles ---
        # Red + strikethrough for missing files
        try:
            default_font = tkfont.nametofont(self.tree.cget("font"))
            missing_font = default_font.copy()
            missing_font.configure(overstrike=1)
            self.tree.tag_configure("missing", foreground="red", font=missing_font)
        except Exception:
            # Fallback: just red if font fails
            self.tree.tag_configure("missing", foreground="red")
        # Optionally, ensure 'found' tag is default
        self.tree.tag_configure("found", foreground="black")

        # --- DND hover highlight ---
        self._dnd_hover_iid = None
        self.tree.tag_configure("dnd_hover", background="#cce6ff")

        # --- Treeview Bindings ---
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu) # Right-click
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Delete>", lambda e: self.remove_selected_tracks()) # Delete key
        self.tree.bind("<Control-c>", lambda e: self.app.copy_selected())
        self.tree.bind("<Control-C>", lambda e: self.app.copy_selected())
        self.tree.bind("<Control-v>", lambda e: self.paste_after_selected())
        self.tree.bind("<Control-V>", lambda e: self.paste_after_selected())
        self.find_entry.bind('<Return>', self.find_next)
        # Right-click context menu: add Paste
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Pre-listen", command=self.context_prelisten)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy", command=self.context_copy)
        # Paste is handled globally/via edit menu
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Edit Metadata...", command=self.context_edit_metadata)
        self.context_menu.add_command(label="Rename Manually", command=self.context_rename_file_manual)
        self.context_menu.add_command(label="Rename by Browsing", command=self.context_rename_file_browse)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rename Tab", command=self.context_rename_tab)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open File Location", command=self.context_open_location)
        self.context_menu.add_command(label="Check File Existence", command=self.context_check_existence)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remove From Playlist", command=self.context_remove)
        self.context_menu.add_command(label="Paste After", command=self.paste_after_selected)

        # Enable drag-and-drop for reordering playlist tracks in the treeview
        self.tree.bind('<ButtonPress-1>', self._on_tree_press)
        self.tree.bind('<B1-Motion>', self._on_tree_drag)
        self.tree.bind('<ButtonRelease-1>', self._on_tree_release)
        self._dragged_iid = None
        self._dragged_index = None

        # Enable drag-and-drop from other programs (files)
        self._dnd_enabled = False
        try:
            import tkinterdnd2 as tkdnd
            # Use the root window from the app, which is a TkinterDnD.Tk instance
            root = self.winfo_toplevel()
            self.tree.drop_target_register(tkdnd.DND_FILES)
            self.tree.dnd_bind('<<Drop>>', self._on_external_drop)
            self.tree.dnd_bind('<<DropPosition>>', self._on_external_dragover)
            self._dnd_enabled = True
            print("[DND] External drag-and-drop enabled.")
        except (ImportError, Exception) as e:
            print(f"[WARN] Drag-and-drop from outside is disabled: {e}")

    def context_rename_tab(self):
        new_name = simpledialog.askstring("Rename Tab", "Enter new tab name:", initialvalue=self.tab_display_name, parent=self)
        if new_name:
            self.tab_display_name = new_name
            self.update_tab_title()

    def update_tab_title(self):
        idx = self.notebook.index(self)
        self.notebook.tab(idx, text=self.get_display_name())

    def get_display_name(self):
        return self.tab_display_name + ("*" if self.is_dirty else "")

    def show_filter_bar(self):
        if self.filter_frame:
            self.filter_frame.pack_forget()
            self.filter_frame = None
            return
        self.filter_frame = ttk.Frame(self.toolbar)
        self.filter_frame.pack(side="right", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_tracks)
        self.search_label = ttk.Label(self.filter_frame, text="Filter:")
        self.search_label.pack(side="left")
        self.search_entry = ttk.Entry(self.filter_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left", padx=(0, 5))
        self.clear_search_button2 = ttk.Button(self.filter_frame, text="Clear", command=lambda: self.search_var.set(""), width=6)
        self.clear_search_button2.pack(side="left")

    def find_tracks(self, event=None):
        find_term = self.find_var.get().lower()
        if not find_term:
            self.refresh_display()
            return
        display_data = []
        for track in self._track_data:
            match = False
            for col in self.visible_columns:
                val = self.get_formatted_value(track, col)
                if find_term in str(val).lower():
                    match = True
                    break
            if match:
                display_data.append(track)
        self.refresh_display(custom_data=display_data)

    def refresh_display(self, sort_col=None, reverse_sort=False, keep_selection=True, custom_data=None):
        selected_iids = self.tree.selection() if keep_selection else []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._iid_map.clear()
        if sort_col:
            self._sort_internal_data(sort_col, reverse_sort)
        display_data = custom_data if custom_data is not None else self._track_data
        for index, track_info in enumerate(display_data):
            values = [index + 1 if col == '#' else self.get_formatted_value(track_info, col) for col in AVAILABLE_COLUMNS]
            tag = "missing" if not track_info.get('exists', True) else "found"
            iid = self.tree.insert("", tk.END, values=values, tags=(tag,))
            self._iid_map[iid] = track_info
        if keep_selection:
            self.tree.selection_set(())

    def get_formatted_value(self, track_data, column_id):
        if column_id == '#':
            return '' # Handled in refresh_display
        elif column_id == 'Duration':
            return format_duration(track_data.get('duration'))
        elif column_id == 'Exists':
            return "Yes" if track_data.get('exists', False) else "No"
        elif column_id == 'Bitrate':
            br = track_data.get('bitrate')
            return f"{br // 1000} kbps" if br else ""
        elif column_id == 'TrackNumber':
            return track_data.get('tracknumber', '')
        else:
            val = track_data.get(column_id.lower(), '')
            if isinstance(val, list):
                return ', '.join(val)
            return val if val is not None else ''

    def get_selected_item_ids(self):
        """Returns a list of the selected item IDs in the Treeview."""
        return self.tree.selection()

    def get_selected_item_id(self):
        """Returns the first selected item ID, or None."""
        selection = self.tree.selection()
        return selection[0] if selection else None

    def get_track_data_by_iid(self, iid):
        """Gets the internal track data dictionary associated with a Treeview item ID."""
        return self._iid_map.get(iid)

    def get_selected_track_data(self):
        """Returns a list of track data dictionaries for selected items."""
        selected_data = []
        for iid in self.tree.selection():
            data = self.get_track_data_by_iid(iid)
            if data:
                selected_data.append(data)
        return selected_data

    def update_track_display(self, iid, track_data):
        """Updates a single row in the treeview."""
        if iid in self._iid_map:
            # Always recalculate the # column index for correct display
            # Find the visible index of this iid
            all_iids = list(self.tree.get_children())
            try:
                row_index = all_iids.index(iid)
            except ValueError:
                row_index = None
            values = [row_index + 1 if col == '#' and row_index is not None else self.get_formatted_value(track_data, col) for col in AVAILABLE_COLUMNS]
            tag = "missing" if not track_data.get('exists', True) else "found"
            self.tree.item(iid, values=values, tags=(tag,))
            # Update the map reference just in case the dict instance changed (it shouldn't if modified in place)
            self._iid_map[iid] = track_data

    # --- Event Handlers ---

    def on_double_click(self, event):
        """Handles double-clicking a track - starts pre-listening."""
        iid = self.tree.identify_row(event.y)
        if iid:
            track_data = self.get_track_data_by_iid(iid)
            if track_data:
                self.app.start_playback(track_data)


    def on_tree_select(self, event=None):
        """Update prelisten info display when selection changes."""
        iid = self.get_selected_item_id() # Get first selected
        if iid:
             track_data = self.get_track_data_by_iid(iid)
             self.app.update_prelisten_info(track_data)
        else:
             # Selection cleared, but don't stop playback, just clear info display if nothing is playing
             if not self.app.currently_playing_path:
                  self.app.reset_prelisten_ui()

    def show_context_menu(self, event):
        """Shows the right-click context menu."""
        # Detect if right-clicked on tab area
        if event.widget == self.notebook:
            # Right-clicked on the tab bar, show tab rename
            current_tab = self.app.get_current_tab()
            if current_tab:
                current_tab.context_rename_tab()
            return
        iid = self.tree.identify_row(event.y)
        if iid:
            # Select the item under the cursor if it wasn't already selected
            if iid not in self.tree.selection():
                self.tree.selection_set(iid) # Select only this item
                # self.tree.selection_add(iid) # Or add to selection

            self.context_menu.post(event.x_root, event.y_root)
        # else: # Optional: show a different menu if clicking empty space?
        #     pass

    # --- Track Manipulation ---

    def add_tracks(self, track_data_list):
        """Adds multiple tracks (list of dicts) to the internal data and refreshes view."""
        # Could add checks for duplicates here if desired
        newly_added_iids = []
        for track_info in track_data_list:
             # Ensure necessary keys exist, even if blank
             track_info.setdefault('artist', 'Unknown Artist')
             track_info.setdefault('title', os.path.splitext(os.path.basename(track_info.get('path','')))[0] if track_info.get('path') else 'Unknown Title')
             track_info.setdefault('path', None)
             track_info.setdefault('exists', os.path.exists(track_info['path']) if track_info['path'] else False)
             # Add other defaults...

             self._track_data.append(track_info)

             # Insert directly into treeview for immediate feedback (might be slow for huge additions)
             values = [self.get_formatted_value(track_info, col) for col in AVAILABLE_COLUMNS]
             tag = "missing" if not track_info.get('exists', True) else "found"
             iid = self.tree.insert("", tk.END, values=values, tags=(tag,))
             self._iid_map[iid] = track_info
             newly_added_iids.append(iid)


        # self.refresh_display(keep_selection=False) # Full refresh might be better for consistency
        self.mark_dirty()
        # Optionally scroll to and select the newly added items
        if newly_added_iids:
             self.tree.selection_set(newly_added_iids)
             self.tree.see(newly_added_iids[-1]) # Scroll to the last added item


    def add_files(self):
        """Opens dialog to add audio files."""
        filepaths = filedialog.askopenfilenames(
            title="Add Audio Files",
            filetypes=[("Audio Files", "*.mp3 *.wav *.ogg *.flac *.m4a *.aac"), ("All Files", "*.*")]
        )
        if filepaths:
            self.app.set_status(f"Scanning {len(filepaths)} files...")
            new_tracks = []
            # Process in chunks or thread for large additions? For now, direct.
            for i, path in enumerate(filepaths):
                 self.app.set_status(f"Scanning file {i+1}/{len(filepaths)}: {os.path.basename(path)}")
                 self.app.update_idletasks() # Allow UI to update status
                 metadata = load_audio_metadata(path)
                 if metadata['duration'] is None:
                     self.app.set_status(f"Warning: No duration for {os.path.basename(path)}")
                 new_tracks.append(metadata)

            self.add_tracks(new_tracks)
            self.app.set_status(f"Added {len(new_tracks)} tracks.")

    def add_folder(self):
        """Opens dialog to add all audio files from a folder (recursively)."""
        folderpath = filedialog.askdirectory(title="Add Folder Contents")
        if not folderpath:
            return

        self.app.set_status(f"Scanning folder: {folderpath}...")
        self.app.update_idletasks()
        
        new_tracks = []
        file_count = 0
        audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'} # Add more if needed

        for root, _, files in os.walk(folderpath):
            for filename in files:
                if os.path.splitext(filename)[1].lower() in audio_extensions:
                    file_count += 1
                    filepath = os.path.join(root, filename)
                    self.app.set_status(f"Scanning file {file_count}: {filename}")
                    self.app.update_idletasks()
                    metadata = load_audio_metadata(filepath)
                    if metadata['duration'] is None:
                        self.app.set_status(f"Warning: No duration for {filename}")
                    new_tracks.append(metadata)

        if new_tracks:
            self.add_tracks(new_tracks)
            self.app.set_status(f"Added {len(new_tracks)} tracks from folder.")
        else:
            self.app.set_status(f"No supported audio files found in folder: {folderpath}")


    def remove_selected_tracks(self):
        """Removes selected tracks from the list and Treeview."""
        selected_iids = self.tree.selection()
        if not selected_iids:
            return

        items_to_remove_from_data = []
        for iid in selected_iids:
            track_data = self.get_track_data_by_iid(iid)
            if track_data:
                 items_to_remove_from_data.append(track_data)
            # Remove from tree immediately
            self.tree.delete(iid)
            if iid in self._iid_map:
                 del self._iid_map[iid]

        # Remove from the internal data list
        # This is inefficient (O(n*m)), better to rebuild _track_data or use indices
        new_track_data = [track for track in self._track_data if track not in items_to_remove_from_data]
        self._track_data = new_track_data

        # No need for full refresh if items deleted directly
        # self.refresh_display(keep_selection=False)
        self.mark_dirty()
        self.app.set_status(f"Removed {len(selected_iids)} track(s).")

    def move_selected_up(self):
         """Moves selected items one position up in the Treeview."""
         selection = self.tree.selection()
         if not selection: return

         # Process selections from top to bottom to avoid index issues
         # Get all children once to determine indices
         all_children = self.tree.get_children('')
         
         moved_count = 0
         for iid in selection:
              current_index = self.tree.index(iid)
              if current_index > 0:
                  # Check if the item above is also selected, if so, skip moving this one relative to it
                  prev_iid = all_children[current_index - 1]
                  if prev_iid not in selection:
                      self.tree.move(iid, '', current_index - 1)
                      # Update internal _track_data order to match
                      track_data = self.get_track_data_by_iid(iid)
                      if track_data:
                          # Find the actual index in _track_data (slow, needs optimization)
                          try:
                             data_index = self._track_data.index(track_data)
                             # Ensure we don't move past beginning or into another selected block being moved
                             if data_index > 0:
                                 # Find the data of the item visually above
                                 prev_track_data = self.get_track_data_by_iid(prev_iid)
                                 if prev_track_data:
                                     try:
                                         prev_data_index = self._track_data.index(prev_track_data)
                                         # Swap in _track_data if indices match visual move
                                         if data_index == prev_data_index + 1:
                                             self._track_data.pop(data_index)
                                             self._track_data.insert(prev_data_index, track_data)
                                             moved_count+=1
                                     except ValueError: pass # Target data not found?
                          except ValueError: pass # Current data not found?

         if moved_count > 0:
              self.mark_dirty()
              # Renumbering might be needed here if '#' column is critical
              # self.refresh_display(keep_selection=True) # Easier but resets view state

    def move_selected_down(self):
         """Moves selected items one position down in the Treeview."""
         selection = self.tree.selection()
         if not selection: return

         # Process selections from bottom to top
         all_children = self.tree.get_children('')
         max_index = len(all_children) - 1

         moved_count = 0
         for iid in reversed(selection): # Iterate backwards
             current_index = self.tree.index(iid)
             if current_index < max_index:
                 # Check if the item below is also selected
                 next_iid = all_children[current_index + 1]
                 if next_iid not in selection:
                     self.tree.move(iid, '', current_index + 1)
                     # Update internal _track_data order (similar logic to move_up, but reversed)
                     track_data = self.get_track_data_by_iid(iid)
                     if track_data:
                         try:
                             data_index = self._track_data.index(track_data)
                             if data_index < len(self._track_data) - 1:
                                 next_track_data = self.get_track_data_by_iid(next_iid)
                                 if next_track_data:
                                     try:
                                         next_data_index = self._track_data.index(next_track_data)
                                         if data_index == next_data_index - 1:
                                              # Move item down in _track_data
                                              item_to_move = self._track_data.pop(data_index)
                                              self._track_data.insert(data_index + 1, item_to_move) # Insert after original next item
                                              moved_count+=1
                                     except ValueError: pass
                         except ValueError: pass
         
         if moved_count > 0:
             self.mark_dirty()
             # Renumbering might be needed here if '#' column is critical
             # self.refresh_display(keep_selection=True)


    def _sort_internal_data(self, column_id, reverse):
        """Sorts the internal _track_data list based on a column."""
        if not column_id: return

        def sort_key(track):
            value = track.get(column_id.lower())
            # Handle different types for sorting
            if value is None:
                return -1 if column_id == 'Duration' else '' # Sort None durations first, empty strings first
            if column_id in ('#', 'TrackNumber', 'Bitrate'):
                try: return int(value)
                except (ValueError, TypeError): return 0
            if column_id == 'Duration':
                 try: return float(value)
                 except (ValueError, TypeError): return -1.0
            if column_id == 'Exists':
                 return bool(value) # False then True
            # Default: case-insensitive string sort
            return str(value).lower()

        try:
            self._track_data.sort(key=sort_key, reverse=reverse)
        except Exception as e:
            print(f"Error sorting data: {e}") # Avoid crashing on unexpected data


    def sort_column(self, column_id):
        """Sorts the treeview by the clicked column header."""
        # Basic toggle sorting direction (needs state per column)
        # For simplicity, let's just sort ascending first time, then maybe toggle later
        # This implementation sorts the *internal data* then refreshes the view
        
        # Basic toggle: Does not store state per column yet
        current_heading = self.tree.heading(column_id)
        order = current_heading.get("command", "") # Store sort order here? Hacky.
        reverse = False
        if f" {column_id}_asc" in str(order): # Simple state check
            reverse = True
            new_command = lambda c=column_id: self.sort_column(c) # Reset command for next click
            # Update visual indicator if possible (ttk doesn't have built-in arrows)
        else:
            reverse = False
            new_command = lambda c=column_id: self.sort_column(c) # Store state in command itself
            # Hack: Store state indicating ascending sort was just done
            # self.tree.heading(column_id, command=str(new_command) + f" {column_id}_asc")

        self.refresh_display(sort_col=column_id, reverse_sort=reverse, keep_selection=False)
        self.app.set_status(f"Sorted by {column_id} {'Descending' if reverse else 'Ascending'}")


    def filter_tracks(self, *args):
        """Filters the Treeview based on the search entry."""
        # Debounce this? Could be slow on huge lists if called on every keypress
        # For now, refresh directly
        self.refresh_display(keep_selection=False)

    # --- Context Menu Actions ---

    def context_prelisten(self):
        iid = self.get_selected_item_id()
        if iid:
            track_data = self.get_track_data_by_iid(iid)
            if track_data:
                 self.app.start_playback(track_data)

    def context_copy(self):
        self.app.copy_selected() # Use global copy handler

    def context_remove(self):
        self.remove_selected_tracks()

    def context_edit_metadata(self):
        selected_iids = self.get_selected_item_ids()
        if not selected_iids: return
        if len(selected_iids) > 1:
             messagebox.showinfo("Edit Metadata", "Please select only one track to edit metadata.")
             return

        iid = selected_iids[0]
        track_data = self.get_track_data_by_iid(iid)
        if not track_data or not track_data['path']:
             messagebox.showerror("Metadata Error", "Cannot edit metadata: Track data or path is missing.")
             return

        if not track_data['exists']:
             messagebox.showwarning("Metadata Warning", "Cannot edit metadata: File does not exist.")
             return

        dialog = MetadataEditDialog(self, track_data)
        if dialog.result: # result contains the updated track_data dict
            # 1. Save changes to the audio file using save_audio_metadata from metadata_utils.py
            try:
                success, error = save_audio_metadata(track_data['path'], dialog.result)
                if not success:
                    raise Exception(error)
                self.app.set_status(f"Metadata saved for: {os.path.basename(track_data['path'])}")

                # 2. Update internal data dictionary (modify in place)
                # Re-read duration/format in case they changed (unlikely but possible)
                updated_meta = load_audio_metadata(track_data['path']) # Re-read all info
                # Only update the fields we allow editing + potentially changed info
                track_data.update(updated_meta) # Overwrite original dict with fresh data

                # 3. Update Treeview display
                self.update_track_display(iid, track_data)
                self.mark_dirty() # Editing metadata might make playlist content effectively different

            except Exception as e:
                import traceback
                print("[ERROR] Metadata Save Error:")
                print(f"  Path: {track_data['path']}")
                print(f"  Dialog Result: {dialog.result}")
                traceback.print_exc()
                messagebox.showerror("Metadata Save Error", f"Could not save metadata for:\n{track_data['path']}\n\nError: {e}")
                self.app.set_status("Metadata save failed.")
                print(f"[ERROR] Metadata Save Error: {e}")

    def context_rename_file_manual(self):
        selected_iids = self.get_selected_item_ids()
        if not selected_iids: return
        if len(selected_iids) > 1:
            messagebox.showinfo("Rename File", "Please select only one track to rename.")
            return
        iid = selected_iids[0]
        track_data = self.get_track_data_by_iid(iid)
        if not track_data or not track_data['path']:
            messagebox.showerror("Rename Error", "Cannot rename: Track data or path is missing.")
            return
        old_path = track_data['path']
        new_path = simpledialog.askstring("Rename File", "Enter the new file path (including extension):", initialvalue=old_path, parent=self)
        if not new_path or new_path == old_path:
            self.app.set_status("Rename cancelled.")
            return
        invalid_chars = ['/', '\\', ':']
        if any(char in os.path.basename(new_path) for char in invalid_chars):
            messagebox.showerror("Rename Error", "New filename cannot contain path separators or invalid characters.")
            return
        try:
            if track_data['exists']:
                try:
                    shutil.move(old_path, new_path)
                    self.app.set_status(f"Renamed '{os.path.basename(old_path)}' to '{os.path.basename(new_path)}'")
                    track_data['exists'] = True
                except Exception as e:
                    messagebox.showerror("Rename Failed", f"Could not rename file:\n{old_path}\n\nError: {e}")
                    self.app.set_status("File rename failed.")
                    track_data['exists'] = os.path.exists(old_path)
                    self.update_track_display(iid, track_data)
                    return
            else:
                self.app.set_status(f"Updated non-existent playlist entry path to '{os.path.basename(new_path)}'")
            track_data['path'] = new_path
            if track_data.get('title') == os.path.splitext(os.path.basename(old_path))[0]:
                track_data['title'] = os.path.splitext(os.path.basename(new_path))[0]
            # --- RELOAD METADATA FULLY AND CHECK EXISTENCE ---
            meta = load_audio_metadata(new_path)
            # Overwrite all relevant fields from meta
            for key in ['artist', 'title', 'album', 'genre', 'tracknumber', 'duration', 'bitrate', 'format', 'exists', 'path']:
                track_data[key] = meta.get(key, track_data.get(key))
            self.update_track_display(iid, track_data)
            self.mark_dirty()
        except Exception as e:
            messagebox.showerror("Rename Failed", f"Could not update playlist entry:\n{old_path}\n\nError: {e}")
            self.app.set_status("File rename failed.")
            track_data['exists'] = os.path.exists(old_path)
            self.update_track_display(iid, track_data)

    def context_rename_file_browse(self):
        selected_iids = self.get_selected_item_ids()
        if not selected_iids: return
        if len(selected_iids) > 1:
            messagebox.showinfo("Rename File", "Please select only one track to rename.")
            return
        iid = selected_iids[0]
        track_data = self.get_track_data_by_iid(iid)
        if not track_data or not track_data['path']:
            messagebox.showerror("Rename Error", "Cannot rename: Track data or path is missing.")
            return
        old_path = track_data['path']
        directory = os.path.dirname(old_path)
        initialfile = os.path.basename(old_path)
        new_path = filedialog.askopenfilename(initialdir=directory, initialfile=initialfile, title="Select New File Path", parent=self)
        if not new_path or new_path == old_path:
            self.app.set_status("Rename cancelled.")
            return
        invalid_chars = ['/', '\\', ':']
        if any(char in os.path.basename(new_path) for char in invalid_chars):
            messagebox.showerror("Rename Error", "New filename cannot contain path separators or invalid characters.")
            return
        try:
            if track_data['exists']:
                try:
                    shutil.move(old_path, new_path)
                    self.app.set_status(f"Renamed '{os.path.basename(old_path)}' to '{os.path.basename(new_path)}'")
                    track_data['exists'] = True
                except Exception as e:
                    messagebox.showerror("Rename Failed", f"Could not rename file:\n{old_path}\n\nError: {e}")
                    self.app.set_status("File rename failed.")
                    track_data['exists'] = os.path.exists(old_path)
                    self.update_track_display(iid, track_data)
                    return
            else:
                self.app.set_status(f"Updated non-existent playlist entry path to '{os.path.basename(new_path)}'")
            track_data['path'] = new_path
            if track_data.get('title') == os.path.splitext(os.path.basename(old_path))[0]:
                track_data['title'] = os.path.splitext(os.path.basename(new_path))[0]
            # --- RELOAD METADATA FULLY AND CHECK EXISTENCE ---
            meta = load_audio_metadata(new_path)
            for key in ['artist', 'title', 'album', 'genre', 'tracknumber', 'duration', 'bitrate', 'format', 'exists', 'path']:
                track_data[key] = meta.get(key, track_data.get(key))
            self.update_track_display(iid, track_data)
            self.mark_dirty()
        except Exception as e:
            messagebox.showerror("Rename Failed", f"Could not update playlist entry:\n{old_path}\n\nError: {e}")
            self.app.set_status("File rename failed.")
            track_data['exists'] = os.path.exists(old_path)
            self.update_track_display(iid, track_data)

    def context_open_location(self):
        iid = self.get_selected_item_id()
        if iid:
            track_data = self.get_track_data_by_iid(iid)
            if track_data and track_data['path']:
                 open_file_location(track_data['path'])
            else:
                 messagebox.showerror("Error", "Path information is missing for this item.")

    def context_check_existence(self):
        """Re-checks existence for selected files."""
        selected_iids = self.get_selected_item_ids()
        for iid in selected_iids:
            track_data = self.get_track_data_by_iid(iid)
            if not track_data or not track_data['path']:
                continue
            meta = load_audio_metadata(track_data['path'])
            track_data['exists'] = meta.get('exists', False)
            track_data['duration'] = meta.get('duration', 0)
            self.update_track_display(iid, track_data)
        self.app.set_status("Checked file existence and duration.")


    # --- Data Loading/Saving ---

    def load_playlist_from_file(self, filepath):
        """Loads tracks from an M3U/M3U8 file and refreshes all metadata."""
        try:
            with open(filepath, 'r', encoding=M3U_ENCODING) as f:
                lines = f.readlines()
            # --- Optimization: batch metadata loading ---
            track_paths = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                abs_path = os.path.abspath(os.path.join(os.path.dirname(filepath), line)) if not os.path.isabs(line) else line
                track_paths.append(abs_path)
            # Use threads to load metadata in parallel for speedup
            import concurrent.futures
            new_tracks = []
            def safe_load(path):
                return load_audio_metadata(path)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(safe_load, track_paths))
            for meta, orig_path in zip(results, track_paths):
                # Accept if duration, or if a path was provided (even if no title in metadata)
                if meta.get('duration') or orig_path:
                    new_tracks.append(meta)
            self._track_data = new_tracks
            self.refresh_display()
            self.is_dirty = False
            self.update_tab_title()
            return True
        except Exception as e:
            import traceback
            logging.error(f"[PLAYLIST][ERROR] Failed to load playlist from {filepath}: {e}\n{traceback.format_exc()}")
            return False


    def save_playlist(self, force_save_as=False):
        """Saves the playlist to M3U8 format."""
        target_path = self.filepath
        if force_save_as or not target_path:
            target_path = filedialog.asksaveasfilename(
                title="Save Playlist As",
                defaultextension=".m3u8",
                filetypes=[("M3U Playlist", "*.m3u8"), ("All Files", "*.*")],
                initialfile=os.path.basename(self.filepath) if self.filepath else "playlist.m3u8"
            )
            if not target_path:
                self.app.set_status("Save cancelled.")
                return False # Indicate save was cancelled

        self.app.set_status(f"Saving playlist: {os.path.basename(target_path)}...")
        try:
            playlist_dir = os.path.dirname(target_path)
            os.makedirs(playlist_dir, exist_ok=True) # Ensure directory exists

            with open(target_path, 'w', encoding=M3U_ENCODING) as f:
                f.write("#EXTM3U\n") # Standard M3U header
                # Use the current order from the Treeview (or _track_data if no filter)
                track_paths_in_order = [self.get_track_data_by_iid(iid)['path'] for iid in self.tree.get_children('')]
                # Or use self._track_data if filtering shouldn't affect save order
                # track_paths_in_order = [track['path'] for track in self._track_data]

                for track_path in track_paths_in_order:
                    # Attempt to make paths relative to the playlist file
                    try:
                        relative_path = os.path.relpath(track_path, playlist_dir)
                    except ValueError:
                        # Happens if paths are on different drives (Windows)
                        relative_path = track_path # Use absolute path

                    # At the start of start_playback
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
                    f.write(relative_path + "\n")

            self.filepath = target_path # Update file path if saved successfully
            self.mark_dirty(False)
            self.update_tab_title() # Update title to remove '*' and reflect new name if 'Save As'
            self.app.set_status(f"Playlist saved: {os.path.basename(target_path)}")
            return True

        except Exception as e:
            self.app.set_status(f"Error saving playlist {os.path.basename(target_path)}: {e}")
            messagebox.showerror("Save Error", f"Could not save playlist to:\n{target_path}\n\nError: {e}")
            return False


    # --- Treeview Display and Interaction ---

    def setup_columns(self):
        """Sets up the Treeview columns based on AVAILABLE_COLUMNS."""
        # Configure all potential columns once
        col_widths = {'#': 40, 'Artist': 150, 'Title': 250, 'Album': 150, 'Genre': 100, 'TrackNumber': 40, 'Duration': 60, 'Path': 300, 'Exists': 50, 'Bitrate':60, 'Format': 60}
        col_anchors = {'#': 'e', 'TrackNumber': 'e', 'Duration': 'e', 'Exists': 'center', 'Bitrate':'e'}

        for col in AVAILABLE_COLUMNS:
            self.tree.heading(col, text=col)  # No sort command
            self.tree.column(col, width=col_widths.get(col, 100), anchor=col_anchors.get(col, 'w'), stretch=tk.NO if col in ['#','Duration','Exists','TrackNumber','Bitrate','Format'] else tk.YES)

        # Apply the currently visible columns
        self.update_columns(self.visible_columns)


    def update_columns(self, visible_column_ids):
        """Updates which columns are visible in the Treeview."""
        self.visible_columns = visible_column_ids
        self.tree['displaycolumns'] = self.visible_columns
        # No need to re-setup headings/widths, just visibility


    def update_displayed_columns(self, new_columns):
        """Updates the columns visible in the treeview."""
        self.visible_columns = new_columns
        try:
            # Filter to only include columns that actually exist in AVAILABLE_COLUMNS
            valid_display_columns = [col for col in new_columns if col in AVAILABLE_COLUMNS]
            if not valid_display_columns:
                # Fallback if somehow all columns are invalid
                valid_display_columns = DEFAULT_COLUMNS
                self.visible_columns = DEFAULT_COLUMNS # Update internal state too

            self.tree.config(displaycolumns=valid_display_columns)
            # Optional: Re-run setup if column widths/headings depend on visibility?
            # self.setup_columns() # Usually not needed just for visibility change
            logging.debug(f"Updated displayed columns for tab '{self.tab_display_name}' to: {valid_display_columns}")
        except tk.TclError as e:
            logging.error(f"Error updating displaycolumns for tab '{self.tab_display_name}': {e}", exc_info=True)
        except Exception as e:
             logging.error(f"Unexpected error in update_displayed_columns for tab '{self.tab_display_name}': {e}", exc_info=True)

    def mark_dirty(self, dirty=True):
        """Sets the dirty state and updates the tab title."""
        if self.is_dirty != dirty:
            self.is_dirty = dirty
            self.update_tab_title()

    def find_next(self, event=None, reverse=False):
        query = self.find_entry.get().strip().lower()
        if not query:
            self.app.set_status("Enter search text.")
            self.find_count_var.set("")
            return
        matches = []
        for iid in self.tree.get_children():
            values = self.tree.item(iid, 'values')
            if any(query in str(v).lower() for v in values):
                matches.append(iid)
        if not matches:
            self.app.set_status("No matches found.")
            self.find_count_var.set("0 found")
            return
        # Cycle through matches
        current = self.tree.selection()
        if current and current[0] in matches:
            idx = matches.index(current[0])
            next_idx = (idx - 1) % len(matches) if reverse else (idx + 1) % len(matches)
        else:
            next_idx = 0
        self.tree.selection_set(matches[next_idx])
        self.tree.see(matches[next_idx])
        self.app.set_status(f"Found {len(matches)} match(es). Showing {next_idx+1} of {len(matches)}.")
        self.find_count_var.set(f"{len(matches)} found")

    def clear_find(self):
        self.find_var.set("")
        self.tree.selection_remove(self.tree.selection())
        self._find_matches = []
        self._find_index = -1

    def paste_after_selected(self):
        """Paste clipboard tracks after the currently selected track(s)."""
        if not self.app.clipboard:
            self.app.set_status("Clipboard is empty.")
            return
        selected = list(self.tree.selection())
        if selected:
            # Insert after last selected
            last_iid = selected[-1]
            last_index = self.tree.index(last_iid)
            insert_index = last_index + 1
        else:
            # No selection, append at end
            insert_index = len(self._track_data)
        for track in self.app.clipboard:
            track_copy = track.copy()
            self._track_data.insert(insert_index, track_copy)
            values = [self.get_formatted_value(track_copy, col) for col in AVAILABLE_COLUMNS]
            tag = "missing" if not track_copy.get('exists', True) else "found"
            iid = self.tree.insert("", insert_index, values=values, tags=(tag,))
            self._iid_map[iid] = track_copy
            insert_index += 1
        self.mark_dirty()
        self.tree.selection_set(self.tree.get_children()[insert_index - len(self.app.clipboard):insert_index])
        self.tree.see(self.tree.get_children()[insert_index - 1])
        self.app.set_status(f"Pasted {len(self.app.clipboard)} track(s) after selection.")

    def _on_tree_press(self, event):
        # Only start drag if plain left-click (no shift/ctrl modifiers)
        if (event.state & 0x0001) or (event.state & 0x0004):  # Shift or Control pressed
            # Let default selection logic handle shift/ctrl multi-select
            self._dragged_iid = None
            self._dragged_index = None
            return
        iid = self.tree.identify_row(event.y)
        if iid:
            # Only start drag if clicking on a selected row and no modifiers
            if iid in self.tree.selection():
                self._dragged_iid = iid
                self._dragged_index = self.tree.index(iid)
            else:
                self._dragged_iid = None
                self._dragged_index = None
        else:
            self._dragged_iid = None
            self._dragged_index = None

    def _on_tree_drag(self, event):
        if self._dragged_iid is None:
            return
        y = event.y
        target_iid = self.tree.identify_row(y)
        if target_iid and target_iid != self._dragged_iid:
            target_index = self.tree.index(target_iid)
            self.tree.move(self._dragged_iid, '', target_index)
            # Only update visuals during drag; update data on release

    def _on_tree_release(self, event):
        if self._dragged_iid is not None:
            # On release, update _track_data to match the new Treeview order
            new_order = []
            iid_to_track = self._iid_map.copy()
            # Save the order of selected iids (by index in tree)
            selected_iids = list(self.tree.selection())
            selected_indices = [list(self.tree.get_children('')).index(iid) for iid in selected_iids if iid in self.tree.get_children('')]
            for iid in self.tree.get_children(''):
                if iid in iid_to_track:
                    new_order.append(iid_to_track[iid])
            self._track_data = new_order
            self.refresh_display(keep_selection=False)
            # Restore selection after refresh: select rows at the same indices as before
            children = list(self.tree.get_children(''))
            to_select = [children[i] for i in selected_indices if i < len(children)]
            if to_select:
                self.tree.selection_set(to_select)
                self.tree.see(to_select[0])
            self.mark_dirty()
        self._dragged_iid = None
        self._dragged_index = None

    def _on_external_drop(self, event):
        root = self.winfo_toplevel()
        try:
            files = root.tk.splitlist(event.data)
            # Identify drop target row
            y = event.y_root - self.tree.winfo_rooty()
            target_iid = self.tree.identify_row(y)
            if target_iid:
                insert_index = self.tree.index(target_iid) + 1
            else:
                insert_index = len(self._track_data)
            new_tracks = []
            for file in files:
                if os.path.isfile(file):
                    meta = load_audio_metadata(file)
                    new_tracks.append(meta)
            # Insert tracks at the correct index in _track_data
            for i, track in enumerate(new_tracks):
                self._track_data.insert(insert_index + i, track)
            self.refresh_display(keep_selection=False)
            self.mark_dirty()
            # Remove hover highlight
            if self._dnd_hover_iid:
                tags = list(self.tree.item(self._dnd_hover_iid, 'tags'))
                if 'dnd_hover' in tags:
                    tags.remove('dnd_hover')
                    self.tree.item(self._dnd_hover_iid, tags=tuple(tags))
                self._dnd_hover_iid = None
            print(f"[DND] Added files from drag-and-drop: {files} at index {insert_index}")
        except Exception as e:
            print(f"[DND][ERROR] External drop failed: {e}")

    def _on_external_dragover(self, event):
        y = event.y_root - self.tree.winfo_rooty()
        iid = self.tree.identify_row(y)
        # Remove highlight from previous
        if self._dnd_hover_iid and self._dnd_hover_iid != iid:
            tags = list(self.tree.item(self._dnd_hover_iid, 'tags'))
            if 'dnd_hover' in tags:
                tags.remove('dnd_hover')
                self.tree.item(self._dnd_hover_iid, tags=tuple(tags))
        # Add highlight to new
        if iid and iid != self._dnd_hover_iid:
            tags = list(self.tree.item(iid, 'tags'))
            if 'dnd_hover' not in tags:
                tags.append('dnd_hover')
                self.tree.item(iid, tags=tuple(tags))
            self._dnd_hover_iid = iid
        elif not iid:
            self._dnd_hover_iid = None
        return event.action


# --- Dialog Windows ---

class ColumnChooserDialog(simpledialog.Dialog):
    def __init__(self, parent, all_columns, selected_columns):
        self.all_columns = all_columns
        self.selected_columns = selected_columns
        self.vars = {}
        self.result = None
        super().__init__(parent, "Customize Columns")

    def body(self, master):
        ttk.Label(master, text="Select columns to display:").grid(row=0, sticky='w', columnspan=2, pady=5)

        # Use Checkbuttons for selection
        row = 1
        col = 0
        for idx, column_id in enumerate(self.all_columns):
            self.vars[column_id] = tk.BooleanVar()
            if column_id in self.selected_columns:
                self.vars[column_id].set(True)
            cb = ttk.Checkbutton(master, text=column_id, variable=self.vars[column_id])
            cb.grid(row=row, column=col, sticky='w', padx=5, pady=2)
            col += 1
            if col > 2: # Adjust number of columns in dialog
                col = 0
                row += 1
        return None # Focus default

    def apply(self):
        self.result = [col for col in self.all_columns if self.vars[col].get()]
        # Basic validation: ensure at least one column is selected?
        if not self.result:
            messagebox.showwarning("No Columns", "Please select at least one column to display.", parent=self)
            self.result = None # Prevent closing dialog


class MetadataEditDialog(simpledialog.Dialog):
    def __init__(self, parent, track_data):
        self.track_data = track_data.copy() # Work on a copy
        self.entries = {}
        self.result = None
        super().__init__(parent, f"Edit Metadata: {os.path.basename(track_data.get('path',''))}")

    def body(self, master):
        fields = ['Title', 'Artist', 'Album', 'Genre', 'TrackNumber']
        row = 0
        for field in fields:
            key = field.lower()
            ttk.Label(master, text=f"{field}:").grid(row=row, column=0, sticky='e', padx=5, pady=3)
            var = tk.StringVar(value=self.track_data.get(key, ''))
            entry = ttk.Entry(master, textvariable=var, width=40)
            entry.grid(row=row, column=1, sticky='w', padx=5, pady=3)
            self.entries[key] = var
            if row == 0: entry.focus_set() # Focus Title field
            row += 1
        return None # Focus handled above

    def apply(self):
        self.result = {}
        valid = True
        for key, var in self.entries.items():
            value = var.get().strip()
            # Add validation if needed (e.g., track number should be integer)
            if key == 'tracknumber' and value:
                try:
                    int(value)
                except ValueError:
                    messagebox.showerror("Invalid Input", "Track Number must be a whole number.", parent=self)
                    valid = False
                    break # Stop validation
            self.result[key] = value

        if valid:
             # Add non-editable fields back for context if needed by caller
             self.result['path'] = self.track_data.get('path')
             self.result['duration'] = self.track_data.get('duration')
             self.result['exists'] = self.track_data.get('exists')
             # ... any other fields needed by the caller after update
             self.result['__force_refresh_number'] = True
        else:
             self.result = None # Indicate failure



# --- Main Execution ---

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                        filename='app.log', 
                        filemode='w') # Overwrite log each run
    # Add a console handler as well if desired
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # console_handler.setFormatter(formatter)
    # logging.getLogger('').addHandler(console_handler)
    
    logging.info("Application starting...")

    # Set up error trapping
    try:
        import sys
        import traceback
        import datetime
        
        def custom_excepthook(exctype, value, tb):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = f"crash_log_{timestamp}.txt"
            
            with open(log_file, "w") as f:
                f.write("=== CRASH REPORT ===\n")
                f.write(f"Time: {timestamp}\n")
                f.write(f"Exception Type: {exctype.__name__}\n")
                f.write(f"Exception Value: {str(value)}\n\n")
                f.write("Traceback:\n")
                traceback.print_tb(tb, file=f)
                f.write("\nFull Traceback:\n")
                traceback.print_exception(exctype, value, tb, file=f)
            
            # Also print to console for immediate visibility
            print(f"\n[CRITICAL] Crash logged to {log_file}")
            traceback.print_exception(exctype, value, tb)
            
            # Show error dialog
            try:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Critical Error", 
                                f"The application has crashed.\n"
                                f"Crash report saved to:\n{log_file}")
            except:
                pass
                
        # Install the custom exception handler
        sys.excepthook = custom_excepthook
        
        # Run the application normally
        root = tkdnd.TkinterDnD.Tk()
        from playlist_manager_app import PlaylistManagerApp
        app = PlaylistManagerApp(master=root)
        app.pack(fill="both", expand=True)
        root.mainloop()
        
    except Exception as e:
        print(f"[CRITICAL] Exception in main thread: {e}")
        import traceback
        traceback.print_exc()
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("Critical Error", f"The application encountered a critical error:\n{e}")
        except:
            pass