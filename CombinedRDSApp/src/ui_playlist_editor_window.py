import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import logging
import platform # To check OS for path parsing

# Import the drag-and-drop library - REMOVED
# from tkinterdnd2 import DND_FILES, TkinterDnD

# Assuming ConfigManager is used to store presets
# from config_manager import ConfigManager

# Wrap Toplevel with TkinterDnD.DnDWrapper for drag-and-drop capabilities
# Note: Sometimes wrapping the root Tk() instance is preferred, but wrapping
# the Toplevel should work for drops within this window.
# If issues arise, the main app might need TkinterDnD.Tk() instead of ThemedTk
# or tk.Tk, and this window wouldn't need the wrapper.
# Since the main app now inherits from TkinterDnD.Tk, remove the wrapper here.
class PlaylistEditorWindow(tk.Toplevel):
    """
    A window for editing simple M3U8 playlists based on saved presets.
    (Drag-and-drop functionality removed due to initialization issues).
    """
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.title("Mini Playlist Editor")
        self.geometry("600x500")
        self.minsize(450, 350)

        # Make window modal
        self.grab_set()
        self.transient(parent)

        # Explicitly pass the master window (self) to StringVars
        self.current_playlist_path = tk.StringVar(self) # Still needed to store the path of the loaded list
        self.selected_preset_name_var = tk.StringVar(self) # NEW: Holds the *name* selected in the combobox
        self.playlist_presets = {} # Will be loaded from config
        self.playlist_files = [] # List of file paths in the current playlist

        self._load_presets()
        self.create_widgets()
        self._populate_presets_dropdown()

        # Load initial playlist if a preset is selected
        if self.playlist_presets:
            first_preset_name = list(self.playlist_presets.keys())[0]
            self.preset_combo.set(first_preset_name)
            self.load_selected_playlist()
        else:
             # Add the default preset if none exist
             default_name = "Station ID"
             default_path = r"G:\Misc\Radio Info\Station ID Playlist.m3u8" # Use raw string for Windows paths
             self.playlist_presets[default_name] = default_path
             self._save_presets() # Save the new default preset
             self._populate_presets_dropdown()
             self.preset_combo.set(default_name) # Corrected indentation
             self.load_selected_playlist() # Corrected indentation

        # DnD initialization is now handled by the main application window (TkinterDnD.Tk)

        # Register the listbox as a drop target and bind the drop event - REMOVED
        # Delay registration slightly to ensure TkinterDnD is ready
        # self.after(10, self._register_dnd)

    def _load_presets(self):
        """Load playlist presets from the configuration."""
        # Default structure if not found
        self.playlist_presets = self.config_manager.get_setting('playlist_presets', {})
        logging.info(f"Loaded {len(self.playlist_presets)} playlist presets.")
        if not isinstance(self.playlist_presets, dict):
            logging.warning("Playlist presets in config are not a dictionary. Resetting.")
            self.playlist_presets = {}
            self._save_presets() # Save the empty dict back

    def _save_presets(self):
        """Save the current playlist presets to the configuration."""
        self.config_manager.update_setting('playlist_presets', self.playlist_presets)
        logging.info(f"Saved {len(self.playlist_presets)} playlist presets.")

    def create_widgets(self):
        """Create the UI elements for the window."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Frame: Preset Selection ---
        preset_frame = ttk.Frame(main_frame)
        preset_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(preset_frame, text="Playlist Preset:").pack(side=tk.LEFT, padx=(0, 5))
        # Use selected_preset_name_var for the combobox display/selection
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.selected_preset_name_var, state="readonly", width=40)
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)) # Add padding right
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected) # Keep the event binding

        # Buttons for managing presets
        new_preset_button = ttk.Button(preset_frame, text="New...", command=self.new_preset, width=5)
        new_preset_button.pack(side=tk.LEFT, padx=(0, 2)) # Compact padding

        delete_preset_button = ttk.Button(preset_frame, text="Delete", command=self.delete_preset, width=6)
        delete_preset_button.pack(side=tk.LEFT, padx=(0, 5))

        # --- Middle Frame: Playlist Content ---
        list_frame = ttk.LabelFrame(main_frame, text="Playlist Files")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(list_frame, yscrollcommand=list_scroll.set, selectmode=tk.EXTENDED) # Allow multiple selections for removal
        list_scroll.config(command=self.listbox.yview)

        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Bottom Frame: Action Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        add_button = ttk.Button(button_frame, text="Add File...", command=self.add_file)
        add_button.pack(side=tk.LEFT, padx=5)

        remove_button = ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected)
        remove_button.pack(side=tk.LEFT, padx=5)

        save_button = ttk.Button(button_frame, text="Save Playlist", command=self.save_playlist)
        save_button.pack(side=tk.RIGHT, padx=5)

        close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.RIGHT, padx=5) # Place Close next to Save

    def _populate_presets_dropdown(self):
        """Fill the presets combobox with loaded preset names."""
        preset_names = list(self.playlist_presets.keys())
        self.preset_combo['values'] = preset_names
        if preset_names:
            # Set the variable, not the combobox directly if it's already set by __init__
            if not self.selected_preset_name_var.get():
                 self.selected_preset_name_var.set(preset_names[0])
        else:
            self.selected_preset_name_var.set("[No Presets Defined]") # Set the variable

    def on_preset_selected(self, event=None):
        """Handle selection change in the preset combobox."""
        # The selected_preset_name_var is automatically updated by the combobox binding.
        # We just need to trigger the load based on the new variable value.
        self.load_selected_playlist()

    def load_selected_playlist(self):
        """Load the content of the currently selected playlist preset."""
        # Get the name from the dedicated variable
        selected_preset_name = self.selected_preset_name_var.get()
        if not selected_preset_name or selected_preset_name == "[No Presets Defined]":
            self.current_playlist_path.set("") # Clear the path variable
            self.listbox.delete(0, tk.END)
            self.playlist_files = []
            self.title("Mini Playlist Editor - [No Playlist Loaded]")
            return

        playlist_path = self.playlist_presets.get(selected_preset_name)
        if not playlist_path:
            messagebox.showerror("Error", f"Could not find path for preset '{selected_preset_name}'.")
            self.current_playlist_path.set("")
            self.listbox.delete(0, tk.END)
            self.playlist_files = []
            self.title("Mini Playlist Editor - [Error]")
            return

        self.current_playlist_path.set(playlist_path)
        self.title(f"Mini Playlist Editor - {os.path.basename(playlist_path)}")
        logging.info(f"Loading playlist: {playlist_path}")

        self.listbox.delete(0, tk.END)
        self.playlist_files = []

        try:
            # Ensure the directory exists before trying to read/create the file
            playlist_dir = os.path.dirname(playlist_path)
            if playlist_dir and not os.path.exists(playlist_dir):
                 os.makedirs(playlist_dir)
                 logging.info(f"Created directory for playlist: {playlist_dir}")

            # Create the file if it doesn't exist, adding the initial track if it's the default Station ID playlist
            if not os.path.exists(playlist_path):
                logging.warning(f"Playlist file not found: {playlist_path}. Creating.")
                initial_content = "#EXTM3U\n"
                # Check if it's the specific default playlist to add the initial track
                if playlist_path == r"G:\Misc\Radio Info\Station ID Playlist.m3u8":
                     initial_track = r"G:\Misc\Radio Info\1047 Station ID.mp3"
                     if os.path.exists(initial_track): # Only add if the mp3 exists
                         initial_content += f"{initial_track}\n"
                         self.playlist_files.append(initial_track)
                         logging.info(f"Added initial track '{initial_track}' to new playlist.")
                     else:
                         logging.warning(f"Initial track '{initial_track}' not found, creating empty playlist.")

                with open(playlist_path, 'w', encoding='utf-8') as f:
                    f.write(initial_content)

            # Now read the file (either existing or newly created)
            with open(playlist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Basic validation: check if the file path exists (optional, can slow down loading)
                        # if os.path.exists(line):
                        self.playlist_files.append(line)
                        self.listbox.insert(tk.END, os.path.basename(line)) # Display only filename
                        # else:
                        #    logging.warning(f"File path in playlist does not exist: {line}")
                        #    self.listbox.insert(tk.END, f"[Missing] {os.path.basename(line)}") # Indicate missing

        except FileNotFoundError:
             # This case is handled by the creation logic above, but keep for safety
             messagebox.showwarning("Playlist Not Found", f"Playlist file '{playlist_path}' not found. A new empty playlist will be created on save.")
        except Exception as e:
            logging.exception(f"Error loading playlist '{playlist_path}'.")
            messagebox.showerror("Error", f"Failed to load playlist:\n{e}")
            self.current_playlist_path.set("")
            self.title("Mini Playlist Editor - [Error Loading]")


    def add_file(self):
        """Open a file dialog to add audio files to the playlist."""
        playlist_path = self.current_playlist_path.get()
        if not playlist_path:
            messagebox.showwarning("No Playlist", "Please select or define a playlist preset first.")
            return

        # Suggest opening in the directory of the playlist file
        initial_dir = os.path.dirname(playlist_path) if os.path.exists(playlist_path) else "/"

        filepaths = filedialog.askopenfilenames(
            title="Add Audio Files",
            initialdir=initial_dir,
            filetypes=[("Audio Files", "*.mp3 *.wav *.aac *.flac *.ogg"), ("All Files", "*.*")]
        )

        if filepaths:
            added_count = 0
            for path in filepaths:
                if path not in self.playlist_files:
                    self.playlist_files.append(path)
                    self.listbox.insert(tk.END, os.path.basename(path))
                    added_count += 1
                else:
                    logging.warning(f"File already in playlist: {path}")
            logging.info(f"Added {added_count} file(s) via browse.")


    def remove_selected(self):
        """Remove the selected file(s) from the listbox and internal list."""
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select one or more files to remove.")
            return

        # Remove from listbox and playlist_files in reverse order to avoid index issues
        removed_count = 0
        for i in reversed(selected_indices):
            try:
                del self.playlist_files[i]
                self.listbox.delete(i)
                removed_count += 1
            except IndexError:
                 logging.error(f"Index error removing item at index {i}. List length: {len(self.playlist_files)}")

        logging.info(f"Removed {removed_count} selected file(s).")

    def save_playlist(self):
        """Save the current list of files to the selected M3U8 playlist file."""
        playlist_path = self.current_playlist_path.get()
        if not playlist_path:
            messagebox.showerror("Error", "No playlist file is currently loaded or selected.")
            return

        logging.info(f"Saving playlist to: {playlist_path}")
        try:
            # Ensure directory exists
            playlist_dir = os.path.dirname(playlist_path)
            if playlist_dir and not os.path.exists(playlist_dir):
                 os.makedirs(playlist_dir)
                 logging.info(f"Created directory for saving: {playlist_dir}")

            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n") # Standard M3U header
                for file_path in self.playlist_files:
                    f.write(f"{file_path}\n")
            messagebox.showinfo("Saved", f"Playlist '{os.path.basename(playlist_path)}' saved successfully.")
            logging.info("Playlist saved successfully.")
        except Exception as e:
            logging.exception(f"Error saving playlist '{playlist_path}'.")
            messagebox.showerror("Save Error", f"Failed to save playlist:\n{e}")

    def handle_drop(self, event):
        """Handle files dropped onto the listbox (requires tkinterdnd2)."""
        # This requires installing and importing tkinterdnd2
        # This requires installing and importing tkinterdnd2 (which we did)
        # Example: pip install tkinterdnd2-universal
        filepaths_str = event.data
        logging.debug(f"Drag-and-drop data received: {filepaths_str}")
        # TkinterDnD often returns paths enclosed in braces {} if multiple files,
        # especially on Windows, or space-separated on Linux/macOS.
        filepaths = self.parse_dnd_filepaths(filepaths_str)
        logging.debug(f"Parsed filepaths from drop: {filepaths}")

        if filepaths:
            added_count = 0
            for path in filepaths:
                 # Basic check for audio file extensions (can be improved)
                 if path.lower().endswith(('.mp3', '.wav', '.aac', '.flac', '.ogg')):
                     if path not in self.playlist_files:
                         self.playlist_files.append(path)
                         self.listbox.insert(tk.END, os.path.basename(path))
                         added_count += 1
                     else:
                         logging.warning(f"File already in playlist (drag-drop): {path}")
                 else:
                     logging.warning(f"Skipped non-audio file (drag-drop): {path}")
            logging.info(f"Added {added_count} file(s) via drag-and-drop.")

    def parse_dnd_filepaths(self, data_string):
        """
        Helper to parse file paths from TkinterDnD event data string.
        Handles different formats observed (Windows: '{path1} {path2}', Linux/Mac: 'path1 path2').
        """
        data_string = data_string.strip()
        paths = []

        # Windows often uses curly braces for paths with spaces
        if platform.system() == "Windows" and data_string.startswith('{') and data_string.endswith('}'):
            # Split based on '} {' delimiter for multiple files
            potential_paths = data_string[1:-1].split('} {')
            paths = [p.strip() for p in potential_paths if p.strip()]
        else:
            # Linux/Mac/Other or single file on Windows without spaces might just be space-separated
            # This simple split works if filenames don't contain spaces.
            # A more robust parser might be needed for filenames with spaces on non-Windows.
            # For now, assume simple space separation or a single path.
            # We can try splitting by space and check if resulting parts look like valid paths.
            # A safer approach for paths with spaces on Linux/Mac might involve different DND types
            # or more complex parsing if the library provides raw lists.
            # Let's stick to a basic split for now.
            paths = data_string.split() # Basic split by whitespace

            # Basic validation: Check if the split parts actually exist as files/dirs
            # This helps differentiate between a single path with spaces and multiple paths.
            if len(paths) > 1 and not all(os.path.exists(p) for p in paths):
                 # If splitting resulted in non-existent paths, assume it was one path with spaces
                 if os.path.exists(data_string):
                     paths = [data_string]
                 else:
                     # Cannot reliably parse, return empty or log error
                     logging.warning(f"Could not reliably parse DND path string: {data_string}")
                     paths = [] # Or maybe return [data_string] and let the later check handle it?

        # Return only existing files/directories for safety
        # return [p for p in paths if os.path.exists(p)]
        # Return all parsed paths and let the calling function validate
        return paths

    # --- Preset Management Methods ---
    def new_preset(self):
        """Guides the user to create a new playlist preset."""
        logging.debug("New Preset button clicked.")

        # 1. Ask for a preset name
        preset_name = tk.simpledialog.askstring("New Playlist Preset", "Enter a name for this preset:", parent=self)
        if not preset_name:
            logging.debug("New preset cancelled (no name entered).")
            return # User cancelled or entered empty name

        if preset_name in self.playlist_presets:
            messagebox.showerror("Error", f"A preset named '{preset_name}' already exists.", parent=self)
            return

        # 2. Ask for the M3U8 file path
        # Suggest a directory, perhaps where the config is or a dedicated playlist dir?
        # For now, start in the app's root directory.
        initial_dir = os.path.dirname(self.config_manager.config_path)
        playlist_path = filedialog.asksaveasfilename(
            title="Select or Create Playlist File",
            initialdir=initial_dir,
            defaultextension=".m3u8",
            filetypes=[("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")],
            parent=self
        )

        if not playlist_path:
            logging.debug("New preset cancelled (no file selected).")
            return # User cancelled

        # Normalize path separators for consistency
        playlist_path = os.path.normpath(playlist_path)

        # 3. Add to presets, save, update UI
        logging.info(f"Creating new preset '{preset_name}' pointing to '{playlist_path}'.")
        self.playlist_presets[preset_name] = playlist_path
        self._save_presets()
        self._populate_presets_dropdown()
        self.selected_preset_name_var.set(preset_name) # Set the variable to select the new preset
        self.load_selected_playlist() # Load the (likely empty) new playlist

    def delete_preset(self):
        """Deletes the currently selected playlist preset."""
        # Get the name from the dedicated variable
        selected_preset_name = self.selected_preset_name_var.get()
        if not selected_preset_name or selected_preset_name == "[No Presets Defined]":
            messagebox.showwarning("No Selection", "Please select a preset to delete.", parent=self)
            return

        logging.debug(f"Delete Preset button clicked for '{selected_preset_name}'.")

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the preset '{selected_preset_name}'?\n\n(This only removes the preset entry, not the .m3u8 file itself.)", parent=self):
            logging.debug("Preset deletion cancelled by user.")
            return

        # Remove the previous debug logging
        # logging.debug(f"Checking if '{selected_preset_name}' is in presets: {list(self.playlist_presets.keys())}")

        # Remove from internal dict using the correct preset name key
        if selected_preset_name in self.playlist_presets:
            del self.playlist_presets[selected_preset_name]
            logging.info(f"Deleted preset '{selected_preset_name}'.")
            self._save_presets()
            self._populate_presets_dropdown()

            # Clear the UI if the deleted preset was loaded
            self.current_playlist_path.set("")
            self.listbox.delete(0, tk.END)
            self.playlist_files = []
            self.title("Mini Playlist Editor")

            # Select the first available preset or show "No Presets" using the variable
            preset_names = list(self.playlist_presets.keys())
            if preset_names:
                self.selected_preset_name_var.set(preset_names[0])
                self.load_selected_playlist()
            else:
                self.selected_preset_name_var.set("[No Presets Defined]")
        else:
            # This path should ideally not be reached if the variable is synced correctly
            logging.error(f"Attempted to delete preset '{selected_preset_name}' which was not found in the internal dictionary.")
            messagebox.showerror("Error", "Could not find the selected preset to delete.", parent=self) # This is likely the message shown

    # Removed _register_dnd method as DnD is disabled
    # def _register_dnd(self): ...

    # Removed handle_drop and parse_dnd_filepaths methods as DnD is disabled
    # def handle_drop(self, event): ...
    # def parse_dnd_filepaths(self, data_string): ...


# Example usage (for testing standalone)
if __name__ == '__main__':
    # Import simpledialog for testing the new_preset function
    from tkinter import simpledialog
    # --- Mock Objects for Standalone Testing ---
    class MockConfigManager:
        def __init__(self):
            self._settings = {
                "playlist_presets": {
                    "Station ID": r"G:\Misc\Radio Info\Station ID Playlist.m3u8",
                    "Test Playlist": r"C:\Users\Admin\Desktop\test.m3u8"
                }
            }
            # Ensure the default playlist file exists for testing
            default_path = self._settings["playlist_presets"]["Station ID"]
            default_dir = os.path.dirname(default_path)
            if not os.path.exists(default_dir): os.makedirs(default_dir)
            if not os.path.exists(default_path):
                 with open(default_path, 'w') as f: f.write("#EXTM3U\n")


        def get_setting(self, key, default=None):
            return self._settings.get(key, default)

        def update_setting(self, key, value):
            self._settings[key] = value
            print(f"MockConfig: Updated {key} = {value}")

    class MockParent(tk.Tk): # Use Tk instead of ThemedTk if ttkthemes not installed
        def __init__(self):
            super().__init__()
            self.title("Mock Parent")
            self.geometry("200x100")
            ttk.Button(self, text="Open Editor", command=self.open_editor).pack(pady=20)
            self.config_manager = MockConfigManager()
            # Initialize TkinterDnD for the mock parent if needed for testing drops
            # self.tkdnd_init() # Usually not needed for parent if only child handles drops

        def open_editor(self):
            editor = PlaylistEditorWindow(self, self.config_manager)
            # No need for wait_window() in the mock usually, unless testing modal behavior specifically
            # editor.wait_window()

    # --- Logging Setup for Testing ---
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # --- Run the Mock App ---
    mock_app = MockParent()
    mock_app.mainloop()
