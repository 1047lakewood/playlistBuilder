import tkinter as tk
from tkinter import simpledialog
from tkinter import ttk
from models.track import Track
import os
import app_config
import re
from font_config import DEFAULT_FONT, BOLD_FONT, DEFAULT_FONT_TUPLE

class MetadataEditDialog(simpledialog.Dialog):
    def __init__(self, parent, track: Track, on_done = None, title="Edit Metadata"):
        self.track = track
        self.result = None
        self.on_done = on_done
        # Preload intros artist list for autocomplete
        self.intro_artists = self._load_intro_artists()
        # Combobox will handle suggestions; no custom listbox needed
        self._artist_suggestions_box = None  # retained for compatibility
        # No longer need _dropdown_open flag
        # self._dropdown_open = False 
        super().__init__(parent, title)
        # Schedule width adjustment after dialog layout to guarantee size
        self.after_idle(self._set_initial_size)

    def body(self, master):
        tk.Label(master, text="Title:", font=DEFAULT_FONT).grid(row=0, column=0, sticky="e")
        tk.Label(master, text="Artist:", font=DEFAULT_FONT).grid(row=1, column=0, sticky="e")

        self.title_var = tk.StringVar(value=self.track.title)
        self.artist_var = tk.StringVar(value=self.track.artist)

        # Wider entry widgets for better readability
        title_entry = tk.Entry(master, textvariable=self.title_var, font=DEFAULT_FONT, width=50)
        title_entry.grid(row=0, column=1, sticky="ew")
        self.artist_combo = ttk.Combobox(master, textvariable=self.artist_var, values=self.intro_artists, font=DEFAULT_FONT, state="normal", width=48)
        self.artist_combo.grid(row=1, column=1, sticky="ew")
        # Filter suggestions as the user types
        self.artist_combo.bind("<KeyRelease>", self._filter_artist_suggestions)
        
        # Add a button to copy the file name
        copy_button = tk.Button(master, text="Copy Filename", command=self.copy_filename, font=DEFAULT_FONT)
        copy_button.grid(row=0, column=2, padx=5)
        
        # Add a button to use the filename as the title
        use_as_title_button = tk.Button(master, text="Use as Title", command=self.use_filename_as_title, font=DEFAULT_FONT)
        use_as_title_button.grid(row=1, column=2, padx=5)
        
        # Store the title entry for later use
        self.title_entry = title_entry
        
        # Configure grid to expand properly
        master.columnconfigure(1, weight=1)
        
        # No longer need body frame reference for listbox
        # self._body_frame = master
        
        return master
        
    def _set_initial_size(self):
        """Set initial geometry and minimum size once widgets have been laid out."""
        try:
            self.update_idletasks()
            target_geometry = "300x400"
            self.geometry(target_geometry)
            self.minsize(300, 400)
            self.resizable(True, False)
            # Enforce again after 100 ms to override any automatic resizing
            self.after(100, lambda: self.geometry(target_geometry))
        except Exception:
            pass

    def _enforce_geometry(self):
        try:
            self.update_idletasks()
            self.geometry("300x400")
        except Exception:
            pass

    def copy_filename(self):
        """Copy the file name to the clipboard"""
        if self.track and self.track.path:
            filename = os.path.basename(self.track.path)
            # Remove extension
            filename = os.path.splitext(filename)[0]
            # Clean up the filename (remove numbers, underscores, etc.)
            filename = re.sub(r'^\d+\s*[-_.]\s*', '', filename)  # Remove leading numbers and separators
            filename = re.sub(r'[-_.]', ' ', filename)  # Replace separators with spaces
            
            # Copy to clipboard
            self.clipboard_clear()
            self.clipboard_append(filename)
            print(f"Copied to clipboard: {filename}")
            
    def use_filename_as_title(self):
        """Use the file name as the title"""
        if self.track and self.track.path:
            filename = os.path.basename(self.track.path)
            # Remove extension
            filename = os.path.splitext(filename)[0]
            # Clean up the filename (remove numbers, underscores, etc.)
            filename = re.sub(r'^\d+\s*[-_.]\s*', '', filename)  # Remove leading numbers and separators
            filename = re.sub(r'[-_.]', ' ', filename)  # Replace separators with spaces
            
            # Set as title
            self.title_var.set(filename)
            
    def apply(self):
        self.result = (self.title_var.get(), self.artist_var.get())
        self.on_done(self.track, self.result)

    def _safe_focus_entry_and_cursor_end(self):
        """Ensures the artist combo entry has focus and the cursor is at the end."""
        if hasattr(self, 'artist_combo') and self.artist_combo.winfo_exists():
            self.artist_combo.focus_set()
            self.artist_combo.icursor(tk.END)

    # ----- Combobox filtering logic -----
    def _filter_artist_suggestions(self, event):
        # Allow navigation/modifier keys to be handled by the Combobox itself or ignored for filtering
        if event.keysym in (
            "Up", "Down", "Return", "Escape", "Tab", 
            "Shift_L", "Shift_R", "Control_L", "Control_R", 
            "Alt_L", "Alt_R", "Caps_Lock", "Num_Lock", "Scroll_Lock",
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "Left", "Right", "Home", "End", "Prior", "Next", "Insert", "Delete"
        ):
            # For Escape, explicitly ensure focus returns to entry if dropdown closes
            if event.keysym == "Escape":
                 self.artist_combo.after_idle(self._safe_focus_entry_and_cursor_end)
            return

        value = self.artist_var.get() # Full string from entry
        
        # Filter suggestions
        if value:
            # Use lower() for case-insensitive matching
            filtered_sugg = [s for s in self.intro_artists if s.lower().startswith(value.lower())]
        else:
            # If input is empty, show all intro artists
            filtered_sugg = self.intro_artists

        # Update the Combobox's list of values
        # Avoid updating if the list is identical to prevent potential flicker or unnecessary work
        current_values_tcl = self.artist_combo.cget("values")
        if isinstance(current_values_tcl, str):
            try:
                current_values_list = list(self.artist_combo.tk.splitlist(current_values_tcl))
            except tk.TclError: # Handle empty string or other Tcl issues
                current_values_list = []
        elif isinstance(current_values_tcl, tuple):
            current_values_list = list(current_values_tcl)
        else: # Should not happen, but as a fallback
            current_values_list = []
        
        if filtered_sugg != current_values_list:
            self.artist_combo["values"] = filtered_sugg

        # Manage dropdown visibility and focus
        if filtered_sugg and value: # Only post if there are suggestions and user has typed something
            try:
                is_posted_str = self.artist_combo.tk.call('ttk::combobox::IsPosted', self.artist_combo)
                if not bool(int(is_posted_str)):
                    self.artist_combo.tk.call('ttk::combobox::Post', self.artist_combo)
            except tk.TclError:
                pass # Ignore Tcl errors (e.g. widget destroyed, command not found)
            except ValueError:
                pass # Ignore error if is_posted_str is not '0' or '1'

        # --- Auto-suggestion/auto-completion ---
        completed_suggestion = False
        # Don't auto-complete on BackSpace/Delete, or if the value is now empty, or no suggestions
        if filtered_sugg and value and event.keysym not in ("BackSpace", "Delete"):
            best_match = filtered_sugg[0]
            # Check if the best match extends the current text and is not identical
            if best_match.lower().startswith(value.lower()) and len(best_match) > len(value):
                # Temporarily unbind KeyRelease to prevent recursion when setting var
                # Store the original binding if it exists
                try:
                    original_binding_id = self.artist_combo.bind("<KeyRelease>")
                    if original_binding_id:
                        # The actual command is usually part of a Tcl string returned by bind.
                        # We need to parse it or, more simply, re-bind to the method directly.
                        # For simplicity here, we'll re-bind to the method. If complex bindings are used,
                        # a more robust way to store/restore Tcl command strings would be needed.
                        pass # We will re-bind to self._filter_artist_suggestions
                except tk.TclError:
                    original_binding_id = None # No binding existed

                self.artist_combo.unbind("<KeyRelease>")
                self.artist_var.set(best_match)
                
                # Schedule selection and re-binding
                def select_suggestion_and_rebind():
                    if hasattr(self, 'artist_combo') and self.artist_combo.winfo_exists():
                        self.artist_combo.icursor(len(value)) # Place cursor after originally typed text
                        self.artist_combo.selection_range(len(value), tk.END) # Select the auto-completed part
                        self.artist_combo.focus_set() # Ensure focus remains
                    
                    # Re-bind after a short delay to ensure set() has propagated and avoid issues
                    # Only re-bind if there was an original binding to this method or we know what to bind to.
                    if hasattr(self, 'artist_combo') and self.artist_combo.winfo_exists():
                        self.artist_combo.bind("<KeyRelease>", self._filter_artist_suggestions)

                self.artist_combo.after_idle(select_suggestion_and_rebind)
                completed_suggestion = True
        
        if not completed_suggestion:
            # If no auto-completion, just ensure focus and cursor at end (previous behavior)
            self.artist_combo.after_idle(self._safe_focus_entry_and_cursor_end)

    # ---------------- Autocomplete logic -----------------
    def _load_intro_artists(self):
        """Scan intros directory once and build a sorted list of unique artist names"""
        intro_dir = app_config.get(["paths","intros_dir"], "")
        artists = set()
        if not os.path.exists(intro_dir):
            print(f"[MetadataEditDialog] Intro directory not found: {intro_dir}")
            return []
        for file_name in os.listdir(intro_dir):
            base = os.path.splitext(file_name)[0]
            # Remove leading numbers and separators similar to copy_filename logic
            base = re.sub(r'^\d+\s*[-_.]\s*', '', base)
            # Take characters up to first separator considered not part of artist name
            m = re.match(r"([A-Za-z\s'`“”‘’]+)", base)
            if m:
                artist_clean = m.group(1).strip()
                if artist_clean:
                    artists.add(artist_clean)
        sorted_artists = sorted(artists, key=str.lower)
        print(f"[MetadataEditDialog] Loaded {len(sorted_artists)} intro artists for autocomplete")
        return sorted_artists