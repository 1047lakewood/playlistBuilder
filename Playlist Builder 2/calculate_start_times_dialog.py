import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog
from datetime import datetime, timedelta
from font_config import DEFAULT_FONT, DEFAULT_FONT_TUPLE


class CalculateStartTimesDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("Calculate Start Times")

        # Days of the week
        day_label = ttk.Label(master, text="Day:")
        day_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.day_var = tk.StringVar()
        self.day_combo = ttk.Combobox(master, textvariable=self.day_var, values=[
            'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'
        ], state='readonly')
        self.day_combo.grid(row=0, column=1, padx=5, pady=5)
        self.day_combo.current(0)

        # Time Entry
        time_label = ttk.Label(master, text="Time (hh:mm:ss AM/PM):")
        time_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.time_entry = ttk.Entry(master)
        self.time_entry.insert(0, "12:00:00 AM")
        self.time_entry.grid(row=1, column=1, padx=5, pady=5)

        return self.day_combo  # initial focus

    def validate(self):
        try:
            # Validate time
            datetime.strptime(self.time_entry.get(), "%I:%M:%S %p")
            return True
        except ValueError:
            tk.messagebox.showerror("Invalid Time", "Please enter time in hh:mm:ss AM/PM format.")
            return False

    def apply(self):
        day_str = self.day_var.get()
        time_str = self.time_entry.get()

        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        day_index = days.index(day_str)

        # Parse time as datetime
        time_obj = datetime.strptime(time_str, "%I:%M:%S %p")
        seconds = day_index * 86400 + time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second

        self.result = seconds