import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import re
import logging
import utils

# Placeholder for ConfigManager if needed directly (passed in constructor)
# from config_manager import ConfigManager

class ConfigWindow(Toplevel):
    """Window for configuring RDS messages (add, delete, edit, schedule)."""
    def __init__(self, parent, config_manager):
        """
        Initialize the Configure RDS Messages window.

        Args:
            parent: Parent tkinter window
            config_manager: ConfigManager instance
        """
        super().__init__(parent)
        self.transient(parent) # Keep window on top of parent
        self.grab_set() # Modal behavior
        self.title("Configure RDS Messages")
        self.geometry("1200x800") # Larger for dual-station tabs

        self.config_manager = config_manager
        self.current_station = "station_1047"  # Default station

        # Station-specific storage for messages and UI state
        self.station_messages = {
            "station_1047": self.config_manager.get_station_messages("station_1047"),
            "station_887": self.config_manager.get_station_messages("station_887")
        }
        self.station_selected_indices = {
            "station_1047": None,
            "station_887": None
        }
        self.station_changes_pending = {
            "station_1047": False,
            "station_887": False
        }

        # Station-specific UI widget storage
        self.station_message_vars = {}
        self.station_enable_vars = {}
        self.station_duration_vars = {}
        self.station_use_schedule_vars = {}
        self.station_days_vars = {}
        self.station_hour_vars = {}
        self.station_days_btn_frames = {}
        self.station_hours_btn_frames = {}
        self.station_char_count_vars = {}
        self.station_time_entries = {}
        self.station_schedule_containers = {}

        # Use parent's theme settings if possible (ttkthemes applies globally)
        self.style = ttk.Style() # Inherit style from parent

        self.create_widgets()
        self.load_messages_into_tree()

        # Handle closing the window
        self.protocol("WM_DELETE_WINDOW", self.on_close)

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

    def toggle_all_days(self, station_id):
        """Toggle all day checkboxes for a station."""
        if station_id not in self.station_days_vars:
            return

        day_vars = self.station_days_vars[station_id]
        # Check if all days are currently selected
        all_selected = all(var.get() for var in day_vars.values())

        # Toggle all days (if all selected, deselect all; otherwise select all)
        new_state = not all_selected
        for day_var in day_vars.values():
            day_var.set(new_state)

        # Update button text
        days_button_frame = self.station_days_btn_frames[station_id]
        select_days_btn = days_button_frame.winfo_children()[0]
        if new_state:
            select_days_btn.config(text="Clear All Days")
        else:
            select_days_btn.config(text="Select All Days")

        self.mark_station_changes(station_id)

    def toggle_all_hours(self, station_id):
        """Toggle all hour checkboxes for a station."""
        if station_id not in self.station_hour_vars:
            return

        hour_vars = self.station_hour_vars[station_id]
        # Check if all hours are currently selected
        all_selected = all(var.get() for var in hour_vars.values())

        # Toggle all hours (if all selected, deselect all; otherwise select all)
        new_state = not all_selected
        for hour_var in hour_vars.values():
            hour_var.set(new_state)

        # Update button text
        hours_button_frame = self.station_hours_btn_frames[station_id]
        select_hours_btn = hours_button_frame.winfo_children()[0]
        if new_state:
            select_hours_btn.config(text="Clear All Hours")
        else:
            select_hours_btn.config(text="Select All Hours")

        self.mark_station_changes(station_id)

    def update_toggle_button_texts(self, station_id):
        """Update the toggle button texts based on current selections."""
        # Update days button
        if station_id in self.station_days_btn_frames:
            days_button_frame = self.station_days_btn_frames[station_id]
            select_days_btn = days_button_frame.winfo_children()[0]
            day_vars = self.station_days_vars[station_id]
            all_days_selected = all(var.get() for var in day_vars.values())
            if all_days_selected:
                select_days_btn.config(text="Clear All Days")
            else:
                select_days_btn.config(text="Select All Days")

        # Update hours button
        if station_id in self.station_hours_btn_frames:
            hours_button_frame = self.station_hours_btn_frames[station_id]
            select_hours_btn = hours_button_frame.winfo_children()[0]
            hour_vars = self.station_hour_vars[station_id]
            all_hours_selected = all(var.get() for var in hour_vars.values())
            if all_hours_selected:
                select_hours_btn.config(text="Clear All Hours")
            else:
                select_hours_btn.config(text="Select All Hours")

    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for station tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs for each station
        self.station_frames = {}
        self.station_trees = {}
        self.station_details_frames = {}

        # Station 104.7 FM tab
        station_1047_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(station_1047_frame, text="Station 104.7 FM")
        self.station_frames["station_1047"] = station_1047_frame
        self.create_station_tab(station_1047_frame, "station_1047")

        # Station 88.7 FM tab
        station_887_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(station_887_frame, text="Station 88.7 FM")
        self.station_frames["station_887"] = station_887_frame
        self.create_station_tab(station_887_frame, "station_887")

        # Bind tab change event
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)

    def create_station_tab(self, parent_frame, station_id):
        """Create the message configuration interface for a specific station."""
        # Split view - messages list on left, details on right
        paned = ttk.PanedWindow(parent_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- Message list frame (left side) ---
        list_frame = ttk.LabelFrame(paned, text="Scheduled Messages")

        # Toolbar for list operations
        list_toolbar = ttk.Frame(list_frame)
        list_toolbar.pack(fill=tk.X, pady=(5, 5))

        ttk.Button(list_toolbar, text="Add New", command=self.add_message).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_toolbar, text="Delete", command=self.delete_message).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_toolbar, text="Move Up", command=self.move_message_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_toolbar, text="Move Down", command=self.move_message_down).pack(side=tk.LEFT, padx=2)

        # Treeview with scrollbars
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(tree_frame, columns=("Text", "Enabled", "Scheduled", "Duration", "Days", "Times"),
                               show='headings', selectmode="browse")
        tree.heading("Text", text="Message", anchor=tk.W)
        tree.heading("Enabled", text="Enabled", anchor=tk.CENTER)
        tree.heading("Scheduled", text="Use Sched", anchor=tk.CENTER)
        tree.heading("Duration", text="Dur (s)", anchor=tk.CENTER)
        tree.heading("Days", text="Days", anchor=tk.W)
        tree.heading("Times", text="Times (Hr)", anchor=tk.W)

        tree.column("Text", width=200, stretch=True)
        tree.column("Enabled", width=60, stretch=False, anchor=tk.CENTER)
        tree.column("Scheduled", width=70, stretch=False, anchor=tk.CENTER)
        tree.column("Duration", width=60, stretch=False, anchor=tk.CENTER)
        tree.column("Days", width=150, stretch=True)
        tree.column("Times", width=100, stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        tree.bind("<<TreeviewSelect>>", self.on_message_select)

        # --- Message details frame (right side) ---
        details_frame = ttk.LabelFrame(paned, text="Message Details")
        paned.add(list_frame, weight=1)
        paned.add(details_frame, weight=2)

        details_content = ttk.Frame(details_frame, padding=(10, 5))
        details_content.pack(fill=tk.BOTH, expand=True)

        # Store references for this station
        self.station_trees[station_id] = tree
        self.station_details_frames[station_id] = details_content

        # Create station-specific details widgets
        self.create_station_details_widgets(details_content, station_id)

    def create_station_details_widgets(self, parent_frame, station_id):
        """Create the message details editing widgets for a specific station."""
        message_frame = ttk.LabelFrame(parent_frame, text="Message Content (64 char max)")
        message_frame.pack(fill=tk.X, pady=(0, 10))

        message_var = tk.StringVar()
        self.station_message_vars[station_id] = message_var
        message_entry = ttk.Entry(message_frame, textvariable=message_var, font=("Segoe UI", 10), width=64)
        message_entry.pack(fill=tk.X, padx=5, pady=5)

        char_count_var = tk.StringVar(value="0/64")
        self.station_char_count_vars[station_id] = char_count_var
        char_count_label = ttk.Label(message_frame, textvariable=char_count_var, anchor=tk.E)
        char_count_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        message_var.trace_add("write", lambda *args, sid=station_id: self.update_station_char_count(sid))

        settings_frame = ttk.LabelFrame(parent_frame, text="Message Settings")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill=tk.X, padx=5, pady=5)

        enable_var = tk.BooleanVar()
        self.station_enable_vars[station_id] = enable_var
        enable_check = ttk.Checkbutton(settings_grid, text="Message Enabled", variable=enable_var,
                                     command=lambda sid=station_id: self.mark_station_changes(sid))
        enable_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        ttk.Label(settings_grid, text="Duration (seconds):").grid(row=0, column=1, sticky=tk.W, padx=(20, 5), pady=5)
        duration_var = tk.StringVar()
        self.station_duration_vars[station_id] = duration_var
        vcmd = (self.register(self.validate_duration), '%P')
        duration_spin = ttk.Spinbox(settings_grid, from_=1, to=60, width=5, textvariable=duration_var, validate='key', validatecommand=vcmd)
        duration_spin.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        duration_var.trace_add("write", lambda *args, sid=station_id: self.mark_station_changes(sid))

        schedule_frame = ttk.LabelFrame(parent_frame, text="Message Schedule")
        schedule_frame.pack(fill=tk.X)
        schedule_options = ttk.Frame(schedule_frame)
        schedule_options.pack(fill=tk.X, padx=5, pady=5)

        use_schedule_var = tk.BooleanVar()
        self.station_use_schedule_vars[station_id] = use_schedule_var
        schedule_check = ttk.Checkbutton(schedule_options, text="Use Scheduling", variable=use_schedule_var,
                                       command=lambda sid=station_id: self.toggle_station_schedule_controls(sid))
        schedule_check.pack(anchor=tk.W)
        schedule_help = ttk.Label(schedule_options, text="If unchecked, message will always display when enabled (subject to artist filters)", font=("Segoe UI", 9), foreground="#666666")
        schedule_help.pack(anchor=tk.W, pady=(0, 5))

        schedule_container = ttk.Frame(schedule_frame)
        schedule_container.pack(fill=tk.X, padx=5, pady=5)
        self.station_schedule_containers[station_id] = schedule_container

        # Days of the week checkboxes
        days_frame = ttk.Frame(schedule_container)
        days_frame.pack(fill=tk.X, pady=5)
        ttk.Label(days_frame, text="Schedule Days:").grid(row=0, column=0, sticky=tk.W)
        days_checks_frame = ttk.Frame(days_frame)
        days_checks_frame.grid(row=1, column=0, sticky=tk.W)

        days_vars = {}
        self.station_days_vars[station_id] = days_vars
        day_labels = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for i, day in enumerate(day_labels):
            var = tk.BooleanVar()
            days_vars[day] = var
            check = ttk.Checkbutton(days_checks_frame, text=day, variable=var,
                                  command=lambda sid=station_id: self.mark_station_changes(sid))
            row, col = divmod(i, 4)
            check.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)

        # Select All Days button
        days_button_frame = ttk.Frame(days_frame)
        days_button_frame.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.station_days_btn_frames[station_id] = days_button_frame
        select_days_btn = ttk.Button(days_button_frame, text="Select All Days",
                                    command=lambda sid=station_id: self.toggle_all_days(sid))
        select_days_btn.pack(side=tk.LEFT)

        # Hours of the day checkboxes
        hours_frame = ttk.Frame(schedule_container)
        hours_frame.pack(fill=tk.X, pady=5)
        ttk.Label(hours_frame, text="Schedule Hours:").grid(row=0, column=0, sticky=tk.W)

        hours_checks_frame = ttk.Frame(hours_frame)
        hours_checks_frame.grid(row=1, column=0, sticky=tk.W)

        hour_vars = {}
        self.station_hour_vars[station_id] = hour_vars

        # Create 4 rows of 6 hours each (24 hours total)
        for h in range(24):
            var = tk.BooleanVar()
            hour_vars[h] = var
            hour_label = self.format_hour_ampm(h)
            check = ttk.Checkbutton(hours_checks_frame, text=hour_label, variable=var,
                                  command=lambda sid=station_id: self.mark_station_changes(sid))
            row, col = divmod(h, 6)
            check.grid(row=row, column=col, sticky=tk.W, padx=2, pady=1)

        # Select All Hours button
        hours_button_frame = ttk.Frame(hours_frame)
        hours_button_frame.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.station_hours_btn_frames[station_id] = hours_button_frame
        select_hours_btn = ttk.Button(hours_button_frame, text="Select All Hours",
                                     command=lambda sid=station_id: self.toggle_all_hours(sid))
        select_hours_btn.pack(side=tk.LEFT)

        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Save Changes", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side=tk.RIGHT, padx=5)

        self.set_details_state(tk.DISABLED)

    def on_tab_changed(self, event):
        """Handle tab change event."""
        # Get the current tab index
        current_tab = self.notebook.index(self.notebook.select())

        # Determine station_id based on tab index
        if current_tab == 0:
            self.current_station = "station_1047"
        elif current_tab == 1:
            self.current_station = "station_887"
        else:
            return  # Unknown tab

        # Update messages and reload tree for current station
        self.load_messages_into_tree()

    def validate_duration(self, P):
        if P == "": return True
        try:
            val = int(P)
            return 1 <= val <= 60
        except ValueError:
            return False

    def update_station_char_count(self, station_id):
        """Update character count for a specific station."""
        if self.is_loading_selection: return
        text = self.station_message_vars[station_id].get()
        count = len(text)
        if count > 64:
            self.station_message_vars[station_id].set(text[:64])
            count = 64
        self.station_char_count_vars[station_id].set(f"{count}/64")
        self.mark_station_changes(station_id)

    def mark_station_changes(self, station_id):
        """Mark changes for a specific station."""
        if self.station_selected_indices[station_id] is not None and not self.is_loading_selection:
            self.station_changes_pending[station_id] = True
            self.update_station_current_message_data(station_id)

    def update_station_current_message_data(self, station_id):
        """Update the current message data for a specific station."""
        selected_index = self.station_selected_indices[station_id]
        if selected_index is None or self.is_loading_selection: return
        try:
            current_messages = self.station_messages[station_id]
            current_msg = current_messages[selected_index]
            current_msg["Text"] = self.station_message_vars[station_id].get()
            current_msg["Enabled"] = self.station_enable_vars[station_id].get()
            try:
                duration = int(self.station_duration_vars[station_id].get())
                current_msg["Message Time"] = duration if 1 <= duration <= 60 else 10
            except ValueError: current_msg["Message Time"] = 10
            use_schedule = self.station_use_schedule_vars[station_id].get()
            current_msg["Scheduled"] = {"Enabled": use_schedule, "Days": [day for day, var in self.station_days_vars[station_id].items() if var.get()] if use_schedule else [], "Times": self.get_station_times(station_id) if use_schedule else []}
            self.update_treeview_item(selected_index)
        except IndexError:
             logging.error(f"Selected index {selected_index} out of bounds.")
             self.station_selected_indices[station_id] = None
             self.set_details_state(tk.DISABLED)
        except Exception as e:
            logging.exception(f"Error updating message data: {e}")
            messagebox.showerror("Error", f"Error updating message details:\n{e}", parent=self)

    def toggle_station_schedule_controls(self, station_id):
        """Toggle schedule controls for a specific station."""
        if self.is_loading_selection: return
        new_state = tk.NORMAL if self.station_use_schedule_vars[station_id].get() else tk.DISABLED
        logging.info(f"Toggle schedule controls for {station_id}: use_schedule={self.station_use_schedule_vars[station_id].get()}, new_state={new_state}")
        def recursive_configure(widget, state):
            try:
                if isinstance(widget, (ttk.Checkbutton, ttk.Entry, ttk.Spinbox, ttk.Button)):
                     widget.configure(state=state)
                for child in widget.winfo_children():
                    recursive_configure(child, state)
            except tk.TclError: pass
        # Configure the schedule container for this station
        if station_id in self.station_schedule_containers:
            recursive_configure(self.station_schedule_containers[station_id], new_state)
        else:
            logging.warning(f"No schedule container found for {station_id}")
        self.mark_station_changes(station_id)

    def set_details_state(self, state):
        """Set the state of details widgets for the current station."""
        # Since we now have station-specific widgets, this method is simplified
        # The actual widget state management is handled by the station-specific logic
        # and the toggle_station_schedule_controls method
        pass

    def load_messages_into_tree(self):
        # Get the current tree and messages for the current station
        current_tree = self.station_trees[self.current_station]
        current_messages = self.station_messages[self.current_station]

        current_tree.delete(*current_tree.get_children())
        for i, msg in enumerate(current_messages):
            days = ", ".join(msg.get("Scheduled", {}).get("Days", []))
            time_list = msg.get("Scheduled", {}).get("Times", [])
            formatted_times = []
            for time_item in time_list:
                if isinstance(time_item, dict) and "hour" in time_item:
                    formatted_times.append(self.format_hour_ampm(time_item['hour']))
                elif isinstance(time_item, (int, float)):
                    formatted_times.append(self.format_hour_ampm(int(time_item)))
            times = ", ".join(formatted_times)
            enabled = "Yes" if msg.get("Enabled", False) else "No"
            scheduled = "Yes" if msg.get("Scheduled", {}).get("Enabled", False) else "No"
            text = msg.get("Text", "")
            display_text = (text[:27] + "...") if len(text) > 30 else text
            current_tree.insert("", tk.END, iid=f"item{i}", values=(display_text, enabled, scheduled, msg.get("Message Time", 10), days, times))

        # Restore the selected index for this station
        selected_index = self.station_selected_indices[self.current_station]
        if selected_index is not None and selected_index < len(current_messages):
            current_tree.selection_set(f"item{selected_index}")
            current_tree.see(f"item{selected_index}")
            self.on_message_select(None)

    def mark_changes(self, *args):
        if self.station_selected_indices[self.current_station] is not None and not self.is_loading_selection:
            self.station_changes_pending[self.current_station] = True
            self.update_station_current_message_data(self.current_station)

    def update_treeview_item(self, index):
        try:
            item_id = f"item{index}"
            current_tree = self.station_trees[self.current_station]
            if not current_tree.exists(item_id): return
            current_messages = self.station_messages[self.current_station]
            msg = current_messages[index]
            days = ", ".join(msg.get("Scheduled", {}).get("Days", []))
            time_list = msg.get("Scheduled", {}).get("Times", [])
            formatted_times = [self.format_hour_ampm(t['hour']) for t in time_list if isinstance(t, dict) and 'hour' in t]
            times = ", ".join(formatted_times)
            enabled = "Yes" if msg.get("Enabled", False) else "No"
            scheduled = "Yes" if msg.get("Scheduled", {}).get("Enabled", False) else "No"
            text = msg.get("Text", "")
            display_text = (text[:27] + "...") if len(text) > 30 else text
            current_tree.item(item_id, values=(display_text, enabled, scheduled, msg.get("Message Time", 10), days, times))
        except IndexError: logging.warning(f"Update treeview invalid index {index}")
        except Exception as e: logging.exception(f"Error updating treeview item {index}: {e}")

    def get_station_times(self, station_id):
        """Get the hours from the station-specific hour checkboxes."""
        if station_id not in self.station_hour_vars:
            return []
        hour_vars = self.station_hour_vars[station_id]
        return [{"hour": h} for h, var in hour_vars.items() if var.get()]

    def parse_station_times(self, station_id):
        """Parse the hours from the station-specific time entry widget (legacy support)."""
        if station_id not in self.station_time_entries:
            return []
        time_str = self.station_time_entries[station_id].get().strip()
        return utils.parse_time_string(time_str)

    def parse_times(self):
        """Parse the hours from the entry widget using ``utils.parse_time_string``."""
        time_str = self.time_entry.get().strip()
        return utils.parse_time_string(time_str)

    def on_message_select(self, event):
        current_tree = self.station_trees[self.current_station]
        current_messages = self.station_messages[self.current_station]

        selected_items = current_tree.selection()
        if not selected_items:
            self.station_selected_indices[self.current_station] = None
            self.set_details_state(tk.DISABLED)
            return

        selected_item_id = selected_items[0]
        try: item_index = int(selected_item_id.replace("item", ""))
        except (ValueError, IndexError):
            logging.error(f"Bad index from ID: {selected_item_id}")
            self.station_selected_indices[self.current_station] = None
            self.set_details_state(tk.DISABLED)
            return

        self.station_selected_indices[self.current_station] = item_index
        try: message = current_messages[item_index]
        except IndexError:
            logging.error(f"Index {item_index} out of range.")
            self.station_selected_indices[self.current_station] = None
            self.set_details_state(tk.DISABLED)
            return
        self.is_loading_selection = True
        logging.info(f"Selecting item index: {item_index}, Text: {message.get('Text', '')}")
        # Set basic message data first for current station
        station_id = self.current_station
        self.station_message_vars[station_id].set(message.get("Text", "")[:64])
        self.station_char_count_vars[station_id].set(f"{len(self.station_message_vars[station_id].get())}/64")
        self.station_enable_vars[station_id].set(message.get("Enabled", False))
        self.station_duration_vars[station_id].set(message.get("Message Time", 10))
        use_schedule = message.get("Scheduled", {}).get("Enabled", False)
        self.station_use_schedule_vars[station_id].set(use_schedule)
        # Now set the details state after schedule variables are set
        self.set_details_state(tk.NORMAL)
        scheduled_days = message.get("Scheduled", {}).get("Days", [])
        logging.info(f"Scheduled Days Before Loading: {scheduled_days}")
        for day, var in self.station_days_vars[station_id].items(): var.set(day in scheduled_days)

        time_list = message.get("Scheduled", {}).get("Times", [])
        logging.info(f"Scheduled Times Before Loading: {time_list}")
        # Set hour checkboxes
        if station_id in self.station_hour_vars:
            for h, var in self.station_hour_vars[station_id].items():
                var.set(any(t.get('hour') == h for t in time_list if isinstance(t, dict) and 'hour' in t))

        # Update button texts based on current selections
        self.update_toggle_button_texts(station_id)
        # Keep is_loading_selection = True while toggle_schedule_controls() runs to prevent unintended mark_changes()
        self.toggle_station_schedule_controls(station_id)
        logging.info(f"Days After Loading: {[day for day, var in self.station_days_vars[station_id].items() if var.get()]}")
        selected_hours = [h for h, var in self.station_hour_vars[station_id].items() if var.get()]
        logging.info(f"Hours After Loading: {selected_hours}")
        self.is_loading_selection = False

    def add_message(self):
        current_messages = self.station_messages[self.current_station]
        new_message = {"Text": "New Message", "Enabled": False, "Message Time": 10, "Scheduled": {"Enabled": False, "Days": [], "Times": []}}
        current_messages.append(new_message)
        self.station_changes_pending[self.current_station] = True
        new_index = len(current_messages) - 1
        self.load_messages_into_tree()
        new_item_id = f"item{new_index}"
        current_tree = self.station_trees[self.current_station]
        if current_tree.exists(new_item_id):
            current_tree.selection_set(new_item_id); current_tree.see(new_item_id); self.on_message_select(None)
        else: logging.error("Failed to find new item in tree.")

    def delete_message(self):
        selected_index = self.station_selected_indices[self.current_station]
        if selected_index is None:
            messagebox.showwarning("No Selection", "Please select a message to delete.", parent=self)
            return

        current_messages = self.station_messages[self.current_station]
        # if messagebox.askyesno("Confirm Delete", f"Delete message:\n'{current_messages[selected_index].get('Text', '')[:30]}...'?", parent=self):
        del current_messages[selected_index]
        self.station_changes_pending[self.current_station] = True
        original_selection_index = selected_index
        self.load_messages_into_tree()
        self.station_selected_indices[self.current_station] = None
        self.set_details_state(tk.DISABLED)

        if current_messages:
            new_selection_index = min(original_selection_index, len(current_messages) - 1)
            new_item_id = f"item{new_selection_index}"
            current_tree = self.station_trees[self.current_station]
            if current_tree.exists(new_item_id):
                current_tree.selection_set(new_item_id)
                current_tree.see(new_item_id)
                self.on_message_select(None)

    def move_message_up(self):
        selected_index = self.station_selected_indices[self.current_station]
        if selected_index is None or selected_index == 0: return

        current_messages = self.station_messages[self.current_station]
        idx = selected_index
        current_messages.insert(idx - 1, current_messages.pop(idx))
        self.station_changes_pending[self.current_station] = True
        new_item_id = f"item{idx - 1}"
        self.load_messages_into_tree()
        current_tree = self.station_trees[self.current_station]
        if current_tree.exists(new_item_id):
            current_tree.selection_set(new_item_id)
            current_tree.see(new_item_id)
            self.on_message_select(None)

    def move_message_down(self):
        selected_index = self.station_selected_indices[self.current_station]
        current_messages = self.station_messages[self.current_station]
        if selected_index is None or selected_index >= len(current_messages) - 1: return

        idx = selected_index
        current_messages.insert(idx + 1, current_messages.pop(idx))
        self.station_changes_pending[self.current_station] = True
        new_item_id = f"item{idx + 1}"
        self.load_messages_into_tree()
        current_tree = self.station_trees[self.current_station]
        if current_tree.exists(new_item_id):
            current_tree.selection_set(new_item_id)
            current_tree.see(new_item_id)
            self.on_message_select(None)

    def save_changes(self):
        if self.station_changes_pending[self.current_station]:
            logging.info(f"Saving message configuration changes for station {self.current_station}...")
            # Ensure the manager has the current list reference before saving
            self.config_manager.set_station_messages(self.current_station, self.station_messages[self.current_station])
            self.config_manager.save_config()
            self.station_changes_pending[self.current_station] = False
            return True
        return False

    def save_and_close(self):
        # Save changes for all stations that have pending changes
        for station_id in self.station_changes_pending:
            if self.station_changes_pending[station_id]:
                self.current_station = station_id
                self.save_changes()
        self.destroy()

    def on_close(self):
        # Check if any station has unsaved changes
        has_changes = any(self.station_changes_pending.values())
        if has_changes:
            response = messagebox.askyesnocancel("Unsaved Changes", "Save changes before closing?", parent=self)
            if response is True: self.save_and_close()
            elif response is False: self.destroy()
            # else: Cancel, do nothing
        else: self.destroy()

# Example usage for testing
if __name__ == "__main__":
    print("This script defines the ConfigWindow UI component.")
    # root = tk.Tk()
    # class MockConfig: # Define mocks if needed for standalone testing
    #     def get_messages(self): return []
    #     def set_messages(self, m): pass
    #     def save_config(self): pass
    # mock_cfg = MockConfig()
    # ConfigWindow(root, mock_cfg)
    # root.mainloop()
