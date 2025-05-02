
import os
import logging
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox


# --- Dialog Windows ---
class ColumnChooserDialog(simpledialog.Dialog):
    def __init__(self, parent, all_columns, selected_columns):
        self.all_columns = all_columns
        self.selected_columns = selected_columns
        self.vars = {}
        self.result = None
        super().__init__(parent, "Customize Columns")

    def body(self, master):
        tk.Label(master, text="Select columns to display:").pack(anchor='w', padx=10, pady=(10, 5))
        frame = ttk.Frame(master)
        frame.pack(padx=10, pady=5, fill='both', expand=True)
        
        for col in self.all_columns:
            var = tk.BooleanVar(value=(col in self.selected_columns))
            self.vars[col] = var
            ttk.Checkbutton(frame, text=col, variable=var).pack(anchor='w', padx=5, pady=2)
            
        return frame  # Initial focus

    def apply(self):
        selected = [col for col, var in self.vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("Warning", "You must select at least one column.", parent=self)
            self.result = None  # Prevent closing
        else:
            self.result = selected


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
        # --- Add Copy File Name Button ---
        copy_btn = ttk.Button(master, text="Copy File Name", command=self.copy_file_name)
        copy_btn.grid(row=row, column=0, columnspan=2, pady=(10, 2))
        return None # Focus handled above

    def copy_file_name(self):
        """Copy file name (no path, no extension) to clipboard and log the action."""
        path = self.track_data.get('path', '')
        if path:
            base = os.path.basename(path)
            name, _ = os.path.splitext(base)
            self.clipboard_clear()
            self.clipboard_append(name)
            logging.info(f"Copied file name to clipboard: {name}")
        else:
            logging.warning("No file path found to copy file name.")

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
