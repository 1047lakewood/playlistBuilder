import tkinter as tk
from tkinter import ttk, messagebox
import json
from datetime import datetime
import os
import re

class MessageSchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Inovonics RDS Message Scheduler")
        self.root.geometry("1100x650")
        
        # Set a modern theme if available
        try:
            self.root.tk.call("source", "azure.tcl")
            self.root.tk.call("set_theme", "light")
        except tk.TclError:
            pass  # Fallback to default theme
            
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f5f5f5")
        self.style.configure("TButton", font=("Segoe UI", 10))
        self.style.configure("TLabel", font=("Segoe UI", 10))
        self.style.configure("Treeview", rowheight=25)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        
        # Load messages from file
        self.messages_file = "messages.json"
        self.messages = self.load_messages()
        self.selected_index = None
        
        # Track changes for auto-save
        self.changes_pending = False
        self.is_loading_selection = False  # Flag to prevent circular updates
        
        # Create UI
        self.create_widgets()
        
        # Set up auto-save timer (check every 5 seconds)
        self.root.after(5000, self.auto_save_check)
    
    def load_messages(self):
        try:
            with open(self.messages_file, "r") as file:
                return json.load(file).get("Messages", [])
        except (FileNotFoundError, json.JSONDecodeError):
            # Create a backup if file exists but is corrupted
            if os.path.exists(self.messages_file):
                backup_name = f"messages_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                try:
                    os.rename(self.messages_file, backup_name)
                except:
                    pass
            return []
    
    def save_messages(self):
        try:
            with open(self.messages_file, "w") as file:
                json.dump({"Messages": self.messages}, file, indent=4)
            self.changes_pending = False
            self.update_status("Changes saved")
        except Exception as e:
            self.update_status(f"Error saving: {str(e)}")
    
    def auto_save_check(self):
        if self.changes_pending:
            self.save_messages()
        self.root.after(5000, self.auto_save_check)
    
    def update_status(self, message, clear_after=3000):
        self.status_var.set(message)
        # Clear status after delay
        if clear_after:
            self.root.after(clear_after, lambda: self.status_var.set(""))
    
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title and description
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="RDS Message Scheduler", 
                               font=("Segoe UI", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # Split view - messages list on left, details on right
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Message list frame (left side)
        list_frame = ttk.LabelFrame(paned, text="Scheduled Messages")
        
        # Toolbar for list operations
        list_toolbar = ttk.Frame(list_frame)
        list_toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(list_toolbar, text="Add New", command=self.add_message).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_toolbar, text="Delete", command=self.delete_message).pack(side=tk.LEFT, padx=2)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Text", "Enabled", "Scheduled", "Duration", "Days", "Times"), 
                               show='headings', selectmode="browse")
        self.tree.heading("Text", text="Message", anchor=tk.W)
        self.tree.heading("Enabled", text="Enabled", anchor=tk.CENTER)
        self.tree.heading("Scheduled", text="Use Schedule", anchor=tk.CENTER)
        self.tree.heading("Duration", text="Duration (s)", anchor=tk.CENTER)
        self.tree.heading("Days", text="Days", anchor=tk.W)
        self.tree.heading("Times", text="Times", anchor=tk.W)
        
        # Column widths
        self.tree.column("Text", width=180, stretch=True)
        self.tree.column("Enabled", width=60, stretch=False, anchor=tk.CENTER)
        self.tree.column("Scheduled", width=90, stretch=False, anchor=tk.CENTER)
        self.tree.column("Duration", width=80, stretch=False, anchor=tk.CENTER)
        self.tree.column("Days", width=150, stretch=True)
        self.tree.column("Times", width=100, stretch=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for tree and scrollbars
        self.tree.grid(column=0, row=0, sticky="nsew")
        vsb.grid(column=1, row=0, sticky="ns")
        hsb.grid(column=0, row=1, sticky="ew")
        
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_message_select)
        
        # Message details frame (right side)
        details_frame = ttk.LabelFrame(paned, text="Message Details")
        
        # Add both frames to the paned window
        paned.add(list_frame, weight=1)
        paned.add(details_frame, weight=2)
        
        # Details content
        details_content = ttk.Frame(details_frame, padding=(10, 5))
        details_content.pack(fill=tk.BOTH, expand=True)
        
        # Message content section
        message_frame = ttk.LabelFrame(details_content, text="Message Content (64 char max)")
        message_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Use Entry widget instead of Text for character limit
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(message_frame, textvariable=self.message_var, font=("Segoe UI", 10), width=64)
        self.message_entry.pack(fill=tk.X, padx=5, pady=10)
        
        # Character count label
        self.char_count_var = tk.StringVar(value="0/64")
        char_count_label = ttk.Label(message_frame, textvariable=self.char_count_var, anchor=tk.E)
        char_count_label.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Track characters and limit to 64
        def update_char_count(*args):
            if self.is_loading_selection:
                return
            
            text = self.message_var.get()
            count = len(text)
            if count > 64:
                # Truncate to 64 characters
                self.message_var.set(text[:64])
                count = 64
            
            self.char_count_var.set(f"{count}/64")
            self.mark_changes()
            
        self.message_var.trace_add("write", update_char_count)
        
        # Settings section
        settings_frame = ttk.LabelFrame(details_content, text="Message Settings")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid layout for settings
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill=tk.X, padx=5, pady=5)
        
        # Enabled checkbox
        self.enable_var = tk.BooleanVar()
        enable_check = ttk.Checkbutton(settings_grid, text="Message Enabled", variable=self.enable_var, 
                                     command=self.mark_changes)
        enable_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Duration
        ttk.Label(settings_grid, text="Duration (seconds):").grid(row=0, column=1, sticky=tk.W, padx=(20, 5), pady=5)
        self.duration_var = tk.StringVar()
        duration_spin = ttk.Spinbox(settings_grid, from_=1, to=60, width=5, textvariable=self.duration_var)
        duration_spin.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.duration_var.trace_add("write", lambda *args: self.mark_changes())
        
        # Schedule section
        schedule_frame = ttk.LabelFrame(details_content, text="Message Schedule")
        schedule_frame.pack(fill=tk.X)
        
        # Use schedule checkbox
        schedule_options = ttk.Frame(schedule_frame)
        schedule_options.pack(fill=tk.X, padx=5, pady=5)
        
        self.use_schedule_var = tk.BooleanVar()
        schedule_check = ttk.Checkbutton(schedule_options, text="Use Scheduling", 
                                       variable=self.use_schedule_var,
                                       command=self.toggle_schedule_controls)
        schedule_check.pack(anchor=tk.W)
        
        # Help text
        schedule_help = ttk.Label(schedule_options, 
                                text="If unchecked, message will always display when enabled", 
                                font=("Segoe UI", 9), foreground="#666666")
        schedule_help.pack(anchor=tk.W, pady=(0, 5))
        
        # Schedule container that can be enabled/disabled
        self.schedule_container = ttk.Frame(schedule_frame)
        self.schedule_container.pack(fill=tk.X, padx=5, pady=5)
        
        # Days selection with better layout
        days_frame = ttk.Frame(self.schedule_container)
        days_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(days_frame, text="Schedule Days:").grid(row=0, column=0, sticky=tk.W)
        
        self.days_vars = {}
        day_labels = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        days_checks_frame = ttk.Frame(days_frame)
        days_checks_frame.grid(row=1, column=0, sticky=tk.W)
        
        for i, day in enumerate(day_labels):
            self.days_vars[day] = tk.BooleanVar()
            check = ttk.Checkbutton(days_checks_frame, text=day, variable=self.days_vars[day], 
                                  command=self.mark_changes)
            row, col = divmod(i, 4)
            check.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
        
        # Times entry
        times_frame = ttk.Frame(self.schedule_container)
        times_frame.pack(fill=tk.X, pady=5)
        
        times_label = ttk.Label(times_frame, text="Schedule Times (24h format, comma-separated):")
        times_label.pack(anchor=tk.W)
        
        # Updated example for time format (hours only)
        example_label = ttk.Label(times_frame, 
                                text="Examples: '9, 14, 23' or '13-16, 20, 21'", 
                                font=("Segoe UI", 9), foreground="#666666")
        example_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.time_entry = ttk.Entry(times_frame, font=("Segoe UI", 10))
        self.time_entry.pack(fill=tk.X, pady=2)
        self.time_entry.bind("<KeyRelease>", lambda e: self.mark_changes())
        
        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        # Load messages into tree
        self.load_messages_into_tree()
        
        # Disable details editing initially until selection
        self.set_details_state(tk.DISABLED)
    
    def toggle_schedule_controls(self):
        """Enable or disable schedule controls based on use_schedule checkbox"""
        if self.is_loading_selection:
            return
            
        new_state = "normal" if self.use_schedule_var.get() else "disabled"

        def recursive_configure(current_widget):
            for child in current_widget.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Spinbox, ttk.Checkbutton, ttk.Button)):
                    child.configure(state=new_state)
                recursive_configure(child)

        recursive_configure(self.schedule_container)
                    
        self.mark_changes()
    
    def set_details_state(self, state):
        self.message_entry.configure(state=state)
        if state == tk.DISABLED:
            self.message_var.set("")
            self.enable_var.set(False)
            self.use_schedule_var.set(False)
            self.duration_var.set("10")
            for var in self.days_vars.values():
                var.set(False)
            self.time_entry.delete(0, tk.END)
    
    def load_messages_into_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, msg in enumerate(self.messages):
            days = ", ".join(msg.get("Scheduled", {}).get("Days", []))
            
            # Format times for display (hours only)
            time_list = msg.get("Scheduled", {}).get("Times", [])
            formatted_times = []
            for time_item in time_list:
                if isinstance(time_item, dict) and "hour" in time_item:
                    hour = time_item["hour"]
                    formatted_times.append(f"{hour}")
                elif isinstance(time_item, (int, float)):
                    # Legacy format - just hour
                    formatted_times.append(f"{int(time_item)}")
                else:
                    # Unknown format
                    formatted_times.append(str(time_item))
                    
            times = ", ".join(formatted_times)
            
            enabled = "Yes" if msg.get("Enabled", False) else "No"
            scheduled = "Yes" if msg.get("Scheduled", {}).get("Enabled", False) else "No"
            
            # Truncate message text if too long
            text = msg.get("Text", "")
            if len(text) > 30:
                text = text[:27] + "..."
                
            self.tree.insert("", tk.END, values=(
                text, 
                enabled, 
                scheduled,
                msg.get("Message Time", 10), 
                days, 
                times
            ), tags=(f"item{i}",))
            
        # Alternate row colors
        for i in range(len(self.messages)):
            if i % 2 == 0:
                self.tree.tag_configure(f"item{i}", background="#f0f0f0")
    
    def mark_changes(self, *args):
        """Mark that changes are pending and need to be saved"""
        if self.selected_index is not None and not self.is_loading_selection:
            self.changes_pending = True
            self.update_status("Changes pending...")
            self.update_current_message()
    
    def update_current_message(self):
        """Update the current message in the data model without saving to file"""
        if self.selected_index is None or self.is_loading_selection:
            return
            
        try:
            self.messages[self.selected_index]["Text"] = self.message_var.get()
            self.messages[self.selected_index]["Enabled"] = self.enable_var.get()
            
            # Ensure valid duration
            try:
                duration = int(self.duration_var.get())
                if duration < 1 or duration > 60:
                    duration = 10
            except ValueError:
                duration = 10
                
            self.messages[self.selected_index]["Message Time"] = duration
            
            # Update scheduling information
            use_schedule = self.use_schedule_var.get()
            self.messages[self.selected_index]["Scheduled"] = {
                "Enabled": use_schedule,
                "Days": [day for day, var in self.days_vars.items() if var.get()] if use_schedule else [],
                "Times": self.parse_times() if use_schedule else []
            }
            
            # Update treeview only if there's a selection
            selected_items = self.tree.selection()
            if selected_items:
                selected_item = selected_items[0]
                days = ", ".join(self.messages[self.selected_index]["Scheduled"]["Days"])
                
                # Format times for display (hours only)
                time_list = self.messages[self.selected_index]["Scheduled"]["Times"]
                formatted_times = []
                for time_item in time_list:
                    if isinstance(time_item, dict) and "hour" in time_item:
                        hour = time_item["hour"]
                        formatted_times.append(f"{hour}")
                    elif isinstance(time_item, (int, float)):
                        # Legacy format - just hour
                        formatted_times.append(f"{int(time_item)}")
                    else:
                        # Unknown format
                        formatted_times.append(str(time_item))
                        
                times = ", ".join(formatted_times)
                
                enabled = "Yes" if self.messages[self.selected_index]["Enabled"] else "No"
                scheduled = "Yes" if self.messages[self.selected_index]["Scheduled"]["Enabled"] else "No"
                
                # Truncate message text if too long
                text = self.messages[self.selected_index]["Text"]
                if len(text) > 30:
                    text = text[:27] + "..."
                    
                self.tree.item(selected_item, values=(
                    text, 
                    enabled,
                    scheduled,
                    self.messages[self.selected_index]["Message Time"],
                    days,
                    times
                ))
        except Exception as e:
            self.update_status(f"Error updating: {str(e)}")
    
    def parse_times(self):
        """Parse and validate times from the time entry field.
        Now supports hour-only format (9, 14, 23) and time ranges (13-16)"""
        time_str = self.time_entry.get().strip()
        if not time_str:
            return []
            
        times = []
        for t in time_str.split(','):
            t = t.strip()
            
            # First check for time range (e.g., 13-16)
            range_match = re.match(r'^(\d{1,2})-(\d{1,2})$', t)
            if range_match:
                start_hour = int(range_match.group(1))
                end_hour = int(range_match.group(2))
                if 0 <= start_hour <= 23 and 0 <= end_hour <= 23 and start_hour < end_hour:
                    for hour in range(start_hour, end_hour + 1):
                        times.append({"hour": hour, "minute": 0})
                continue
            
            # Try to match hour-only format
            try:
                hour = int(t)
                if 0 <= hour <= 23:
                    times.append({"hour": hour, "minute": 0})
            except ValueError:
                pass  # Skip invalid entries
                
        return times
    
    def validate_times(self):
        """Validate the times entered in the time entry field and provide feedback"""
        time_str = self.time_entry.get().strip()
        if not time_str:
            self.update_status("No times entered")
            return
            
        valid_times = []
        invalid_times = []
        
        for t in time_str.split(','):
            t = t.strip()
            if not t:
                continue
                
            # Check hour-only format
            try:
                hour = int(t)
                if 0 <= hour <= 23:
                    valid_times.append(f"{hour}")
                else:
                    invalid_times.append(t)
            except ValueError:
                # Check for range format
                range_match = re.match(r'^(\d{1,2})-(\d{1,2})$', t)
                if range_match:
                    start_hour = int(range_match.group(1))
                    end_hour = int(range_match.group(2))
                    if 0 <= start_hour <= 23 and 0 <= end_hour <= 23 and start_hour < end_hour:
                        # For display purposes, show the range
                        valid_times.append(f"{start_hour}-{end_hour}")
                    else:
                        invalid_times.append(t)
                else:
                    invalid_times.append(t)
        
        if invalid_times:
            self.update_status(f"Invalid times: {', '.join(invalid_times)}", 5000)
        elif valid_times:
            valid_times_str = ", ".join(valid_times)
            self.update_status(f"Valid times: {valid_times_str}", 3000)
        else:
            self.update_status("No valid times entered", 3000)
    
    def on_message_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_index = None
            self.set_details_state(tk.DISABLED)
            return
            
        selected_item = selected_items[0]
        item_index = self.tree.index(selected_item)
        
        # Save previous changes if there are any
        if self.changes_pending:
            self.save_messages()
        
        self.selected_index = item_index
        message = self.messages[item_index]
        
        # Set loading flag to prevent circular updates
        self.is_loading_selection = True
        
        # Enable details editing
        self.set_details_state(tk.NORMAL)
        
        # Update details
        self.message_var.set(message.get("Text", "")[:64])  # Limit to 64 chars
        self.char_count_var.set(f"{len(self.message_var.get())}/64")
        
        self.enable_var.set(message.get("Enabled", False))
        self.duration_var.set(message.get("Message Time", 10))
        
        # Set scheduling enabled/disabled
        use_schedule = message.get("Scheduled", {}).get("Enabled", False)
        self.use_schedule_var.set(use_schedule)
        
        # Update days
        scheduled_days = message.get("Scheduled", {}).get("Days", [])
        for day, var in self.days_vars.items():
            var.set(day in scheduled_days)
        
        # Update times with hours-only format
        self.time_entry.delete(0, tk.END)
        time_list = message.get("Scheduled", {}).get("Times", [])
        
        formatted_times = []
        for time_item in time_list:
            if isinstance(time_item, dict) and "hour" in time_item:
                # Only display the hour, ignore minutes
                hour = time_item["hour"]
                formatted_times.append(str(hour))
            elif isinstance(time_item, (int, float)):
                # Legacy format - just hour
                formatted_times.append(str(int(time_item)))
            else:
                # Unknown format
                formatted_times.append(str(time_item))
                
        self.time_entry.insert(0, ", ".join(formatted_times))
        
        # Enable/disable schedule controls based on use_schedule
        state = "normal" if use_schedule else "disabled"
        def configure_children(parent):
            for child in parent.winfo_children():
                if isinstance(child, (ttk.Entry, ttk.Spinbox, ttk.Checkbutton, ttk.Button)):
                    child.configure(state=state)
                configure_children(child)  # Recursively process child widgets

        configure_children(self.schedule_container)
        
        # Clear loading flag
        self.is_loading_selection = False
    
    def add_message(self):
        new_message = {
            "Text": "New Message",
            "Enabled": False,
            "Message Time": 10,
            "Scheduled": {"Enabled": False, "Days": [], "Times": []}
        }
        self.messages.append(new_message)
        self.changes_pending = True
        self.load_messages_into_tree()
        
        # Select the new message
        last_item = self.tree.get_children()[-1]
        self.tree.selection_set(last_item)
        self.tree.see(last_item)
        self.on_message_select(None)
        
        self.update_status("New message added")
    
    def delete_message(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        item_index = self.tree.index(selected_items[0])
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this message?"):
            del self.messages[item_index]
            self.changes_pending = True
            self.load_messages_into_tree()
            self.selected_index = None
            self.set_details_state(tk.DISABLED)
            self.update_status("Message deleted")

if __name__ == "__main__":
    root = tk.Tk()
    app = MessageSchedulerGUI(root)
    root.mainloop()