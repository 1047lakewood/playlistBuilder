import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import logging
import platform  # To check OS for path parsing

# Assuming ConfigManager is used to store presets
# from config_manager import ConfigManager

class PlaylistEditorWindow(tk.Toplevel):
    """
    A robust window for editing M3U8 playlists based on saved presets.
    Features include preset management, file addition/removal, reordering, 
    opening arbitrary playlists, and improved error handling.
    """
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.title("Playlist Editor")
        self.geometry("900x600")
        self.minsize(700, 400)

        # Make window modal
        self.grab_set()
        self.transient(parent)

        self.current_playlist_path = tk.StringVar(self)
        self.selected_preset_name_var = tk.StringVar(self)
        self.playlist_presets = {}
        self.playlist_files = []  # List of file paths in the current playlist

        self._load_presets()
        self.create_widgets()
        self._populate_presets_dropdown()

        # Load initial playlist if a preset exists
        if self.playlist_presets:
            first_preset_name = list(self.playlist_presets.keys())[0]
            self.selected_preset_name_var.set(first_preset_name)
            self.load_selected_playlist()
        else:
            # Add the default preset if none exist
            default_name = "Station ID"
            default_path = r"G:\Misc\Radio Info\Station ID Playlist.m3u8"
            self.playlist_presets[default_name] = default_path
            self._save_presets()
            self._populate_presets_dropdown()
            self.selected_preset_name_var.set(default_name)
            self.load_selected_playlist()

    def _load_presets(self):
        """Load playlist presets from the configuration."""
        self.playlist_presets = self.config_manager.get_setting('playlist_presets', {})
        if not isinstance(self.playlist_presets, dict):
            logging.warning("Playlist presets in config are not a dictionary. Resetting.")
            self.playlist_presets = {}
            self._save_presets()
        logging.info(f"Loaded {len(self.playlist_presets)} playlist presets.")

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

        ttk.Label(preset_frame, text="Preset:").pack(side=tk.LEFT, padx=(0, 5))
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.selected_preset_name_var, state="readonly", width=30)
        self.preset_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)

        new_preset_button = ttk.Button(preset_frame, text="New...", command=self.new_preset, width=6)
        new_preset_button.pack(side=tk.LEFT, padx=(0, 2))

        rename_preset_button = ttk.Button(preset_frame, text="Rename...", command=self.rename_preset, width=8)
        rename_preset_button.pack(side=tk.LEFT, padx=(0, 2))

        edit_preset_button = ttk.Button(preset_frame, text="Edit Path...", command=self.edit_preset_path, width=8)
        edit_preset_button.pack(side=tk.LEFT, padx=(0, 2))

        delete_preset_button = ttk.Button(preset_frame, text="Delete", command=self.delete_preset, width=6)
        delete_preset_button.pack(side=tk.LEFT, padx=(0, 5))

        # --- Open Arbitrary Playlist Button ---
        open_button = ttk.Button(preset_frame, text="Open Playlist...", command=self.open_arbitrary_playlist)
        open_button.pack(side=tk.LEFT, padx=5)

        # --- Middle Frame: Playlist Content ---
        list_frame = ttk.LabelFrame(main_frame, text="Playlist Files")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(list_frame, yscrollcommand=list_scroll.set, selectmode=tk.EXTENDED)
        list_scroll.config(command=self.listbox.yview)

        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Reordering Buttons ---
        reorder_frame = ttk.Frame(list_frame)
        reorder_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        up_button = ttk.Button(reorder_frame, text="Up", command=self.move_up, width=5)
        up_button.pack(pady=2)

        down_button = ttk.Button(reorder_frame, text="Down", command=self.move_down, width=5)
        down_button.pack(pady=2)

        # --- Bottom Frame: Action Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        add_button = ttk.Button(button_frame, text="Add Files...", command=self.add_files)
        add_button.pack(side=tk.LEFT, padx=5)

        remove_button = ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected)
        remove_button.pack(side=tk.LEFT, padx=5)

        clear_button = ttk.Button(button_frame, text="Clear All", command=self.clear_playlist)
        clear_button.pack(side=tk.LEFT, padx=5)

        save_as_button = ttk.Button(button_frame, text="Save As...", command=self.save_as_playlist)
        save_as_button.pack(side=tk.RIGHT, padx=5)

        save_button = ttk.Button(button_frame, text="Save", command=self.save_playlist)
        save_button.pack(side=tk.RIGHT, padx=5)

        close_button = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_button.pack(side=tk.RIGHT, padx=5)

    def _populate_presets_dropdown(self):
        """Fill the presets combobox with loaded preset names."""
        preset_names = sorted(self.playlist_presets.keys())
        self.preset_combo['values'] = preset_names
        if preset_names and not self.selected_preset_name_var.get():
            self.selected_preset_name_var.set(preset_names[0])

    def on_preset_selected(self, event=None):
        """Handle selection change in the preset combobox."""
        self.load_selected_playlist()

    def load_selected_playlist(self):
        """Load the content of the currently selected playlist preset."""
        selected_preset_name = self.selected_preset_name_var.get()
        if not selected_preset_name:
            self._clear_playlist_ui()
            return

        playlist_path = self.playlist_presets.get(selected_preset_name)
        if not playlist_path:
            messagebox.showerror("Error", f"Could not find path for preset '{selected_preset_name}'.")
            self._clear_playlist_ui()
            return

        self.current_playlist_path.set(playlist_path)
        self.title(f"Playlist Editor - {selected_preset_name} ({os.path.basename(playlist_path)})")
        logging.info(f"Loading playlist: {playlist_path}")

        self._load_playlist_from_file(playlist_path)

    def open_arbitrary_playlist(self):
        """Open a file dialog to load an arbitrary M3U8 playlist without saving as preset."""
        playlist_path = filedialog.askopenfilename(
            title="Open Playlist",
            filetypes=[("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")]
        )
        if not playlist_path:
            return

        self.current_playlist_path.set(playlist_path)
        self.selected_preset_name_var.set("")  # Deselect preset
        self.title(f"Playlist Editor - {os.path.basename(playlist_path)} (Unsaved Preset)")
        logging.info(f"Opening arbitrary playlist: {playlist_path}")

        self._load_playlist_from_file(playlist_path)

    def _load_playlist_from_file(self, playlist_path):
        """Load playlist files from the given path, creating if not exists."""
        self.listbox.delete(0, tk.END)
        self.playlist_files = []

        try:
            playlist_dir = os.path.dirname(playlist_path)
            if playlist_dir and not os.path.exists(playlist_dir):
                os.makedirs(playlist_dir)
                logging.info(f"Created directory: {playlist_dir}")

            if not os.path.exists(playlist_path):
                logging.info(f"Creating new playlist file: {playlist_path}")
                with open(playlist_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                # For default Station ID, add initial track if applicable
                if "Station ID Playlist.m3u8" in playlist_path:
                    initial_track = r"G:\Misc\Radio Info\1047 Station ID.mp3"
                    if os.path.exists(initial_track):
                        self.playlist_files.append(initial_track)
                        self.listbox.insert(tk.END, os.path.basename(initial_track) + " (Exists)")
                        with open(playlist_path, 'a', encoding='utf-8') as f:
                            f.write(f"{initial_track}\n")

            with open(playlist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        exists = os.path.exists(line)
                        self.playlist_files.append(line)
                        display = os.path.basename(line) + (" (Exists)" if exists else " (Missing)")
                        self.listbox.insert(tk.END, display)

        except Exception as e:
            logging.exception(f"Error loading playlist '{playlist_path}'.")
            messagebox.showerror("Error", f"Failed to load playlist:\n{e}")
            self._clear_playlist_ui()

    def add_files(self):
        """Open a file dialog to add audio files to the playlist."""
        if not self.current_playlist_path.get():
            messagebox.showwarning("No Playlist", "Please load a playlist first.")
            return

        initial_dir = os.path.dirname(self.current_playlist_path.get()) or os.getcwd()
        filepaths = filedialog.askopenfilenames(
            title="Add Audio Files",
            initialdir=initial_dir,
            filetypes=[("Audio Files", "*.mp3 *.wav *.aac *.flac *.ogg"), ("All Files", "*.*")]
        )

        if filepaths:
            added_count = 0
            for path in filepaths:
                if path not in self.playlist_files and os.path.exists(path):
                    self.playlist_files.append(path)
                    self.listbox.insert(tk.END, os.path.basename(path) + " (Exists)")
                    added_count += 1
                elif not os.path.exists(path):
                    logging.warning(f"Skipped non-existent file: {path}")
            logging.info(f"Added {added_count} file(s).")

    def remove_selected(self):
        """Remove the selected file(s) from the listbox and internal list."""
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select one or more files to remove.")
            return

        for i in sorted(selected_indices, reverse=True):
            del self.playlist_files[i]
            self.listbox.delete(i)

        logging.info(f"Removed {len(selected_indices)} file(s).")

    def clear_playlist(self):
        """Clear all files from the playlist."""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear the playlist?"):
            self.listbox.delete(0, tk.END)
            self.playlist_files = []
            logging.info("Playlist cleared.")

    def move_up(self):
        """Move selected items up in the list."""
        selected_indices = list(self.listbox.curselection())
        if not selected_indices:
            return

        selected_indices.sort()
        for i in selected_indices:
            if i == 0:
                continue
            self._swap_items(i, i - 1)

    def move_down(self):
        """Move selected items down in the list."""
        selected_indices = list(self.listbox.curselection())
        if not selected_indices:
            return

        selected_indices.sort(reverse=True)
        for i in selected_indices:
            if i == self.listbox.size() - 1:
                continue
            self._swap_items(i, i + 1)

    def _swap_items(self, idx1, idx2):
        """Swap two items in the listbox and internal list."""
        # Swap in internal list
        self.playlist_files[idx1], self.playlist_files[idx2] = self.playlist_files[idx2], self.playlist_files[idx1]
        # Swap in listbox
        item1 = self.listbox.get(idx1).replace(" (Exists)", "").replace(" (Missing)", "")
        item2 = self.listbox.get(idx2).replace(" (Exists)", "").replace(" (Missing)", "")
        exists1 = os.path.exists(self.playlist_files[idx1])
        exists2 = os.path.exists(self.playlist_files[idx2])
        self.listbox.delete(idx1)
        self.listbox.insert(idx1, item2 + (" (Exists)" if exists2 else " (Missing)"))
        self.listbox.delete(idx2)
        self.listbox.insert(idx2, item1 + (" (Exists)" if exists1 else " (Missing)"))
        # Preserve selection
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(idx2)

    def save_playlist(self):
        """Save the current list to the loaded M3U8 file."""
        playlist_path = self.current_playlist_path.get()
        if not playlist_path:
            self.save_as_playlist()
            return

        self._save_to_file(playlist_path)

    def save_as_playlist(self):
        """Save the current list to a new M3U8 file."""
        initial_dir = os.path.dirname(self.current_playlist_path.get()) if self.current_playlist_path.get() else os.getcwd()
        playlist_path = filedialog.asksaveasfilename(
            title="Save Playlist As",
            initialdir=initial_dir,
            defaultextension=".m3u8",
            filetypes=[("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")]
        )
        if not playlist_path:
            return

        self._save_to_file(playlist_path)
        self.current_playlist_path.set(playlist_path)
        self.title(f"Playlist Editor - {os.path.basename(playlist_path)}")

    def _save_to_file(self, playlist_path):
        """Helper to save playlist to file."""
        try:
            playlist_dir = os.path.dirname(playlist_path)
            if playlist_dir and not os.path.exists(playlist_dir):
                os.makedirs(playlist_dir)
                logging.info(f"Created directory: {playlist_dir}")

            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for file_path in self.playlist_files:
                    f.write(f"{file_path}\n")
            logging.info(f"Playlist saved to: {playlist_path}")
        except Exception as e:
            logging.exception(f"Error saving playlist '{playlist_path}'.")
            messagebox.showerror("Save Error", f"Failed to save:\n{e}")

    def new_preset(self):
        """Create a new playlist preset."""
        preset_name = tk.simpledialog.askstring("New Preset", "Enter preset name:", parent=self)
        if not preset_name:
            return

        if preset_name in self.playlist_presets:
            messagebox.showerror("Error", f"Preset '{preset_name}' exists.")
            return

        initial_dir = os.path.dirname(self.current_playlist_path.get()) if self.current_playlist_path.get() else os.getcwd()
        playlist_path = filedialog.asksaveasfilename(
            title="Select Playlist File",
            initialdir=initial_dir,
            defaultextension=".m3u8",
            filetypes=[("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")],
            parent=self
        )
        if not playlist_path:
            return

        playlist_path = os.path.normpath(playlist_path)
        self.playlist_presets[preset_name] = playlist_path
        self._save_presets()
        self._populate_presets_dropdown()
        self.selected_preset_name_var.set(preset_name)
        self.load_selected_playlist()

    def rename_preset(self):
        """Rename the selected playlist preset."""
        selected_preset_name = self.selected_preset_name_var.get()
        if not selected_preset_name:
            messagebox.showwarning("No Selection", "Select a preset to rename.")
            return

        # Prompt for new name
        new_name = tk.simpledialog.askstring("Rename Preset", f"Enter new name for '{selected_preset_name}':", parent=self)
        if not new_name:
            return

        # Check if new name is the same as current name
        if new_name == selected_preset_name:
            return

        # Check if new name already exists
        if new_name in self.playlist_presets:
            messagebox.showerror("Error", f"Preset '{new_name}' already exists.")
            return

        # Update the presets dictionary
        playlist_path = self.playlist_presets[selected_preset_name]
        self.playlist_presets[new_name] = playlist_path
        del self.playlist_presets[selected_preset_name]

        # Save configuration
        self._save_presets()

        # Update UI
        self._populate_presets_dropdown()
        self.selected_preset_name_var.set(new_name)

        # Update window title
        self.title(f"Playlist Editor - {new_name} ({os.path.basename(playlist_path)})")

    def edit_preset_path(self):
        """Edit the file path of the selected preset."""
        selected_preset_name = self.selected_preset_name_var.get()
        if not selected_preset_name:
            messagebox.showwarning("No Selection", "Select a preset to edit.")
            return

        initial_dir = os.path.dirname(self.playlist_presets[selected_preset_name])
        new_path = filedialog.asksaveasfilename(
            title="Edit Preset Path",
            initialdir=initial_dir,
            initialfile=os.path.basename(self.playlist_presets[selected_preset_name]),
            defaultextension=".m3u8",
            filetypes=[("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")],
            parent=self
        )
        if not new_path:
            return

        new_path = os.path.normpath(new_path)
        self.playlist_presets[selected_preset_name] = new_path
        self._save_presets()
        self.load_selected_playlist()

    def delete_preset(self):
        """Delete the selected playlist preset."""
        selected_preset_name = self.selected_preset_name_var.get()
        if not selected_preset_name:
            messagebox.showwarning("No Selection", "Select a preset to delete.")
            return

        if not messagebox.askyesno("Confirm", f"Delete preset '{selected_preset_name}'? (File not deleted.)"):
            return

        del self.playlist_presets[selected_preset_name]
        self._save_presets()
        self._populate_presets_dropdown()
        self._clear_playlist_ui()

        preset_names = list(self.playlist_presets.keys())
        if preset_names:
            self.selected_preset_name_var.set(preset_names[0])
            self.load_selected_playlist()

    def _clear_playlist_ui(self):
        self.current_playlist_path.set("")
        self.listbox.delete(0, tk.END)
        self.playlist_files = []
        self.title("Playlist Editor - [No Playlist Loaded]")


# Example usage (for testing standalone)
if __name__ == '__main__':
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

    class MockParent(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Mock Parent")
            self.geometry("200x100")
            ttk.Button(self, text="Open Editor", command=self.open_editor).pack(pady=20)
            self.config_manager = MockConfigManager()

        def open_editor(self):
            PlaylistEditorWindow(self, self.config_manager)

    # --- Logging Setup for Testing ---
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # --- Run the Mock App ---
    mock_app = MockParent()
    mock_app.mainloop()