import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
import copy

class AdInserterWindow(tk.Toplevel):
    """Dialog for configuring advertisement insertions with tabs for each station."""

    def format_hour_ampm(self, hour):
        """Convert hour (0-23) to AM/PM format for display."""
        if hour == 0:
            return "12 AM"
        elif hour == 12:
            return "12 PM"
        elif hour < 12:
            return f"{hour} AM"
        else:
            return f"{hour - 12} PM"
    def __init__(self, parent, config_manager):
        """
        Initialize the Ad Inserter window.

        Args:
            parent: Parent tkinter window
            config_manager: ConfigManager instance
        """
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        
        self.title("Ad Inserter")
        self.geometry("850x650")
        self.minsize(750, 550)

        self.config_manager = config_manager
        
        # Dictionary to store station-specific data
        self.stations = {
            'station_1047': {
                'name': '104.7 FM',
                'ads': None,
                'initial_ads': None,
                'current_index': None,
                'widgets': {}
            },
            'station_887': {
                'name': '88.7 FM',
                'ads': None,
                'initial_ads': None,
                'current_index': None,
                'widgets': {}
            }
        }
        
        # Load ads for both stations
        for station_id in self.stations.keys():
            station_data = self.stations[station_id]
            loaded_ads = self.config_manager.get_station_ads(station_id)
            logging.info(f"Loaded ads from config for {station_id}: {loaded_ads}")
            station_data['ads'] = copy.deepcopy(loaded_ads or [])
            station_data['initial_ads'] = copy.deepcopy(station_data['ads'])
            logging.info(f"Ad Inserter initialized with {len(station_data['ads'])} existing ads for station {station_id}")

        self.create_widgets()
        
        # Populate ad lists for both stations
        for station_id in self.stations.keys():
            self.populate_ad_list(station_id)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create a tab for each station
        for station_id, station_data in self.stations.items():
            tab_frame = ttk.Frame(notebook, padding="10")
            notebook.add(tab_frame, text=station_data['name'])
            self.create_station_tab(tab_frame, station_id)
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="Save & Close", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side=tk.RIGHT, padx=5)

    def create_station_tab(self, parent_frame, station_id):
        """Create the ad inserter interface for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        
        # Left: Ad List with move buttons
        left_frame = ttk.LabelFrame(parent_frame, text="Advertisements", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 10))

        # Listbox container
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        widgets['ad_listbox'] = tk.Listbox(
            list_container, width=25, height=15, font=("Segoe UI", 10), exportselection=False
        )
        widgets['ad_listbox'].pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        widgets['ad_listbox'].bind(
            "<<ListboxSelect>>", lambda e, s=station_id: self.after(0, lambda: self.on_ad_select(s))
        )

        # Move buttons to the right of the listbox
        move_buttons = ttk.Frame(list_container)
        move_buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        ttk.Button(move_buttons, text="↑", width=3, command=lambda: self.move_up_ad(station_id)).pack(pady=2)
        ttk.Button(move_buttons, text="↓", width=3, command=lambda: self.move_down_ad(station_id)).pack(pady=2)

        # Buttons for list management (Add New, Delete)
        list_buttons = ttk.Frame(left_frame)
        list_buttons.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(list_buttons, text="Add New", command=lambda: self.add_new_ad(station_id)).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_buttons, text="Delete", command=lambda: self.delete_ad(station_id)).pack(side=tk.LEFT, padx=2)

        # Right: Options
        right_frame = ttk.LabelFrame(parent_frame, text="Ad Details", padding="5")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Name
        name_label = ttk.Label(right_frame, text="Name:", font=("Segoe UI", 10, "bold"))
        name_label.grid(row=0, column=0, sticky=tk.W, pady=5)
        widgets['name_var'] = tk.StringVar()
        ttk.Entry(right_frame, textvariable=widgets['name_var'], width=50, font=("Segoe UI", 10)).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # Enabled
        widgets['enabled_var'] = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="Enabled", variable=widgets['enabled_var'], style="Toggle.TCheckbutton").grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # MP3 File
        mp3_label = ttk.Label(right_frame, text="MP3 File:", font=("Segoe UI", 10, "bold"))
        mp3_label.grid(row=2, column=0, sticky=tk.W, pady=5)
        widgets['mp3_var'] = tk.StringVar()

        # Create a frame for MP3 file entry and browse button to keep them close together
        mp3_frame = ttk.Frame(right_frame)
        mp3_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5)

        ttk.Entry(mp3_frame, textvariable=widgets['mp3_var'], width=35, font=("Segoe UI", 10)).pack(side=tk.LEFT)
        ttk.Button(mp3_frame, text="Browse", command=lambda: self.browse_mp3(station_id), width=8).pack(side=tk.LEFT, padx=(5, 0))

        # Scheduled
        widgets['scheduled_var'] = tk.BooleanVar(value=False)
        ttk.Checkbutton(right_frame, text="Scheduled", variable=widgets['scheduled_var'], command=lambda: self.toggle_schedule(station_id), style="Toggle.TCheckbutton").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Days
        days_label = ttk.Label(right_frame, text="Days:", font=("Segoe UI", 10, "bold"))
        days_label.grid(row=4, column=0, sticky=tk.W, pady=5)
        days_frame = ttk.Frame(right_frame)
        days_frame.grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=5)
        widgets['day_vars'] = {}
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        for i, day in enumerate(days):
            widgets['day_vars'][day] = tk.BooleanVar()
            ttk.Checkbutton(days_frame, text=day[:3], variable=widgets['day_vars'][day]).pack(side=tk.LEFT, padx=2)

        # Select All Days button
        days_button_frame = ttk.Frame(right_frame)
        days_button_frame.grid(row=5, column=1, columnspan=2, sticky=tk.W, pady=(5, 0))
        widgets['select_all_days_btn'] = ttk.Button(days_button_frame, text="Select All Days",
                                                   command=lambda: self.toggle_all_days(station_id))
        widgets['select_all_days_btn'].pack(side=tk.LEFT)

        # Hours
        hours_label = ttk.Label(right_frame, text="Hours:", font=("Segoe UI", 10, "bold"))
        hours_label.grid(row=6, column=0, sticky=tk.NW, pady=5)
        hours_frame = ttk.Frame(right_frame)
        hours_frame.grid(row=6, column=1, columnspan=2, sticky=tk.W, pady=5)
        widgets['hour_vars'] = {}
        for h in range(24):
            widgets['hour_vars'][h] = tk.BooleanVar()
            hour_label = self.format_hour_ampm(h)
            cb = ttk.Checkbutton(hours_frame, text=hour_label, variable=widgets['hour_vars'][h], width=6)
            cb.grid(row=h//6, column=h%6, padx=1, pady=1, sticky=tk.W)

        # Select All Hours button
        hours_button_frame = ttk.Frame(right_frame)
        hours_button_frame.grid(row=7, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))
        widgets['select_all_hours_btn'] = ttk.Button(hours_button_frame, text="Select All Hours",
                                                   command=lambda: self.toggle_all_hours(station_id))
        widgets['select_all_hours_btn'].pack(side=tk.LEFT)

        # Save button (for changes within tab)
        save_frame = ttk.Frame(right_frame)
        save_frame.grid(row=8, column=0, columnspan=3, pady=10)
        ttk.Button(save_frame, text="Save Changes", command=lambda: self.save_current_ad(station_id)).pack()

    def populate_ad_list(self, station_id):
        """Populate the ad list for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        listbox = widgets['ad_listbox']
        
        listbox.delete(0, tk.END)
        for ad in station_data['ads']:
            ad_name = ad.get('Name', 'Unnamed Ad')
            enabled_marker = "✓" if ad.get('Enabled', False) else "✗"
            listbox.insert(tk.END, f"{enabled_marker} {ad_name}")

    def on_ad_select(self, station_id):
        """Handle ad selection for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        listbox = widgets['ad_listbox']
        
        selection = listbox.curselection()
        if not selection:
            # In rare timing cases, try once more after the event loop cycles
            self.after(0, lambda: self.on_ad_select(station_id))
            return
        
        index = selection[0]
        station_data['current_index'] = index
        ad = station_data['ads'][index]
        
        # Populate fields
        widgets['name_var'].set(ad.get('Name', ''))
        widgets['enabled_var'].set(ad.get('Enabled', True))
        widgets['mp3_var'].set(ad.get('MP3File', ''))
        widgets['scheduled_var'].set(ad.get('Scheduled', False))
        
        # Days
        for day in widgets['day_vars']:
            widgets['day_vars'][day].set(day in ad.get('Days', []))
        
        # Hours
        for h in widgets['hour_vars']:
            widgets['hour_vars'][h].set(h in ad.get('Hours', []))
        
        self.toggle_schedule(station_id)

    def add_new_ad(self, station_id):
        """Add a new ad for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        
        new_ad = {
            'Name': 'New Ad',
            'Enabled': True,
            'MP3File': '',
            'Scheduled': False,
            'Days': [],
            'Hours': [],
            'PlayCount': 0,
            'LastPlayed': None
        }
        station_data['ads'].append(new_ad)
        self.populate_ad_list(station_id)
        
        # Select the new ad
        listbox = widgets['ad_listbox']
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(tk.END)
        listbox.see(tk.END)
        self.on_ad_select(station_id)

    def delete_ad(self, station_id):
        """Delete the selected ad for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']

        if station_data['current_index'] is None:
            messagebox.showwarning("No Selection", "Please select an ad to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this ad?"):
            del station_data['ads'][station_data['current_index']]
            station_data['current_index'] = None
            self.populate_ad_list(station_id)

            # Clear fields
            widgets['name_var'].set('')
            widgets['enabled_var'].set(True)
            widgets['mp3_var'].set('')
            widgets['scheduled_var'].set(False)
            for day in widgets['day_vars']:
                widgets['day_vars'][day].set(False)
            for h in widgets['hour_vars']:
                widgets['hour_vars'][h].set(False)

    def move_up_ad(self, station_id):
        """Move the selected ad up in the list for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']

        if station_data['current_index'] is None:
            messagebox.showwarning("No Selection", "Please select an ad to move.")
            return

        index = station_data['current_index']
        if index > 0:
            # Swap with the previous item
            station_data['ads'][index], station_data['ads'][index - 1] = station_data['ads'][index - 1], station_data['ads'][index]
            station_data['current_index'] = index - 1
            self.populate_ad_list(station_id)

            # Update selection in the listbox
            listbox = widgets['ad_listbox']
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index - 1)
            listbox.see(index - 1)
            self.on_ad_select(station_id)

    def move_down_ad(self, station_id):
        """Move the selected ad down in the list for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']

        if station_data['current_index'] is None:
            messagebox.showwarning("No Selection", "Please select an ad to move.")
            return

        index = station_data['current_index']
        if index < len(station_data['ads']) - 1:
            # Swap with the next item
            station_data['ads'][index], station_data['ads'][index + 1] = station_data['ads'][index + 1], station_data['ads'][index]
            station_data['current_index'] = index + 1
            self.populate_ad_list(station_id)

            # Update selection in the listbox
            listbox = widgets['ad_listbox']
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index + 1)
            listbox.see(index + 1)
            self.on_ad_select(station_id)

    def save_current_ad(self, station_id):
        """Save changes to the currently selected ad for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        
        if station_data['current_index'] is None:
            messagebox.showwarning("No Selection", "Please select an ad to save.")
            return
        
        ad = station_data['ads'][station_data['current_index']]
        ad['Name'] = widgets['name_var'].get()
        ad['Enabled'] = widgets['enabled_var'].get()
        ad['MP3File'] = widgets['mp3_var'].get()
        ad['Scheduled'] = widgets['scheduled_var'].get()
        ad['Days'] = [day for day, var in widgets['day_vars'].items() if var.get()]
        ad['Hours'] = [h for h, var in widgets['hour_vars'].items() if var.get()]
        
        logging.info(f"Saved ad to memory: {ad}")
        self.populate_ad_list(station_id)

    def browse_mp3(self, station_id):
        """Browse for an MP3 file for a specific station."""
        widgets = self.stations[station_id]['widgets']
        filename = filedialog.askopenfilename(
            title="Select MP3 File",
            filetypes=[("MP3 Files", "*.mp3"), ("All Files", "*.*")]
        )
        if filename:
            widgets['mp3_var'].set(filename)

    def toggle_schedule(self, station_id):
        """Toggle schedule-related fields for a specific station."""
        # This method can be used to enable/disable schedule fields
        pass

    def toggle_all_days(self, station_id):
        """Toggle all day checkboxes for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        day_vars = widgets['day_vars']

        # Check if all days are currently selected
        all_selected = all(var.get() for var in day_vars.values())

        # Toggle all days (if all selected, deselect all; otherwise select all)
        new_state = not all_selected
        for day_var in day_vars.values():
            day_var.set(new_state)

        # Update button text
        select_days_btn = widgets['select_all_days_btn']
        if new_state:
            select_days_btn.config(text="Clear All Days")
        else:
            select_days_btn.config(text="Select All Days")

    def toggle_all_hours(self, station_id):
        """Toggle all hour checkboxes for a specific station."""
        station_data = self.stations[station_id]
        widgets = station_data['widgets']
        hour_vars = widgets['hour_vars']

        # Check if all hours are currently selected
        all_selected = all(var.get() for var in hour_vars.values())

        # Toggle all hours (if all selected, deselect all; otherwise select all)
        new_state = not all_selected
        for hour_var in hour_vars.values():
            hour_var.set(new_state)

        # Update button text
        select_hours_btn = widgets['select_all_hours_btn']
        if new_state:
            select_hours_btn.config(text="Clear All Hours")
        else:
            select_hours_btn.config(text="Select All Hours")

    def save_and_close(self):
        """Save all changes for both stations and close the window."""
        try:
            # First save any currently edited ad for each station
            for station_id in self.stations.keys():
                if self.stations[station_id]['current_index'] is not None:
                    self.save_current_ad(station_id)

            # Save ads for both stations
            for station_id, station_data in self.stations.items():
                logging.info(f"Saving {len(station_data['ads'])} ads for {station_id}")
                self.config_manager.set_station_ads(station_id, station_data['ads'])
                logging.info(f"Ads set for {station_id}: {[ad.get('Name', 'Unnamed') for ad in station_data['ads']]}")

            self.config_manager.save_config()
            logging.info("All ad configurations saved successfully for both stations.")
            self.destroy()
        except Exception as e:
            logging.error(f"Error saving ad configurations: {e}")
            import traceback
            logging.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to save ad configurations: {e}")

    def on_close(self):
        """Handle window close event."""
        # Check if there are unsaved changes in either station
        has_changes = False
        for station_id, station_data in self.stations.items():
            if station_data['ads'] != station_data['initial_ads']:
                has_changes = True
                break
        
        if has_changes:
            if messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Close anyway?"):
                self.destroy()
        else:
            self.destroy()
