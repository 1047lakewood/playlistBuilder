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


class AutocompleteEntry(tk.Entry):
    def __init__(self, master, choices, textvariable=None, *args, **kwargs):
        super().__init__(master, textvariable=textvariable, *args, **kwargs)
        self.choices = choices
        self.var = textvariable or tk.StringVar()
        self.var.trace('w', self._on_change)
        self.listbox = None
        self.scrollbar = None
        self.popup_open = False
        self.bind('<Down>', self._move_down)
        # Remove Enter handler so Enter never selects from autocomplete, only closes dialog
        self.bind('<Escape>', lambda e: self._hide_listbox())
        self.bind('<FocusOut>', lambda e: self._hide_listbox())

    def _on_change(self, *args):
        typed = self.var.get().strip().lower()
        matches = [c for c in self.choices if c.lower().startswith(typed)] if typed else self.choices
        if matches:
            self._show_listbox(matches)
        else:
            self._hide_listbox()

    def _show_listbox(self, matches):
        if self.listbox is None or not self.listbox.winfo_exists():
            self.listbox = tk.Listbox(self.master, height=12, exportselection=False)
            self.listbox.bind('<ButtonRelease-1>', self._on_listbox_click)
            # self.listbox.bind('<Return>', self._select_from_listbox)  # removed
            # Add vertical scrollbar
            self.scrollbar = tk.Scrollbar(self.master, orient='vertical', command=self.listbox.yview)
            self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.listbox.config(height=12)
        self.listbox.delete(0, tk.END)
        for m in matches:
            self.listbox.insert(tk.END, m)
        x = self.winfo_x()
        y = self.winfo_y() + self.winfo_height()
        self.listbox.place(in_=self, x=0, y=self.winfo_height(), relwidth=0.92)
        self.listbox.lift()
        self.scrollbar.place(in_=self, x=self.winfo_width()-18, y=self.winfo_height(), width=18, height=self.listbox.winfo_reqheight())
        self.scrollbar.lift()
        self.listbox.selection_clear(0, tk.END)
        self.listbox.activate(0)
        self.listbox.selection_set(0)
        self.popup_open = True

    def _hide_listbox(self):
        if self.listbox and self.listbox.winfo_exists():
            self.listbox.place_forget()
        if self.scrollbar and self.scrollbar.winfo_exists():
            self.scrollbar.place_forget()
        self.popup_open = False

    def _move_down(self, event):
        if self.listbox and self.listbox.winfo_exists():
            self.listbox.focus_set()
            self.listbox.selection_set(0)
            return 'break'

    def _on_listbox_click(self, event):
        if self.listbox.curselection():
            value = self.listbox.get(self.listbox.curselection()[0])
            self.var.set(value)
            self._hide_listbox()
            self.focus_set()

    def _select_from_listbox(self, event=None):
        if self.listbox and self.listbox.winfo_exists() and self.listbox.curselection():
            value = self.listbox.get(self.listbox.curselection()[0])
            self.var.set(value)
            self._hide_listbox()
            self.focus_set()
        return 'break'

    def _on_return(self, event):
        if self.popup_open:
            # Select from listbox and close popup, but do not close dialog
            self._select_from_listbox()
            self._return_pressed_with_popup = True
            return 'break'
        elif getattr(self, '_return_pressed_with_popup', False):
            # Second Enter: allow dialog to close
            self._return_pressed_with_popup = False
            return None  # Let dialog handle
        else:
            return None  # Let dialog handle


class MetadataEditDialog(simpledialog.Dialog):
    def __init__(self, parent, track_data, artist_choices=None):
        self.track_data = track_data.copy() # Work on a copy
        self.entries = {}
        self.result = None
        self.artist_choices = artist_choices or []
        super().__init__(parent, f"Edit Metadata: {os.path.basename(track_data.get('path',''))}")

    def body(self, master):
        fields = ['Title', 'Artist', 'Album', 'Genre', 'TrackNumber']
        row = 0
        for field in fields:
            key = field.lower()
            ttk.Label(master, text=f"{field}:").grid(row=row, column=0, sticky='e', padx=5, pady=3)
            var = tk.StringVar(value=self.track_data.get(key, ''))
            if key == 'artist' and self.artist_choices:
                entry = AutocompleteEntry(master, self.artist_choices, textvariable=var, width=40)
            else:
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


class StartTimeDialog(simpledialog.Dialog):
    def __init__(self, parent, title=None):
        self.result = None
        super().__init__(parent, title or "Set Playlist Start Time")

    def body(self, master):
        import datetime
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        self.day_var = tk.StringVar(value=days[0])
        self.time_var = tk.StringVar(value='12:00:00 PM')
        row = 0
        tk.Label(master, text="Day of Week:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        day_menu = ttk.Combobox(master, textvariable=self.day_var, values=days, state='readonly')
        day_menu.grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Label(master, text="Start Time (hh:mm:ss AM/PM):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        time_entry = ttk.Entry(master, textvariable=self.time_var)
        time_entry.grid(row=row, column=1, padx=5, pady=5)
        return time_entry

    def apply(self):
        import datetime
        try:
            day = self.day_var.get()
            time_str = self.time_var.get()
            time_obj = datetime.datetime.strptime(time_str, '%I:%M:%S %p').time()
            self.result = (day, time_obj)
        except Exception as e:
            messagebox.showerror("Invalid Input", f"Invalid time format: {e}", parent=self)
            self.result = None

    def get_next_weekday_date(self, day):
        import datetime
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        today = datetime.datetime(2025, 5, 5)  # Use fixed current date as per user context
        today_weekday = today.weekday()  # Monday=0
        target_weekday = days.index(day)
        days_ahead = (target_weekday - today_weekday + 7) % 7
        if days_ahead == 0:
            days_ahead = 7  # Always go forward at least one week if today
        return today + datetime.timedelta(days=days_ahead)

    @staticmethod
    def get_next_weekday_date_static(day):
        import datetime
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        today = datetime.datetime(2025, 5, 5)  # Use fixed current date as per user context
        today_weekday = today.weekday()  # Monday=0
        target_weekday = days.index(day)
        days_ahead = (target_weekday - today_weekday + 7) % 7
        if days_ahead == 0:
            days_ahead = 7  # Always go forward at least one week if today
        return today + datetime.timedelta(days=days_ahead)
