import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import re
import logging

# Placeholder for ConfigManager if needed directly (passed in constructor)
# from config_manager import ConfigManager

class ConfigWindow(Toplevel):
    """Window for configuring RDS messages (add, delete, edit, schedule)."""
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.transient(parent) # Keep window on top of parent
        self.grab_set() # Modal behavior
        self.title("Configure RDS Messages")
        self.geometry("1150x700") # Slightly larger for potential future additions

        self.config_manager = config_manager
        # Get a reference to the list; changes here will be reflected in the manager's list
        # if the manager returns a direct reference. If it returns a copy, we need to update it on save.
        # Assuming ConfigManager handles the state internally and we just tell it to save.
        self.messages = self.config_manager.get_messages()
        self.selected_index = None
        self.changes_pending = False
        self.is_loading_selection = False

        # Use parent's theme settings if possible (ttkthemes applies globally)
        self.style = ttk.Style() # Inherit style from parent

        self.create_widgets()
        self.load_messages_into_tree()

        # Handle closing the window
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Split view - messages list on left, details on right
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
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

        self.tree = ttk.Treeview(tree_frame, columns=("Text", "Enabled", "Scheduled", "Duration", "Days", "Times"),
                               show='headings', selectmode="browse")
        self.tree.heading("Text", text="Message", anchor=tk.W)
        self.tree.heading("Enabled", text="Enabled", anchor=tk.CENTER)
        self.tree.heading("Scheduled", text="Use Sched", anchor=tk.CENTER)
        self.tree.heading("Duration", text="Dur (s)", anchor=tk.CENTER)
        self.tree.heading("Days", text="Days", anchor=tk.W)
        self.tree.heading("Times", text="Times (Hr)", anchor=tk.W)

        self.tree.column("Text", width=200, stretch=True)
        self.tree.column("Enabled", width=60, stretch=False, anchor=tk.CENTER)
        self.tree.column("Scheduled", width=70, stretch=False, anchor=tk.CENTER)
        self.tree.column("Duration", width=60, stretch=False, anchor=tk.CENTER)
        self.tree.column("Days", width=150, stretch=True)
        self.tree.column("Times", width=100, stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_message_select)

        # --- Message details frame (right side) ---
        details_frame = ttk.LabelFrame(paned, text="Message Details")
        paned.add(list_frame, weight=1)
        paned.add(details_frame, weight=2)

        details_content = ttk.Frame(details_frame, padding=(10, 5))
        details_content.pack(fill=tk.BOTH, expand=True)

        message_frame = ttk.LabelFrame(details_content, text="Message Content (64 char max)")
        message_frame.pack(fill=tk.X, pady=(0, 10))

        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(message_frame, textvariable=self.message_var, font=("Segoe UI", 10), width=64)
        self.message_entry.pack(fill=tk.X, padx=5, pady=5)

        self.char_count_var = tk.StringVar(value="0/64")
        char_count_label = ttk.Label(message_frame, textvariable=self.char_count_var, anchor=tk.E)
        char_count_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.message_var.trace_add("write", self.update_char_count)

        settings_frame = ttk.LabelFrame(details_content, text="Message Settings")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill=tk.X, padx=5, pady=5)

        self.enable_var = tk.BooleanVar()
        enable_check = ttk.Checkbutton(settings_grid, text="Message Enabled", variable=self.enable_var, command=self.mark_changes)
        enable_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        ttk.Label(settings_grid, text="Duration (seconds):").grid(row=0, column=1, sticky=tk.W, padx=(20, 5), pady=5)
        self.duration_var = tk.StringVar()
        vcmd = (self.register(self.validate_duration), '%P')
        duration_spin = ttk.Spinbox(settings_grid, from_=1, to=60, width=5, textvariable=self.duration_var, validate='key', validatecommand=vcmd)
        duration_spin.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.duration_var.trace_add("write", lambda *args: self.mark_changes())

        schedule_frame = ttk.LabelFrame(details_content, text="Message Schedule")
        schedule_frame.pack(fill=tk.X)
        schedule_options = ttk.Frame(schedule_frame)
        schedule_options.pack(fill=tk.X, padx=5, pady=5)

        self.use_schedule_var = tk.BooleanVar()
        schedule_check = ttk.Checkbutton(schedule_options, text="Use Scheduling", variable=self.use_schedule_var, command=self.toggle_schedule_controls)
        schedule_check.pack(anchor=tk.W)
        schedule_help = ttk.Label(schedule_options, text="If unchecked, message will always display when enabled (subject to artist filters)", font=("Segoe UI", 9), foreground="#666666")
        schedule_help.pack(anchor=tk.W, pady=(0, 5))

        self.schedule_container = ttk.Frame(schedule_frame)
        self.schedule_container.pack(fill=tk.X, padx=5, pady=5)

        days_frame = ttk.Frame(self.schedule_container)
        days_frame.pack(fill=tk.X, pady=5)
        ttk.Label(days_frame, text="Schedule Days:").grid(row=0, column=0, sticky=tk.W)
        self.days_vars = {}
        day_labels = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        days_checks_frame = ttk.Frame(days_frame)
        days_checks_frame.grid(row=1, column=0, sticky=tk.W)
        for i, day in enumerate(day_labels):
            self.days_vars[day] = tk.BooleanVar()
            check = ttk.Checkbutton(days_checks_frame, text=day, variable=self.days_vars[day], command=self.mark_changes)
            row, col = divmod(i, 4)
            check.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)

        times_frame = ttk.Frame(self.schedule_container)
        times_frame.pack(fill=tk.X, pady=5)
        times_label = ttk.Label(times_frame, text="Schedule Hours (24h format, comma-separated):")
        times_label.pack(anchor=tk.W)
        example_label = ttk.Label(times_frame, text="Examples: '9, 14, 23' (specific hours) or '13-16' (range)", font=("Segoe UI", 9), foreground="#666666")
        example_label.pack(anchor=tk.W, pady=(0, 5))
        self.time_entry = ttk.Entry(times_frame, font=("Segoe UI", 10))
        self.time_entry.pack(fill=tk.X, pady=2)
        self.time_entry.bind("<KeyRelease>", lambda e: self.mark_changes())

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Save Changes", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side=tk.RIGHT, padx=5)

        self.set_details_state(tk.DISABLED)

    def validate_duration(self, P):
        if P == "": return True
        try:
            val = int(P)
            return 1 <= val <= 60
        except ValueError:
            return False

    def update_char_count(self, *args):
        if self.is_loading_selection: return
        text = self.message_var.get()
        count = len(text)
        if count > 64:
            self.message_var.set(text[:64])
            count = 64
        self.char_count_var.set(f"{count}/64")
        self.mark_changes()

    def toggle_schedule_controls(self):
        if self.is_loading_selection: return
        new_state = tk.NORMAL if self.use_schedule_var.get() else tk.DISABLED
        def recursive_configure(widget, state):
            try:
                if isinstance(widget, (ttk.Checkbutton, ttk.Entry, ttk.Spinbox, ttk.Button)):
                     widget.configure(state=state)
                for child in widget.winfo_children():
                    recursive_configure(child, state)
            except tk.TclError: pass
        recursive_configure(self.schedule_container, new_state)
        self.mark_changes()

    def set_details_state(self, state):
        duration_spinbox = None
        # Simplified search for spinbox assuming structure
        try:
            settings_grid = self.enable_var.master # settings_grid
            for widget in settings_grid.winfo_children():
                 if isinstance(widget, ttk.Spinbox):
                     duration_spinbox = widget
                     break
        except Exception: pass # Ignore if structure changes

        if duration_spinbox: duration_spinbox.config(state=state)

        # Toggle Checkbuttons in settings_grid
        try:
            settings_grid = self.enable_var.master
            for widget in settings_grid.winfo_children():
                 if isinstance(widget, ttk.Checkbutton):
                     widget.config(state=state)
        except Exception: pass

        # Toggle schedule container children
        schedule_state = state if self.use_schedule_var.get() else tk.DISABLED
        def recursive_configure(widget, current_state):
             try:
                 if isinstance(widget, (ttk.Checkbutton, ttk.Entry, ttk.Spinbox, ttk.Button)):
                     widget.configure(state=current_state)
                 for child in widget.winfo_children():
                     recursive_configure(child, current_state)
             except tk.TclError: pass
        recursive_configure(self.schedule_container, schedule_state if state == tk.NORMAL else tk.DISABLED)

        self.message_entry.config(state=state)
        # Time entry state depends on both main state and schedule checkbox
        self.time_entry.config(state=schedule_state if state == tk.NORMAL else tk.DISABLED)

        if state == tk.DISABLED:
            self.is_loading_selection = True
            self.message_var.set("")
            self.char_count_var.set("0/64")
            self.enable_var.set(False)
            self.duration_var.set("10")
            self.use_schedule_var.set(False)
            for var in self.days_vars.values(): var.set(False)
            self.time_entry.delete(0, tk.END)
            self.is_loading_selection = False

    def load_messages_into_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, msg in enumerate(self.messages):
            days = ", ".join(msg.get("Scheduled", {}).get("Days", []))
            time_list = msg.get("Scheduled", {}).get("Times", [])
            formatted_times = []
            for time_item in time_list:
                if isinstance(time_item, dict) and "hour" in time_item: formatted_times.append(f"{time_item['hour']}")
                elif isinstance(time_item, (int, float)): formatted_times.append(f"{int(time_item)}")
            times = ", ".join(formatted_times)
            enabled = "Yes" if msg.get("Enabled", False) else "No"
            scheduled = "Yes" if msg.get("Scheduled", {}).get("Enabled", False) else "No"
            text = msg.get("Text", "")
            display_text = (text[:27] + "...") if len(text) > 30 else text
            self.tree.insert("", tk.END, iid=f"item{i}", values=(display_text, enabled, scheduled, msg.get("Message Time", 10), days, times))

    def mark_changes(self, *args):
        if self.selected_index is not None and not self.is_loading_selection:
            self.changes_pending = True
            self.update_current_message_data()

    def update_current_message_data(self):
        if self.selected_index is None or self.is_loading_selection: return
        try:
            current_msg = self.messages[self.selected_index]
            current_msg["Text"] = self.message_var.get()
            current_msg["Enabled"] = self.enable_var.get()
            try:
                duration = int(self.duration_var.get())
                current_msg["Message Time"] = duration if 1 <= duration <= 60 else 10
            except ValueError: current_msg["Message Time"] = 10
            use_schedule = self.use_schedule_var.get()
            current_msg["Scheduled"] = {"Enabled": use_schedule, "Days": [day for day, var in self.days_vars.items() if var.get()] if use_schedule else [], "Times": self.parse_times() if use_schedule else []}
            self.update_treeview_item(self.selected_index)
        except IndexError:
             logging.error(f"Selected index {self.selected_index} out of bounds.")
             self.selected_index = None; self.set_details_state(tk.DISABLED)
        except Exception as e:
            logging.exception(f"Error updating message data: {e}")
            messagebox.showerror("Error", f"Error updating message details:\n{e}", parent=self)

    def update_treeview_item(self, index):
         try:
             item_id = f"item{index}"
             if not self.tree.exists(item_id): return
             msg = self.messages[index]
             days = ", ".join(msg.get("Scheduled", {}).get("Days", []))
             time_list = msg.get("Scheduled", {}).get("Times", [])
             formatted_times = [f"{t['hour']}" for t in time_list if isinstance(t, dict) and 'hour' in t]
             times = ", ".join(formatted_times)
             enabled = "Yes" if msg.get("Enabled", False) else "No"
             scheduled = "Yes" if msg.get("Scheduled", {}).get("Enabled", False) else "No"
             text = msg.get("Text", "")
             display_text = (text[:27] + "...") if len(text) > 30 else text
             self.tree.item(item_id, values=(display_text, enabled, scheduled, msg.get("Message Time", 10), days, times))
         except IndexError: logging.warning(f"Update treeview invalid index {index}")
         except Exception as e: logging.exception(f"Error updating treeview item {index}: {e}")

    def parse_times(self):
        time_str = self.time_entry.get().strip(); times_list = []
        if not time_str: return times_list
        for part in time_str.split(','):
            part = part.strip();
            if not part: continue
            range_match = re.match(r'^(\d{1,2})-(\d{1,2})$', part)
            if range_match:
                try:
                    start, end = int(range_match.group(1)), int(range_match.group(2))
                    if 0 <= start <= 23 and 0 <= end <= 23 and start <= end:
                        for hour in range(start, end + 1):
                            time_obj = {"hour": hour}
                            if time_obj not in times_list: times_list.append(time_obj)
                    else: logging.warning(f"Invalid hour range: {part}")
                except ValueError: logging.warning(f"Invalid number in range: {part}")
            else:
                try:
                    hour = int(part)
                    if 0 <= hour <= 23:
                         time_obj = {"hour": hour}
                         if time_obj not in times_list: times_list.append(time_obj)
                    else: logging.warning(f"Invalid hour: {part}")
                except ValueError: logging.warning(f"Invalid time format: {part}")
        times_list.sort(key=lambda x: x['hour']); return times_list

    def on_message_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items: self.selected_index = None; self.set_details_state(tk.DISABLED); return
        selected_item_id = selected_items[0]
        try: item_index = int(selected_item_id.replace("item", ""))
        except (ValueError, IndexError): logging.error(f"Bad index from ID: {selected_item_id}"); self.selected_index = None; self.set_details_state(tk.DISABLED); return
        self.selected_index = item_index
        try: message = self.messages[item_index]
        except IndexError: logging.error(f"Index {item_index} out of range."); self.selected_index = None; self.set_details_state(tk.DISABLED); return
        self.is_loading_selection = True
        self.set_details_state(tk.NORMAL)
        self.message_var.set(message.get("Text", "")[:64])
        self.char_count_var.set(f"{len(self.message_var.get())}/64")
        self.enable_var.set(message.get("Enabled", False))
        self.duration_var.set(message.get("Message Time", 10))
        use_schedule = message.get("Scheduled", {}).get("Enabled", False)
        self.use_schedule_var.set(use_schedule)
        scheduled_days = message.get("Scheduled", {}).get("Days", [])
        for day, var in self.days_vars.items(): var.set(day in scheduled_days)
        time_list = message.get("Scheduled", {}).get("Times", [])
        formatted_times = [f"{t['hour']}" for t in time_list if isinstance(t, dict) and 'hour' in t]
        self.time_entry.delete(0, tk.END); self.time_entry.insert(0, ", ".join(formatted_times))
        # self.toggle_schedule_controls() # Set state based on checkbox # <<< MOVED
        self.is_loading_selection = False
        self.toggle_schedule_controls() # <<< MOVED HERE: Ensure controls update after loading flag is off

    def add_message(self):
        new_message = {"Text": "New Message", "Enabled": False, "Message Time": 10, "Scheduled": {"Enabled": False, "Days": [], "Times": []}}
        self.messages.append(new_message); self.changes_pending = True
        new_index = len(self.messages) - 1
        self.load_messages_into_tree()
        new_item_id = f"item{new_index}"
        if self.tree.exists(new_item_id):
            self.tree.selection_set(new_item_id); self.tree.see(new_item_id); self.on_message_select(None)
        else: logging.error("Failed to find new item in tree.")

    def delete_message(self):
        if self.selected_index is None: messagebox.showwarning("No Selection", "Please select a message to delete.", parent=self); return
        # if messagebox.askyesno("Confirm Delete", f"Delete message:\n'{self.messages[self.selected_index].get('Text', '')[:30]}...'?", parent=self):
        del self.messages[self.selected_index]; self.changes_pending = True
        original_selection_index = self.selected_index
        self.load_messages_into_tree(); self.selected_index = None; self.set_details_state(tk.DISABLED)
        if self.messages:
                new_selection_index = min(original_selection_index, len(self.messages) - 1)
                new_item_id = f"item{new_selection_index}"
                if self.tree.exists(new_item_id): self.tree.selection_set(new_item_id); self.tree.see(new_item_id); self.on_message_select(None)

    def move_message_up(self):
        if self.selected_index is None or self.selected_index == 0: return
        idx = self.selected_index
        self.messages.insert(idx - 1, self.messages.pop(idx)); self.changes_pending = True
        new_item_id = f"item{idx - 1}"
        self.load_messages_into_tree()
        if self.tree.exists(new_item_id): self.tree.selection_set(new_item_id); self.tree.see(new_item_id); self.on_message_select(None)

    def move_message_down(self):
        if self.selected_index is None or self.selected_index >= len(self.messages) - 1: return
        idx = self.selected_index
        self.messages.insert(idx + 1, self.messages.pop(idx)); self.changes_pending = True
        new_item_id = f"item{idx + 1}"
        self.load_messages_into_tree()
        if self.tree.exists(new_item_id): self.tree.selection_set(new_item_id); self.tree.see(new_item_id); self.on_message_select(None)

    def save_changes(self):
        if self.changes_pending:
            logging.info("Saving message configuration changes...")
            # Ensure the manager has the current list reference before saving
            self.config_manager.set_messages(self.messages)
            self.config_manager.save_config()
            self.changes_pending = False
            return True
        return False

    def save_and_close(self):
        self.save_changes(); self.destroy()

    def on_close(self):
        if self.changes_pending:
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
