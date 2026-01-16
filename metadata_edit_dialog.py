import tkinter as tk
from tkinter import simpledialog
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
        self._filtered_artists = self.intro_artists.copy()
        super().__init__(parent, title)
        self.after_idle(self._set_initial_size)

    def body(self, master):
        # Title row
        tk.Label(master, text="Title:", font=DEFAULT_FONT).grid(row=0, column=0, sticky="e", padx=(0, 5))
        self.title_var = tk.StringVar(value=self.track.title)
        title_entry = tk.Entry(master, textvariable=self.title_var, font=DEFAULT_FONT, width=50)
        title_entry.grid(row=0, column=1, sticky="ew")
        self.title_entry = title_entry

        copy_button = tk.Button(master, text="Copy Filename", command=self.copy_filename, font=DEFAULT_FONT)
        copy_button.grid(row=0, column=2, padx=5)

        # Artist row
        tk.Label(master, text="Artist:", font=DEFAULT_FONT).grid(row=1, column=0, sticky="e", padx=(0, 5), pady=(10, 0))
        self.artist_var = tk.StringVar(value=self.track.artist)
        self.artist_entry = tk.Entry(master, textvariable=self.artist_var, font=DEFAULT_FONT, width=50)
        self.artist_entry.grid(row=1, column=1, sticky="ew", pady=(10, 0))
        self.artist_entry.bind("<KeyRelease>", self._on_artist_key)
        self.artist_entry.bind("<Down>", self._focus_listbox)
        self.artist_entry.bind("<Return>", self._select_first_match)

        use_as_title_button = tk.Button(master, text="Use as Title", command=self.use_filename_as_title, font=DEFAULT_FONT)
        use_as_title_button.grid(row=1, column=2, padx=5, pady=(10, 0))

        # Artist suggestions section
        suggestions_frame = tk.Frame(master)
        suggestions_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10, 0))

        # Status label showing match count
        self.status_label = tk.Label(suggestions_frame, text="", font=DEFAULT_FONT, fg="gray")
        self.status_label.pack(anchor="w")

        # Listbox with scrollbar for artist suggestions
        list_frame = tk.Frame(suggestions_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.artist_listbox = tk.Listbox(
            list_frame,
            font=DEFAULT_FONT,
            height=8,
            yscrollcommand=scrollbar.set,
            exportselection=False
        )
        self.artist_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.artist_listbox.yview)

        # Listbox bindings
        self.artist_listbox.bind("<ButtonRelease-1>", self._on_listbox_select)
        self.artist_listbox.bind("<Return>", self._on_listbox_select)
        self.artist_listbox.bind("<Up>", self._listbox_up)

        # Configure grid weights
        master.columnconfigure(1, weight=1)
        master.rowconfigure(2, weight=1)

        # Initial population
        self._update_suggestions()

        return title_entry

    def _set_initial_size(self):
        """Set initial geometry and minimum size once widgets have been laid out."""
        try:
            self.update_idletasks()
            self.geometry("500x350")
            self.minsize(400, 300)
            self.resizable(True, True)
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

    # ----- Artist search/filtering logic -----
    def _on_artist_key(self, event):
        """Handle typing in the artist entry - filter suggestions."""
        # Ignore navigation/modifier keys
        if event.keysym in (
            "Up", "Down", "Return", "Escape", "Tab",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Left", "Right", "Home", "End"
        ):
            return

        # Get what user typed before updating suggestions
        typed = self.artist_var.get()

        self._update_suggestions()

        # Autocomplete: fill in first match if user is typing (not deleting)
        if event.keysym not in ("BackSpace", "Delete") and typed and self._filtered_artists:
            best = self._filtered_artists[0]
            # Only autocomplete if best match starts with what user typed
            if best.lower().startswith(typed.lower()) and len(best) > len(typed):
                self.artist_var.set(best)
                # Select the auto-completed portion so typing replaces it
                self.artist_entry.icursor(len(typed))
                self.artist_entry.selection_range(len(typed), len(best))

    def _update_suggestions(self):
        """Update the listbox with filtered artist suggestions."""
        query = self.artist_var.get().strip().lower()

        if query:
            # Contains matching - find artists that contain the search term anywhere
            self._filtered_artists = [
                a for a in self.intro_artists
                if query in a.lower()
            ]
            # Sort: prioritize artists that START with query, then alphabetical
            def sort_key(artist):
                lower = artist.lower()
                starts_with = lower.startswith(query)
                return (0 if starts_with else 1, lower)
            self._filtered_artists.sort(key=sort_key)
        else:
            self._filtered_artists = self.intro_artists.copy()

        # Update status label
        total = len(self.intro_artists)
        shown = len(self._filtered_artists)
        if query:
            self.status_label.config(text=f"Showing {shown} of {total} artists matching \"{query}\"")
        else:
            self.status_label.config(text=f"All {total} artists (type to filter)")

        # Update listbox
        self.artist_listbox.delete(0, tk.END)
        for artist in self._filtered_artists:
            self.artist_listbox.insert(tk.END, artist)

    def _focus_listbox(self, event):
        """Move focus to listbox when Down is pressed in entry."""
        if self._filtered_artists:
            self.artist_listbox.focus_set()
            self.artist_listbox.selection_clear(0, tk.END)
            self.artist_listbox.selection_set(0)
            self.artist_listbox.activate(0)
        return "break"

    def _listbox_up(self, event):
        """Return to entry when Up is pressed at top of listbox."""
        sel = self.artist_listbox.curselection()
        if sel and sel[0] == 0:
            self.artist_entry.focus_set()
            return "break"

    def _select_first_match(self, event):
        """Select the first match when Enter is pressed in entry."""
        if self._filtered_artists:
            self.artist_var.set(self._filtered_artists[0])
            self._update_suggestions()
        return "break"

    def _on_listbox_select(self, event):
        """Handle selection from the listbox (double-click or Enter)."""
        sel = self.artist_listbox.curselection()
        if sel:
            artist = self.artist_listbox.get(sel[0])
            self.artist_var.set(artist)
            self.artist_entry.focus_set()
            self._update_suggestions()

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