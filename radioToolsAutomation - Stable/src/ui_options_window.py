#  --- Ad Inserter Settings Section ---.*?ttk.Button(ad_frame, text="Browse".*?
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, filedialog
import logging
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from ad_inserter_service import AdInserterService

# Placeholders for managers/handlers if needed directly (passed in constructor)
# from config_manager import ConfigManager
# from intro_loader_handler import IntroLoaderHandler

class OptionsWindow(Toplevel):
    """Window for application options (Whitelist, Blacklist, Debug)."""
    def __init__(self, parent, config_manager, intro_loader_handler_1047, intro_loader_handler_887,
                 auto_rds_handler_1047=None, auto_rds_handler_887=None,
                 ad_scheduler_handler_1047=None, ad_scheduler_handler_887=None):
        """
        Initialize the Options window.

        Args:
            parent: Parent tkinter window
            config_manager: ConfigManager instance
            intro_loader_handler_1047: IntroLoaderHandler for station 1047
            intro_loader_handler_887: IntroLoaderHandler for station 887
            auto_rds_handler_1047: AutoRDSHandler for station 1047
            auto_rds_handler_887: AutoRDSHandler for station 887
            ad_scheduler_handler_1047: AdSchedulerHandler for station 1047
            ad_scheduler_handler_887: AdSchedulerHandler for station 887
        """
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Options")
        self.geometry("800x800")  # Larger to accommodate Migration tab

        self.config_manager = config_manager
        self.intro_1047_handler = intro_loader_handler_1047
        self.intro_887_handler = intro_loader_handler_887
        self.rds_1047_handler = auto_rds_handler_1047
        self.rds_887_handler = auto_rds_handler_887
        self.ad_1047_handler = ad_scheduler_handler_1047
        self.ad_887_handler = ad_scheduler_handler_887

        # Store initial lists to detect changes (shared across stations)
        self.initial_whitelist = self.config_manager.get_shared_whitelist().copy()
        self.initial_blacklist = self.config_manager.get_shared_blacklist().copy()
        self.changes_pending = False # Track if lists were modified

        # Store station-specific variables in dictionaries to avoid conflicts
        self.station_vars = {
            'station_1047': {},
            'station_887': {}
        }

        # Shared volume variables for intro/overlay
        self.volume_vars = {
            'intro_db': tk.DoubleVar(value=self.config_manager.get_shared_setting("intro_loader.volume.intro_db", 0.0)),
            'overlay_db': tk.DoubleVar(value=self.config_manager.get_shared_setting("intro_loader.volume.overlay_db", 0.0))
        }

        # Migration variables
        from migration_utils import MigrationUtils
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Parent of src/
        default_stable = MigrationUtils.get_default_stable_path(app_root)
        self.migration_vars = {
            'stable_path': tk.StringVar(value=self.config_manager.get_shared_setting("migration.stable_path", default_stable))
        }

        # Hour simulation scheduler state per station
        self._hour_sim_after_ids = {"1047": None, "887": None}
        self._hour_sim_status = {"1047": tk.StringVar(value="None"), "887": tk.StringVar(value="None")}

        self.create_widgets()

        self.protocol("WM_DELETE_WINDOW", self.on_close)


    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Bottom Buttons (pack first to ensure they're always visible) ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        ttk.Button(button_frame, text="Save & Close", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side=tk.RIGHT, padx=5)

        # --- Notebook (fills remaining space) ---
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # --- Whitelist Tab ---
        whitelist_frame = ttk.Frame(notebook, padding="10")
        notebook.add(whitelist_frame, text="Artist Whitelist")
        self.whitelist_listbox = self.create_list_editor(
            whitelist_frame,
            "Whitelist",
            self.initial_whitelist # Pass initial list
        )

        # --- Blacklist Tab ---
        blacklist_frame = ttk.Frame(notebook, padding="10")
        notebook.add(blacklist_frame, text="Artist Blacklist")
        self.blacklist_listbox = self.create_list_editor(
            blacklist_frame,
            "Blacklist",
            self.initial_blacklist # Pass initial list
        )

        # --- Station 104.7 FM Settings Tab ---
        station_1047_frame = ttk.Frame(notebook, padding="10")
        notebook.add(station_1047_frame, text="Station 104.7 FM")
        self.create_station_settings_tab(station_1047_frame, "station_1047")

        # --- Station 88.7 FM Settings Tab ---
        station_887_frame = ttk.Frame(notebook, padding="10")
        notebook.add(station_887_frame, text="Station 88.7 FM")
        self.create_station_settings_tab(station_887_frame, "station_887")

        # --- mAirList Schedule Tab ---
        mairlist_frame = ttk.Frame(notebook, padding="10")
        notebook.add(mairlist_frame, text="mAirList Schedule")
        self.create_mairlist_tab(mairlist_frame)

        # --- Intro/Overlay Volume Tab ---
        volume_frame = ttk.Frame(notebook, padding="10")
        notebook.add(volume_frame, text="Intro/Overlay Volume")
        self.create_volume_tab(volume_frame)

        # --- Debug Tab ---
        debug_frame = ttk.Frame(notebook, padding="10")
        notebook.add(debug_frame, text="Debug")
        self.create_debug_tab(debug_frame)

        # --- Migration Tab ---
        migration_frame = ttk.Frame(notebook, padding="10")
        notebook.add(migration_frame, text="Migration")
        self.create_migration_tab(migration_frame)

    def browse_file(self, var, save=False):
        """Opens a file dialog to select a file path and sets the variable."""
        if save:
            path = filedialog.asksaveasfilename(title="Select File", defaultextension=".log")
        else:
            path = filedialog.askopenfilename(title="Select File")
        if path:
            var.set(path)

    def browse_directory(self, var):
        """Opens a directory dialog to select a folder path and sets the variable."""
        path = filedialog.askdirectory(title="Select Directory")
        if path:
            var.set(path)

    def create_list_editor(self, parent_frame, list_name, initial_list):
        """Helper to create the listbox, entry, and buttons for Whitelist/Blacklist."""
        ttk.Label(parent_frame, text=f"Enter artist name exactly as it appears in XML (case-insensitive match):").pack(anchor=tk.W)

        list_container = ttk.Frame(parent_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # Listbox with Scrollbar
        listbox_frame = ttk.Frame(list_container)
        listbox_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 5))

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, exportselection=False, height=10)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Populate Listbox
        for item in initial_list:
            listbox.insert(tk.END, item)

        # Entry and Buttons Frame
        entry_button_frame = ttk.Frame(list_container)
        entry_button_frame.pack(fill=tk.Y, side=tk.LEFT)

        entry_var = tk.StringVar()
        entry = ttk.Entry(entry_button_frame, textvariable=entry_var, width=30)
        entry.pack(pady=(0, 5))

        def mark_change_flag():
            self.changes_pending = True

        def add_item():
            item = entry_var.get().strip()
            if item and item not in listbox.get(0, tk.END):
                listbox.insert(tk.END, item)
                entry_var.set("")
                mark_change_flag() # Mark changes when item added
        ttk.Button(entry_button_frame, text="Add", command=add_item).pack(fill=tk.X, pady=2)

        def delete_item():
            selected_indices = listbox.curselection()
            if selected_indices:
                # Delete from bottom up to avoid index issues
                for i in reversed(selected_indices):
                    listbox.delete(i)
                mark_change_flag() # Mark changes when item deleted
        ttk.Button(entry_button_frame, text="Delete", command=delete_item).pack(fill=tk.X, pady=2)

        # Return the listbox widget so it can be accessed for saving
        return listbox

    def touch_xml_file_action(self):
        """Calls the handler method to touch the XML file, without confirmation."""
        logging.debug("Touch XML File button clicked.")
        try:
            # Call the new method in the handler
            success = self.intro_loader_handler.touch_monitored_xml()
            if success:
                logging.info("Debug touch XML successful via Options window.")
                # Optionally provide non-modal feedback, e.g., update a status label if one existed here
            else:
                logging.error("Debug touch XML failed via Options window. Check logs.")
                # Optionally show error, but user requested no alerts
        except Exception as e:
             logging.exception("Exception calling touch_monitored_xml.")
             # Avoid showing error popup as requested

    def run_ad_service_action(self):
        """Combine ads and trigger the ad inserter URL."""
        logging.debug("Run Ad Service button clicked.")
        try:
            service = AdInserterService(self.config_manager)
            success = service.run()
            if success:
                logging.info("Ad service executed successfully via Options window.")
            else:
                logging.error("Ad service failed via Options window. Check logs.")
        except Exception:
            logging.exception("Exception running AdInserterService.")

    def run_instant_ad_service_action(self):
        """Combine ads and trigger the instant ad URL."""
        logging.debug("Play Ad Now button clicked.")
        try:
            service = AdInserterService(self.config_manager)
            success = service.run_instant()
            if success:
                logging.info("Instant ad executed successfully via Options window.")
            else:
                logging.error("Instant ad failed via Options window. Check logs.")
        except Exception:
            logging.exception("Exception running AdInserterService instant.")

    def simulate_hour_start(self):
        """Simulate the start of an hour for AdScheduler testing."""
        logging.debug("Simulate Hour Start button clicked.")
        try:
            selected_station = self.simulate_station_var.get()
            station_suffix = f"_{selected_station}"

            # Get the appropriate handler based on selected station
            handler_attr = f"ad{station_suffix}_handler"

            if hasattr(self, handler_attr) and getattr(self, handler_attr):
                handler = getattr(self, handler_attr)
                handler._perform_hourly_check()
                logging.info(f"AdScheduler {selected_station} hourly check triggered successfully.")
            else:
                logging.error(f"AdScheduler handler for station {selected_station} not available.")
                messagebox.showerror("Error", f"AdScheduler handler for station {selected_station} not available.", parent=self)
        except Exception as e:
            logging.exception("Exception triggering AdScheduler hourly check.")
            messagebox.showerror("Error", f"Failed to trigger AdScheduler check:\n{e}", parent=self)

    def _compute_next_occurrence(self, minute: int) -> datetime:
        """Compute the next occurrence of the specified minute in the hour."""
        now = datetime.now()
        run_at = now.replace(minute=minute, second=0, microsecond=0)
        if run_at <= now:
            run_at = (now + timedelta(hours=1)).replace(minute=minute, second=0, microsecond=0)
        return run_at

    def schedule_hour_start_at_minute(self):
        """Schedule a one-shot AdScheduler hourly check at the specified minute for the selected station."""
        try:
            selected_station = self.simulate_station_var.get()
            minute = int(self.sim_minute_var.get())

            # Cancel any existing scheduled call for this station
            if self._hour_sim_after_ids[selected_station] is not None:
                self.after_cancel(self._hour_sim_after_ids[selected_station])
                self._hour_sim_after_ids[selected_station] = None

            # Compute next occurrence
            run_at = self._compute_next_occurrence(minute)

            # Calculate delay in milliseconds
            now = datetime.now()
            delay_ms = max(0, int((run_at - now).total_seconds() * 1000))

            # Schedule the call
            def scheduled_callback():
                try:
                    # Clear the after_id and status first
                    self._hour_sim_after_ids[selected_station] = None
                    self._hour_sim_status[selected_station].set("None")

                    # Trigger the hourly check
                    self.simulate_hour_start()
                except Exception as e:
                    logging.exception("Error in scheduled hour start callback.")
                    messagebox.showerror("Scheduled Action Error", f"Failed to execute scheduled hour start:\n{e}", parent=self)

            self._hour_sim_after_ids[selected_station] = self.after(delay_ms, scheduled_callback)

            # Update status
            self._hour_sim_status[selected_station].set(run_at.strftime("%H:%M"))

            logging.info(f"Scheduled hour start for station {selected_station} at {run_at.strftime('%H:%M')}")

        except Exception as e:
            logging.exception("Error scheduling hour start.")
            messagebox.showerror("Scheduling Error", f"Failed to schedule hour start:\n{e}", parent=self)

    def cancel_scheduled_hour_start(self):
        """Cancel any scheduled hour start for the selected station."""
        try:
            selected_station = self.simulate_station_var.get()

            if self._hour_sim_after_ids[selected_station] is not None:
                self.after_cancel(self._hour_sim_after_ids[selected_station])
                self._hour_sim_after_ids[selected_station] = None
                self._hour_sim_status[selected_station].set("None")
                logging.info(f"Cancelled scheduled hour start for station {selected_station}")
            else:
                logging.debug(f"No scheduled hour start to cancel for station {selected_station}")

        except Exception as e:
            logging.exception("Error cancelling scheduled hour start.")
            messagebox.showerror("Cancel Error", f"Failed to cancel scheduled hour start:\n{e}", parent=self)

    def toggle_debug_logging(self):
        """Toggle debug logging on or off immediately."""
        enable_debug = self.enable_debug_logs_var.get()
        
        # Set logging level for all loggers
        log_level = logging.DEBUG if enable_debug else logging.INFO
        
        # Update root logger
        logging.getLogger().setLevel(log_level)
        
        # Update specific loggers
        logging.getLogger('AutoRDS').setLevel(log_level)
        logging.getLogger('IntroLoader').setLevel(log_level)
        logging.getLogger('AdScheduler').setLevel(log_level)
        logging.getLogger('AdService').setLevel(log_level)
        logging.getLogger('AdPlayLogger').setLevel(log_level)
        logging.getLogger('AdStatisticsUI').setLevel(log_level)
        
        status = "enabled" if enable_debug else "disabled"
        logging.info(f"Debug logging {status}")
        
        # Save setting to config
        self.config_manager.update_setting("settings.debug.enable_debug_logs", enable_debug)
        try:
            self.config_manager.save_config()
        except Exception as e:
            logging.error(f"Failed to save debug logging setting: {e}")

    def fetch_mairlist_events(self):
        """Fetch events from mAirList server using the mAirList tab settings."""
        server = self.mairlist_server_entry_var.get().strip()
        password = self.mairlist_password_entry_var.get().strip()
        station_id = self.mairlist_station_var.get()

        if not server:
            messagebox.showerror("Error", "Please enter mAirList server address.", parent=self)
            return

        # Build the URL
        if not server.startswith("http://") and not server.startswith("https://"):
            server = f"http://{server}"
        
        url = f"{server}/?pass={password}&action=schedule&type=list"

        try:
            logging.info(f"Fetching mAirList events from: {url} for {station_id}")
            
            # Fetch the XML
            with urllib.request.urlopen(url, timeout=10) as response:
                xml_data = response.read().decode('utf-8')
            
            # Parse the XML
            root = ET.fromstring(xml_data)
            
            # Clear existing items
            for item in self.mairlist_events_tree.get_children():
                self.mairlist_events_tree.delete(item)
            
            # Parse events
            event_count = 0
            for item in root.findall('item'):
                task_name = item.get('TaskName', '(No Name)')
                event_id = item.get('Id', '')
                enabled = item.get('EnabledEvent', 'False')
                is_immediate = item.get('Imm', 'False') == 'True'
                
                # Determine type
                if is_immediate:
                    event_type = "Immediate"
                else:
                    event_type = "Scheduled"
                
                # Only show events with task names and IDs
                if event_id:
                    self.mairlist_events_tree.insert('', tk.END, values=(task_name, event_id, enabled, event_type))
                    event_count += 1
            
            logging.info(f"Successfully fetched {event_count} events from mAirList for {station_id}")

            # Update the station's mAirList settings and save to config
            self.station_vars[station_id]['mairlist_server'].set(server)
            self.station_vars[station_id]['mairlist_password'].set(password)

            # Save the mAirList settings to config for this station
            self.config_manager.update_station_setting(station_id, "mairlist.server", server)
            self.config_manager.update_station_setting(station_id, "mairlist.password", password)
            self.config_manager.save_config()
            
        except urllib.error.URLError as e:
            logging.error(f"Failed to fetch mAirList events: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect to mAirList:\n{e}", parent=self)
        except ET.ParseError as e:
            logging.error(f"Failed to parse mAirList XML: {e}")
            messagebox.showerror("Parse Error", f"Failed to parse response from mAirList:\n{e}", parent=self)
        except Exception as e:
            logging.exception("Error fetching mAirList events")
            messagebox.showerror("Error", f"An error occurred:\n{e}", parent=self)

    def copy_mairlist_event_url(self):
        """Copy the selected event URL to clipboard."""
        selection = self.mairlist_events_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an event from the list.", parent=self)
            return
        
        item = self.mairlist_events_tree.item(selection[0])
        values = item['values']
        event_id = values[1]  # Event ID is in column 1
        task_name = values[0]  # Task name is in column 0
        
        # Build URL using current settings
        server = self.mairlist_server_entry_var.get().strip()
        password = self.mairlist_password_entry_var.get().strip()
        
        if not server.startswith("http://") and not server.startswith("https://"):
            server = f"http://{server}"
        
        url = f"{server}/?pass={password}&action=schedule&type=run&id={event_id}"
        
        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(url)
        self.update()  # Required for clipboard to work

        logging.info(f"Copied URL for event: {task_name}")

    def save_and_close(self):
        """Saves the whitelist/blacklist if changed and closes."""
        # Get current lists from listboxes
        new_whitelist = list(self.whitelist_listbox.get(0, tk.END))
        new_blacklist = list(self.blacklist_listbox.get(0, tk.END))

        # Check if changes were actually made (or if flag was set)
        if self.changes_pending or new_whitelist != self.initial_whitelist or new_blacklist != self.initial_blacklist:
            try:
                self.config_manager.set_whitelist(new_whitelist)
                self.config_manager.set_blacklist(new_blacklist)
                self.config_manager.save_config()
                logging.info("Whitelist/Blacklist changes saved.")
                self.changes_pending = False # Reset flag after successful save
            except Exception as e:
                 logging.exception("Failed to save Whitelist/Blacklist.")
                 messagebox.showerror("Save Error", f"Failed to save settings:\n{e}", parent=self)
                 return # Don't close if save failed

        # Save settings from both station tabs
        for station_id, station_vars in self.station_vars.items():
            # RDS settings
            self.config_manager.update_station_setting(station_id, "rds.ip", station_vars['rds_ip'].get())
            self.config_manager.update_station_setting(station_id, "rds.port", station_vars['rds_port'].get())
            self.config_manager.update_station_setting(station_id, "rds.now_playing_xml", station_vars['rds_xml'].get())
            self.config_manager.update_station_setting(station_id, "rds.default_message", station_vars['rds_default'].get())

            # Intro Loader settings
            self.config_manager.update_station_setting(station_id, "intro_loader.now_playing_xml", station_vars['loader_xml'].get())
            self.config_manager.update_station_setting(station_id, "intro_loader.mp3_directory", station_vars['loader_mp3_dir'].get())
            self.config_manager.update_station_setting(station_id, "intro_loader.missing_artists_log", station_vars['loader_log'].get())
            self.config_manager.update_station_setting(station_id, "intro_loader.schedule_url", station_vars['loader_url'].get())
            self.config_manager.update_station_setting(station_id, "intro_loader.current_artist_filename", station_vars['current_artist_filename'].get())
            self.config_manager.update_station_setting(station_id, "intro_loader.actual_current_artist_filename", station_vars['actual_current_artist_filename'].get())
            self.config_manager.update_station_setting(station_id, "intro_loader.blank_mp3_filename", station_vars['blank_mp3_filename'].get())
            self.config_manager.update_station_setting(station_id, "intro_loader.silent_mp3_filename", station_vars['silent_mp3_filename'].get())

            # Ad Inserter settings
            self.config_manager.update_station_setting(station_id, "ad_inserter.insertion_url", station_vars['ad_url'].get())
            self.config_manager.update_station_setting(station_id, "ad_inserter.instant_url", station_vars['ad_instant_url'].get())
            self.config_manager.update_station_setting(station_id, "ad_inserter.output_mp3", station_vars['ad_mp3'].get())

            # mAirList settings
            self.config_manager.update_station_setting(station_id, "mairlist.server", station_vars['mairlist_server'].get())
            self.config_manager.update_station_setting(station_id, "mairlist.password", station_vars['mairlist_password'].get())

        # Save shared volume settings
        self.config_manager.update_shared_setting("intro_loader.volume.intro_db", self.volume_vars['intro_db'].get())
        self.config_manager.update_shared_setting("intro_loader.volume.overlay_db", self.volume_vars['overlay_db'].get())

        # Save migration settings
        self.config_manager.update_shared_setting("migration.stable_path", self.migration_vars['stable_path'].get())

        # Save all settings changes to file
        try:
            self.config_manager.save_config()
            logging.info("Settings changes saved for all stations.")
        except Exception as e:
            logging.exception("Failed to save settings.")
            messagebox.showerror("Save Error", f"Failed to save settings:\n{e}", parent=self)
            return # Don't close if save failed

        # Reload configuration in handlers to apply changes immediately
        try:
            self.intro_1047_handler.reload_configuration()
            self.intro_887_handler.reload_configuration()
            logging.info("Intro Loader configurations reloaded for both stations.")
        except Exception as e:
            logging.warning(f"Failed to reload Intro Loader configuration: {e}")

        if self.rds_1047_handler:
            try:
                self.rds_1047_handler.reload_configuration()
                self.rds_1047_handler.reload_lecture_detector()
                logging.info("RDS Handler 104.7 configuration reloaded.")
            except Exception as e:
                logging.warning(f"Failed to reload RDS Handler 104.7 configuration: {e}")

        if self.rds_887_handler:
            try:
                self.rds_887_handler.reload_configuration()
                self.rds_887_handler.reload_lecture_detector()
                logging.info("RDS Handler 88.7 configuration reloaded.")
            except Exception as e:
                logging.warning(f"Failed to reload RDS Handler 88.7 configuration: {e}")

        if self.ad_1047_handler:
            try:
                self.ad_1047_handler.reload_configuration()
                logging.info("Ad Scheduler 104.7 configuration reloaded.")
            except Exception as e:
                logging.warning(f"Failed to reload Ad Scheduler 104.7 configuration: {e}")

        if self.ad_887_handler:
            try:
                self.ad_887_handler.reload_configuration()
                logging.info("Ad Scheduler 88.7 configuration reloaded.")
            except Exception as e:
                logging.warning(f"Failed to reload Ad Scheduler 88.7 configuration: {e}")

        self.destroy()

    def on_close(self):
        """Checks for unsaved changes on close."""
        new_whitelist = list(self.whitelist_listbox.get(0, tk.END))
        new_blacklist = list(self.blacklist_listbox.get(0, tk.END))

        # Check flag first, then compare lists as backup
        if self.changes_pending or new_whitelist != self.initial_whitelist or new_blacklist != self.initial_blacklist:
            response = messagebox.askyesnocancel("Unsaved Changes", "Whitelist or Blacklist has been modified. Save changes before closing?", parent=self)
            if response is True: # Yes
                self.save_and_close()
            elif response is False: # No
                self.destroy() # Close without saving
            # else: Cancel, do nothing
        else:
            self.destroy() # No changes, just close

    def create_mairlist_tab(self, parent_frame):
        """Create the mAirList schedule events tab."""
        title_label = ttk.Label(parent_frame, text="mAirList Schedule Events", font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=(0,10))

        help_label = ttk.Label(
            parent_frame,
            text="Fetch scheduled events from your mAirList server. Select an event and copy its URL to use in Ad Inserter or Intro Loader settings.",
            wraplength=700,
            foreground="gray"
        )
        help_label.pack(pady=(0,10))

        # Station selector
        station_frame = ttk.Frame(parent_frame)
        station_frame.pack(fill=tk.X, pady=5)

        ttk.Label(station_frame, text="Station:").pack(side=tk.LEFT, padx=5)
        self.mairlist_station_var = tk.StringVar(value="station_1047")
        station_combo = ttk.Combobox(station_frame, textvariable=self.mairlist_station_var, 
                                     values=["station_1047", "station_887"], state="readonly", width=15)
        station_combo.pack(side=tk.LEFT, padx=5)

        # Display labels for station name
        ttk.Label(station_frame, text="(104.7 FM or 88.7 FM)").pack(side=tk.LEFT, padx=5)

        # Server configuration
        server_frame = ttk.Frame(parent_frame)
        server_frame.pack(fill=tk.X, pady=10)

        ttk.Label(server_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.mairlist_server_entry_var = tk.StringVar()
        server_entry = ttk.Entry(server_frame, textvariable=self.mairlist_server_entry_var, width=35)
        server_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(server_frame, text="Password:").grid(row=0, column=2, sticky=tk.W, padx=(20,5))
        self.mairlist_password_entry_var = tk.StringVar()
        password_entry = ttk.Entry(server_frame, textvariable=self.mairlist_password_entry_var, width=20, show="*")
        password_entry.grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Button(server_frame, text="Fetch Events", command=self.fetch_mairlist_events).grid(row=0, column=4, padx=(20,5))

        # Update server/password fields when station changes
        def on_station_change(*args):
            station_id = self.mairlist_station_var.get()
            self.mairlist_server_entry_var.set(self.station_vars[station_id]['mairlist_server'].get())
            self.mairlist_password_entry_var.set(self.station_vars[station_id]['mairlist_password'].get())

        # Update station variables when mAirList fields change
        def on_server_change(*args):
            station_id = self.mairlist_station_var.get()
            self.station_vars[station_id]['mairlist_server'].set(self.mairlist_server_entry_var.get())

        def on_password_change(*args):
            station_id = self.mairlist_station_var.get()
            self.station_vars[station_id]['mairlist_password'].set(self.mairlist_password_entry_var.get())

        self.mairlist_station_var.trace('w', on_station_change)
        self.mairlist_server_entry_var.trace('w', on_server_change)
        self.mairlist_password_entry_var.trace('w', on_password_change)
        on_station_change()  # Initialize with current station

        # Events list
        events_list_frame = ttk.Frame(parent_frame)
        events_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Create Treeview with columns
        columns = ("Task Name", "Event ID", "Enabled", "Type")
        self.mairlist_events_tree = ttk.Treeview(events_list_frame, columns=columns, show="headings", height=8)
        
        self.mairlist_events_tree.heading("Task Name", text="Task Name")
        self.mairlist_events_tree.heading("Event ID", text="Event ID")
        self.mairlist_events_tree.heading("Enabled", text="Enabled")
        self.mairlist_events_tree.heading("Type", text="Type")
        
        self.mairlist_events_tree.column("Task Name", width=250)
        self.mairlist_events_tree.column("Event ID", width=250)
        self.mairlist_events_tree.column("Enabled", width=80)
        self.mairlist_events_tree.column("Type", width=100)

        # Scrollbar for tree
        tree_scrollbar = ttk.Scrollbar(events_list_frame, orient=tk.VERTICAL, command=self.mairlist_events_tree.yview)
        self.mairlist_events_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.mairlist_events_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button for copying URL
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Copy URL to Clipboard", command=self.copy_mairlist_event_url).pack(side=tk.LEFT, padx=5)

    def create_volume_tab(self, parent_frame):
        """Create the intro/overlay volume tab with dB sliders."""
        title_label = ttk.Label(parent_frame, text="Intro/Overlay Volume Control", font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=(0, 15))

        # Intro Volume Section
        intro_frame = ttk.Frame(parent_frame)
        intro_frame.pack(fill=tk.X, pady=10)

        ttk.Label(intro_frame, text="Intro Volume (dB):", font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W, padx=5)
        intro_scale = ttk.Scale(
            intro_frame,
            from_=-20.0,
            to=6.0,
            orient=tk.HORIZONTAL,
            variable=self.volume_vars['intro_db'],
            length=300
        )
        intro_scale.grid(row=0, column=1, sticky=tk.W, padx=5)

        intro_value_label = ttk.Label(intro_frame, textvariable=self.volume_vars['intro_db'], width=5)
        intro_value_label.grid(row=0, column=2, sticky=tk.W, padx=5)

        ttk.Label(intro_frame, text="(currentArtist.mp3)", font=("Segoe UI", 9)).grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5)

        # Overlay Volume Section
        overlay_frame = ttk.Frame(parent_frame)
        overlay_frame.pack(fill=tk.X, pady=10)

        ttk.Label(overlay_frame, text="Overlay Volume (dB):", font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W, padx=5)
        overlay_scale = ttk.Scale(
            overlay_frame,
            from_=-20.0,
            to=6.0,
            orient=tk.HORIZONTAL,
            variable=self.volume_vars['overlay_db'],
            length=300
        )
        overlay_scale.grid(row=0, column=1, sticky=tk.W, padx=5)

        overlay_value_label = ttk.Label(overlay_frame, textvariable=self.volume_vars['overlay_db'], width=5)
        overlay_value_label.grid(row=0, column=2, sticky=tk.W, padx=5)

        ttk.Label(overlay_frame, text="(actualCurrentArtist.mp3)", font=("Segoe UI", 9)).grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5)

        # Info text
        info_text = (
            "Volume adjustments in decibels (dB):\n"
            "• 0 dB = No change (original volume)\n"
            "• +6 dB = Approximately double volume\n"
            "• -20 dB = Approximately 1/10th volume\n\n"
            "Changes take effect when the intro loader processes the next XML update."
        )
        info_label = ttk.Label(parent_frame, text=info_text, justify=tk.LEFT, wraplength=380)
        info_label.pack(pady=(20, 0), anchor=tk.W)

    def create_debug_tab(self, parent_frame):
        """Create the debug tab with testing and logging controls."""
        debug_label = ttk.Label(parent_frame, text="Debug Tools", font=("Segoe UI", 10, "bold"))
        debug_label.pack(pady=(0,10))

        # --- Intro Loader Section ---
        intro_frame = ttk.LabelFrame(parent_frame, text="Intro Loader", padding="5")
        intro_frame.pack(fill=tk.X, pady=(0, 10))

        # Add button to "touch" the XML file
        touch_button = ttk.Button(intro_frame, text="Touch XML File", command=self.touch_xml_file_action)
        touch_button.pack(pady=2)
        touch_help = ttk.Label(
            intro_frame,
            text="Updates the XML file's modification time to force the Intro Loader to re-check it.",
            wraplength=380,
        )
        touch_help.pack(pady=(0, 5))

        # --- Ad Inserter Section ---
        ad_inserter_frame = ttk.LabelFrame(parent_frame, text="Ad Inserter", padding="5")
        ad_inserter_frame.pack(fill=tk.X, pady=(0, 10))

        # Button to combine ads and trigger the ad inserter URL
        ad_button = ttk.Button(ad_inserter_frame, text="Run Ad Service", command=self.run_ad_service_action)
        ad_button.pack(pady=2)
        ad_help = ttk.Label(
            ad_inserter_frame,
            text="Combine enabled ads into one MP3 and call the ad inserter URL.",
            wraplength=380,
        )
        ad_help.pack(pady=(0, 5))

        # Button to instantly play ads via the instant URL
        instant_button = ttk.Button(ad_inserter_frame, text="Play Ad Now", command=self.run_instant_ad_service_action)
        instant_button.pack(pady=2)
        instant_help = ttk.Label(
            ad_inserter_frame,
            text="Combine enabled ads and trigger immediate playback.",
            wraplength=380,
        )
        instant_help.pack(pady=(0, 5))

        # --- Ad Scheduler Section ---
        ad_scheduler_frame = ttk.LabelFrame(parent_frame, text="Ad Scheduler", padding="5")
        ad_scheduler_frame.pack(fill=tk.X, pady=(0, 10))

        # Station selector for hour simulation
        station_frame = ttk.Frame(ad_scheduler_frame)
        station_frame.pack(fill=tk.X, pady=2)
        ttk.Label(station_frame, text="Station:").pack(side=tk.LEFT)
        self.simulate_station_var = tk.StringVar(value="887")
        station_combo = ttk.Combobox(station_frame, textvariable=self.simulate_station_var,
                                     values=["1047", "887"], state="readonly", width=5)
        station_combo.pack(side=tk.LEFT, padx=5)

        # Minute selector
        minute_frame = ttk.Frame(ad_scheduler_frame)
        minute_frame.pack(fill=tk.X, pady=2)
        ttk.Label(minute_frame, text="Minute:").pack(side=tk.LEFT)
        self.sim_minute_var = tk.IntVar(value=0)
        minute_spinbox = ttk.Spinbox(minute_frame, from_=0, to=59, textvariable=self.sim_minute_var, width=3)
        minute_spinbox.pack(side=tk.LEFT, padx=5)

        # Schedule/Cancel buttons
        button_frame = ttk.Frame(ad_scheduler_frame)
        button_frame.pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Schedule Hour Start", command=self.schedule_hour_start_at_minute).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel Scheduled", command=self.cancel_scheduled_hour_start).pack(side=tk.LEFT)

        # Status display
        status_frame = ttk.Frame(ad_scheduler_frame)
        status_frame.pack(fill=tk.X, pady=2)
        ttk.Label(status_frame, text="Scheduled:").pack(side=tk.LEFT)
        status_label = ttk.Label(status_frame, textvariable=self._hour_sim_status[self.simulate_station_var.get()])
        status_label.pack(side=tk.LEFT, padx=5)

        # Update status label when station changes
        def update_status_on_station_change(*args):
            station = self.simulate_station_var.get()
            status_label.config(textvariable=self._hour_sim_status[station])

        self.simulate_station_var.trace('w', update_status_on_station_change)

        # Button to simulate start of hour for AdScheduler testing
        hour_button = ttk.Button(ad_scheduler_frame, text="Simulate Hour Start", command=self.simulate_hour_start)
        hour_button.pack(pady=2)
        hour_help = ttk.Label(
            ad_scheduler_frame,
            text="Triggers the AdScheduler's hourly check logic to test ad insertion timing.",
            wraplength=380,
        )
        hour_help.pack(pady=(0, 5))

        # --- Logging Section ---
        logging_frame = ttk.LabelFrame(parent_frame, text="Logging", padding="5")
        logging_frame.pack(fill=tk.X, pady=(0, 10))

        self.enable_debug_logs_var = tk.BooleanVar(
            value=self.config_manager.get_setting("settings.debug.enable_debug_logs", False)
        )

        debug_checkbox = ttk.Checkbutton(
            logging_frame,
            text="Enable Debug Logs (Shows detailed DEBUG messages)",
            variable=self.enable_debug_logs_var,
            command=self.toggle_debug_logging
        )
        debug_checkbox.pack(pady=2)

        debug_note = ttk.Label(
            logging_frame,
            text="Note: Debug logs provide detailed information useful for troubleshooting.\nDisabling this will only show INFO, WARNING, and ERROR messages.",
            wraplength=380,
        )
        debug_note.pack(pady=(0, 5))

    def create_migration_tab(self, parent_frame):
        """Create the migration tab with stable folder path and migration buttons."""
        title_label = ttk.Label(parent_frame, text="Migration Assistant", font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=(0, 15))

        # Stable folder path section
        path_frame = ttk.Frame(parent_frame)
        path_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(path_frame, text="Stable Folder Path:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        path_entry = ttk.Entry(path_frame, textvariable=self.migration_vars['stable_path'], width=50)
        path_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Button(path_frame, text="Browse", command=self.browse_stable_folder).grid(row=0, column=2, padx=5, pady=2)

        path_help = ttk.Label(
            path_frame,
            text="Path to the stable version folder. Default is a sibling folder with ' - stable' suffix.\n"
                 "This path is saved and remembered for future migrations.",
            wraplength=400,
            justify=tk.LEFT
        )
        path_help.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(5, 0))

        # Migration buttons section
        buttons_frame = ttk.Frame(parent_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            buttons_frame,
            text="Copy Config: Stable → Active",
            command=self.copy_config_from_stable,
            width=25
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_frame,
            text="Copy Config: Active → Stable",
            command=self.copy_config_to_stable,
            width=25
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_frame,
            text="Deploy Active → Stable\n(wipe Stable first)",
            command=self.deploy_active_to_stable,
            width=25
        ).pack(side=tk.LEFT, padx=5)

        # Status label
        self.migration_status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(parent_frame, textvariable=self.migration_status_var, foreground="blue")
        status_label.pack(pady=(20, 0), anchor=tk.W)

        # Help text
        help_text = (
            "Migration Operations:\n\n"
            "• Copy Config Stable → Active: Copies config.json from Stable to Active folder, backing up Active's config first.\n\n"
            "• Copy Config Active → Stable: Copies config.json from Active to Stable folder, backing up Stable's config first.\n\n"
            "• Deploy Active → Stable: Completely replaces Stable folder contents with Active folder contents.\n"
            "  This is destructive and excludes development artifacts (.git, __pycache__, etc.). Requires confirmation."
        )
        help_label = ttk.Label(parent_frame, text=help_text, justify=tk.LEFT, wraplength=500)
        help_label.pack(pady=(10, 0), anchor=tk.W)

    def browse_stable_folder(self):
        """Browse for stable folder path."""
        path = filedialog.askdirectory(title="Select Stable Folder", initialdir=self.migration_vars['stable_path'].get())
        if path:
            self.migration_vars['stable_path'].set(path)

    def copy_config_from_stable(self):
        """Copy config.json from Stable to Active folder."""
        from migration_utils import MigrationUtils

        stable_path = self.migration_vars['stable_path'].get().strip()
        active_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Validate paths
        validation_error = MigrationUtils.validate_paths(active_root, stable_path)
        if validation_error:
            messagebox.showerror("Path Error", validation_error, parent=self)
            return

        # Check if stable config exists
        stable_config = os.path.join(stable_path, 'config.json')
        if not os.path.exists(stable_config):
            messagebox.showerror("Config Error", f"Stable config.json not found at: {stable_config}", parent=self)
            return

        # Perform the copy
        self.migration_status_var.set("Copying config Stable → Active...")
        self.update()  # Force UI update

        success = MigrationUtils.copy_config_file(stable_path, active_root, backup=True)

        if success:
            self.migration_status_var.set("Config copied successfully from Stable to Active")
            messagebox.showinfo("Success", "Config copied from Stable to Active folder.\n\nActive config was backed up.", parent=self)
            logging.info("Migration: Copied config from Stable to Active")
        else:
            self.migration_status_var.set("Failed to copy config")
            messagebox.showerror("Copy Failed", "Failed to copy config from Stable to Active.\nCheck logs for details.", parent=self)

    def copy_config_to_stable(self):
        """Copy config.json from Active to Stable folder."""
        from migration_utils import MigrationUtils

        stable_path = self.migration_vars['stable_path'].get().strip()
        active_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Validate paths
        validation_error = MigrationUtils.validate_paths(active_root, stable_path)
        if validation_error:
            messagebox.showerror("Path Error", validation_error, parent=self)
            return

        # Ensure stable directory exists
        if not os.path.exists(stable_path):
            try:
                os.makedirs(stable_path, exist_ok=True)
                logging.info(f"Created stable directory: {stable_path}")
            except Exception as e:
                messagebox.showerror("Directory Error", f"Failed to create stable directory: {e}", parent=self)
                return

        # Perform the copy
        self.migration_status_var.set("Copying config Active → Stable...")
        self.update()  # Force UI update

        success = MigrationUtils.copy_config_file(active_root, stable_path, backup=True)

        if success:
            self.migration_status_var.set("Config copied successfully from Active to Stable")
            messagebox.showinfo("Success", "Config copied from Active to Stable folder.\n\nStable config was backed up.", parent=self)
            logging.info("Migration: Copied config from Active to Stable")
        else:
            self.migration_status_var.set("Failed to copy config")
            messagebox.showerror("Copy Failed", "Failed to copy config from Active to Stable.\nCheck logs for details.", parent=self)

    def deploy_active_to_stable(self):
        """Deploy entire Active folder to Stable (destructive)."""
        from migration_utils import MigrationUtils

        stable_path = self.migration_vars['stable_path'].get().strip()
        active_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Validate paths
        validation_error = MigrationUtils.validate_paths(active_root, stable_path)
        if validation_error:
            messagebox.showerror("Path Error", validation_error, parent=self)
            return

        # Confirm destructive operation
        confirm_msg = (
            "WARNING: This will completely replace the contents of the Stable folder with the Active folder.\n\n"
            f"Stable folder: {stable_path}\n\n"
            "This operation cannot be undone. Are you sure you want to proceed?"
        )
        if not messagebox.askyesno("Confirm Deployment", confirm_msg, parent=self, icon='warning'):
            return

        # Disable buttons during operation
        self._set_migration_buttons_state(False)
        self.migration_status_var.set("Deploying Active → Stable...")

        def progress_callback(status):
            self.migration_status_var.set(status)
            self.update()

        def deploy_thread():
            try:
                success = MigrationUtils.deploy_active_to_stable(active_root, stable_path, progress_callback)
                if success:
                    self.migration_status_var.set("Deployment completed successfully")
                    messagebox.showinfo("Success", "Active folder deployed to Stable successfully!", parent=self)
                    logging.info("Migration: Deployed Active to Stable")
                else:
                    self.migration_status_var.set("Deployment failed")
                    messagebox.showerror("Deployment Failed", "Failed to deploy Active to Stable.\nCheck logs for details.", parent=self)
            except Exception as e:
                logging.exception("Deployment exception")
                self.migration_status_var.set("Deployment failed with exception")
                messagebox.showerror("Deployment Error", f"Deployment failed: {e}", parent=self)
            finally:
                self._set_migration_buttons_state(True)

        # Run in background thread to avoid UI freeze
        MigrationUtils.run_in_thread(deploy_thread)

    def _set_migration_buttons_state(self, enabled: bool):
        """Enable/disable migration buttons during operations."""
        # This would require storing references to the buttons, but for simplicity
        # we'll just update the status. In a full implementation, we'd store button refs.
        pass

    def create_station_settings_tab(self, parent_frame, station_id):
        """Create a settings tab for a specific station."""
        # Store variables for this station
        station_vars = self.station_vars[station_id]
        
        # RDS Settings Section
        rds_label = ttk.Label(parent_frame, text="RDS Settings", font=("Segoe UI", 10, "bold"))
        rds_label.pack(anchor=tk.W, pady=(0,5))

        rds_frame = ttk.Frame(parent_frame)
        rds_frame.pack(fill=tk.X, pady=5)

        # RDS IP
        ttk.Label(rds_frame, text="RDS IP:").grid(row=0, column=0, sticky=tk.W, padx=5)
        station_vars['rds_ip'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.rds.ip"))
        ttk.Entry(rds_frame, textvariable=station_vars['rds_ip'], width=40).grid(row=0, column=1, sticky=tk.W, padx=5)

        # RDS Port
        ttk.Label(rds_frame, text="RDS Port:").grid(row=1, column=0, sticky=tk.W, padx=5)
        station_vars['rds_port'] = tk.IntVar(value=self.config_manager.get_station_setting(station_id, "settings.rds.port"))
        ttk.Entry(rds_frame, textvariable=station_vars['rds_port'], width=40).grid(row=1, column=1, sticky=tk.W, padx=5)

        # Now Playing XML
        ttk.Label(rds_frame, text="Now Playing XML:").grid(row=2, column=0, sticky=tk.W, padx=5)
        station_vars['rds_xml'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.rds.now_playing_xml"))
        ttk.Entry(rds_frame, textvariable=station_vars['rds_xml'], width=40).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Button(rds_frame, text="Browse", command=lambda: self.browse_file(station_vars['rds_xml'])).grid(row=2, column=2, padx=5)

        # Default Message
        ttk.Label(rds_frame, text="Default Message:").grid(row=3, column=0, sticky=tk.W, padx=5)
        station_vars['rds_default'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.rds.default_message", ""))
        ttk.Entry(rds_frame, textvariable=station_vars['rds_default'], width=40).grid(row=3, column=1, sticky=tk.W, padx=5)

        # Intro Loader Settings Section
        loader_label = ttk.Label(parent_frame, text="Intro Loader Settings", font=("Segoe UI", 10, "bold"))
        loader_label.pack(anchor=tk.W, pady=(10,5))

        loader_frame = ttk.Frame(parent_frame)
        loader_frame.pack(fill=tk.X, pady=5)

        # Now Playing XML (shared with RDS, but allow separate if needed)
        ttk.Label(loader_frame, text="Now Playing XML:").grid(row=0, column=0, sticky=tk.W, padx=5)
        station_vars['loader_xml'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.intro_loader.now_playing_xml"))
        ttk.Entry(loader_frame, textvariable=station_vars['loader_xml'], width=40).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(loader_frame, text="Browse", command=lambda: self.browse_file(station_vars['loader_xml'])).grid(row=0, column=2, padx=5)

        # MP3 Directory
        ttk.Label(loader_frame, text="MP3 Directory:").grid(row=1, column=0, sticky=tk.W, padx=5)
        station_vars['loader_mp3_dir'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.intro_loader.mp3_directory"))
        ttk.Entry(loader_frame, textvariable=station_vars['loader_mp3_dir'], width=40).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Button(loader_frame, text="Browse", command=lambda: self.browse_directory(station_vars['loader_mp3_dir'])).grid(row=1, column=2, padx=5)

        # Missing Artists Log
        ttk.Label(loader_frame, text="Missing Artists Log:").grid(row=2, column=0, sticky=tk.W, padx=5)
        station_vars['loader_log'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.intro_loader.missing_artists_log"))
        ttk.Entry(loader_frame, textvariable=station_vars['loader_log'], width=40).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Button(loader_frame, text="Browse", command=lambda: self.browse_file(station_vars['loader_log'], save=True)).grid(row=2, column=2, padx=5)

        # Schedule URL
        ttk.Label(loader_frame, text="Schedule URL:").grid(row=3, column=0, sticky=tk.W, padx=5)
        station_vars['loader_url'] = tk.StringVar(
            value=self.config_manager.get_station_setting(
                station_id,
                "settings.intro_loader.schedule_url",
                "http://192.168.3.11:9000/?pass=bmas220&action=schedule&type=run&id=TBACFNBGJKOMETDYSQYR",
            )
        )
        ttk.Entry(loader_frame, textvariable=station_vars['loader_url'], width=40).grid(row=3, column=1, sticky=tk.W, padx=5)

        # Current Artist Filename
        ttk.Label(loader_frame, text="Current Artist Filename:").grid(row=4, column=0, sticky=tk.W, padx=5)
        station_suffix = "_1047" if station_id == "station_1047" else "_887"
        station_vars['current_artist_filename'] = tk.StringVar(
            value=self.config_manager.get_station_setting(
                station_id,
                "settings.intro_loader.current_artist_filename",
                f"currentArtist{station_suffix}.mp3"
            )
        )
        ttk.Entry(loader_frame, textvariable=station_vars['current_artist_filename'], width=40).grid(row=4, column=1, sticky=tk.W, padx=5)

        # Actual Current Artist Filename
        ttk.Label(loader_frame, text="Actual Current Artist Filename:").grid(row=5, column=0, sticky=tk.W, padx=5)
        station_vars['actual_current_artist_filename'] = tk.StringVar(
            value=self.config_manager.get_station_setting(
                station_id,
                "settings.intro_loader.actual_current_artist_filename",
                f"actualCurrentArtist{station_suffix}.mp3"
            )
        )
        ttk.Entry(loader_frame, textvariable=station_vars['actual_current_artist_filename'], width=40).grid(row=5, column=1, sticky=tk.W, padx=5)

        # Blank MP3 Filename
        ttk.Label(loader_frame, text="Blank MP3 Filename:").grid(row=6, column=0, sticky=tk.W, padx=5)
        station_vars['blank_mp3_filename'] = tk.StringVar(
            value=self.config_manager.get_station_setting(
                station_id,
                "settings.intro_loader.blank_mp3_filename",
                f"blank{station_suffix}.mp3"
            )
        )
        ttk.Entry(loader_frame, textvariable=station_vars['blank_mp3_filename'], width=40).grid(row=6, column=1, sticky=tk.W, padx=5)

        # Silent MP3 Filename
        ttk.Label(loader_frame, text="Silent MP3 Filename:").grid(row=7, column=0, sticky=tk.W, padx=5)
        station_vars['silent_mp3_filename'] = tk.StringVar(
            value=self.config_manager.get_station_setting(
                station_id,
                "settings.intro_loader.silent_mp3_filename",
                f"near_silent{station_suffix}.mp3"
            )
        )
        ttk.Entry(loader_frame, textvariable=station_vars['silent_mp3_filename'], width=40).grid(row=7, column=1, sticky=tk.W, padx=5)

        # --- Ad Settings ---
        ad_label = ttk.Label(parent_frame, text="Ad Inserter Settings", font=("Segoe UI", 10, "bold"))
        ad_label.pack(anchor=tk.W, pady=(10,5))

        ad_frame = ttk.Frame(parent_frame)
        ad_frame.pack(fill=tk.X, pady=5)

        ttk.Label(ad_frame, text="Schedule URL:").grid(row=0, column=0, sticky=tk.W, padx=5)
        station_vars['ad_url'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.ad_inserter.insertion_url", "http://localhost:8000/insert"))
        ttk.Entry(ad_frame, textvariable=station_vars['ad_url'], width=40).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(ad_frame, text="Instant URL:").grid(row=1, column=0, sticky=tk.W, padx=5)
        station_vars['ad_instant_url'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.ad_inserter.instant_url", "http://localhost:8000/play"))
        ttk.Entry(ad_frame, textvariable=station_vars['ad_instant_url'], width=40).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(ad_frame, text="New Ad MP3:").grid(row=2, column=0, sticky=tk.W, padx=5)
        station_vars['ad_mp3'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "settings.ad_inserter.output_mp3", r"G:\\Ads\\newAd.mp3"))
        ttk.Entry(ad_frame, textvariable=station_vars['ad_mp3'], width=40).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Button(ad_frame, text="Browse", command=lambda: self.browse_file(station_vars['ad_mp3'])).grid(row=2, column=2, padx=5)

        # mAirList server settings (just server info, no UI)
        station_vars['mairlist_server'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "mairlist.server", "localhost:9000"))
        station_vars['mairlist_password'] = tk.StringVar(value=self.config_manager.get_station_setting(station_id, "mairlist.password", "bmas220"))

# Example usage for testing
if __name__ == "__main__":
    print("This script defines the OptionsWindow UI component.")
    # root = tk.Tk()
    # class MockConfig: # Define mocks if needed for standalone testing
    #     def get_whitelist(self): return ["Artist A"]
    #     def get_blacklist(self): return ["Artist B"]
    #     def set_whitelist(self, l): pass
    #     def set_blacklist(self, l): pass
    #     def save_config(self): print("Mock Save")
    # class MockLoader:
    #     def trigger_xml_change(self): print("Mock Trigger XML"); return True
    # mock_cfg = MockConfig()
    # mock_ldr = MockLoader()
    # OptionsWindow(root, mock_cfg, mock_ldr)
    # root.mainloop()