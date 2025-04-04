import tkinter as tk
from tkinter import ttk
import logging
import sys
import threading
import queue
import os
from tkinter import messagebox # Import messagebox explicitly
from ttkthemes import ThemedTk # Restore ThemedTk
# from tkinterdnd2 import TkinterDnD # Remove DnD import - hack didn't work
# from PIL import Image # For loading the icon - Removed
# import pystray # For system tray functionality - Removed

# --- Core Components ---
from config_manager import ConfigManager
from auto_rds_handler import AutoRDSHandler
from intro_loader_handler import IntroLoaderHandler
# Import window classes from their specific files
from ui_config_window import ConfigWindow
from ui_missing_artists_window import MissingArtistsWindow
from ui_options_window import OptionsWindow
# Import the new playlist editor window
from ui_playlist_editor_window import PlaylistEditorWindow
# from utils import format_timestamp # Not currently used

# --- Constants ---
APP_NAME = "Combined RDS & Intro Loader"
LOG_TIMESTAMP_FORMAT = '%b %d %Y %I:%M:%S %p' # e.g., Jan 05 2025 03:45:48 PM
# ICON_FILENAME = "placeholder.ico" # Removed
# ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ICON_FILENAME) # Icon in parent dir - Removed

# --- Logging Setup ---
# Create separate queues for each handler
rds_log_queue = queue.Queue()
loader_log_queue = queue.Queue()

# Define the QueueHandler class (used by both)
class QueueHandler(logging.Handler):
    """Class to send logging records to a specific queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        # Optional: Add formatter here if all queue handlers use the same format
        # self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt=LOG_TIMESTAMP_FORMAT))

    def emit(self, record):
        # Put the formatted record into the queue
        self.log_queue.put(self.format(record))

# Keep setup_logging simple for now, handlers will be added specifically
def setup_logging():
    """Basic logging setup (level). Handlers are added elsewhere."""
    # Set root logger level if needed, but specific loggers are preferred
    # logging.getLogger().setLevel(logging.INFO)
    pass # Handlers will be attached to specific loggers

    # Optional: Add console handler for debugging if needed
    # console_handler = logging.StreamHandler(sys.stderr)
    # console_handler.setFormatter(log_formatter)
    # logger.addHandler(console_handler)

# --- Main Application Class ---
class MainApplication(ThemedTk): # Restore ThemedTk base class
    def __init__(self):
        super().__init__(theme="arc") # Restore theme argument
        self.title(APP_NAME)
        # Remove DnD initialization from here
        # Don't start hidden - remove self.withdraw()
        # self.withdraw()
        # Set geometry after withdraw/deiconify might be better
        self.geometry("800x600") # Set initial size since it's visible now

        # Allow resizing
        self.resizable(True, True) # Allow resizing now that it's a main window
        self.minsize(600, 400) # Set a minimum size

        # Handle closing - Make 'X' button quit the app
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Changed from self.hide_window

        # Tray icon setup - Removed
        # self.tray_icon = None
        # self.tray_thread = None

        # Initialize core components
        logging.info("Initializing components...")
        try:
            self.config = ConfigManager()
            # Pass the specific log queue to each handler
            self.auto_rds = AutoRDSHandler(self.config, rds_log_queue)
            self.intro_loader = IntroLoaderHandler(loader_log_queue)
            self._configure_handler_logging() # Configure logging handlers *after* creating instances
            logging.info("Components initialized.")
        except Exception as e:
             logging.exception("FATAL: Failed to initialize core components.")
             messagebox.showerror("Initialization Error", f"Failed to initialize application components:\n{e}\n\nCheck logs for details. Application will exit.")
             self.destroy()
             return # Stop further initialization

        self.create_widgets()
        self.start_background_tasks()
        self.process_log_queues() # Start polling the log queues (Corrected method name)
        self.update_current_messages_display() # Start polling current messages
        # self.setup_tray_icon() # Setup and run the tray icon - Removed

        logging.info(f"{APP_NAME} started.")
        # Show window briefly on first start? Optional.
        # self.show_window()

    def create_widgets(self):
        """Creates the main GUI layout."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Frame for Buttons ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Placeholder buttons
        config_button = ttk.Button(top_frame, text="Configure Messages", command=self.open_config)
        config_button.pack(side=tk.LEFT, padx=5)

        missing_button = ttk.Button(top_frame, text="Show Missing Artists", command=self.open_missing_artists)
        missing_button.pack(side=tk.LEFT, padx=5)

        options_button = ttk.Button(top_frame, text="Options", command=self.open_options)
        options_button.pack(side=tk.LEFT, padx=5)

        playlist_editor_button = ttk.Button(top_frame, text="Mini Playlist Editor", command=self.open_playlist_editor)
        playlist_editor_button.pack(side=tk.LEFT, padx=5)

        # --- Log Display Area (using PanedWindow for resizing) ---
        log_pane = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        log_pane.pack(fill=tk.BOTH, expand=True)

        # RDS Log Area
        rds_log_frame = ttk.LabelFrame(log_pane, text="AutoRDS Logs")
        self.rds_log_text = tk.Text(rds_log_frame, wrap=tk.WORD, state=tk.DISABLED, height=10, font=("Consolas", 9))
        rds_log_scroll = ttk.Scrollbar(rds_log_frame, orient=tk.VERTICAL, command=self.rds_log_text.yview)
        self.rds_log_text.config(yscrollcommand=rds_log_scroll.set)
        rds_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.rds_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Intro Loader Log Area
        loader_log_frame = ttk.LabelFrame(log_pane, text="Intro Loader Logs")
        self.loader_log_text = tk.Text(loader_log_frame, wrap=tk.WORD, state=tk.DISABLED, height=10, font=("Consolas", 9))
        loader_log_scroll = ttk.Scrollbar(loader_log_frame, orient=tk.VERTICAL, command=self.loader_log_text.yview)
        self.loader_log_text.config(yscrollcommand=loader_log_scroll.set)
        loader_log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.loader_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_pane.add(rds_log_frame, weight=1)
        log_pane.add(loader_log_frame, weight=1)

        # --- Current Messages Display ---
        msg_frame = ttk.LabelFrame(main_frame, text="Current RDS Messages Cycle")
        # Pack below logs or adjust layout as needed
        msg_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM) # Pack at bottom before status bar

        self.msg_listbox = tk.Listbox(msg_frame, height=8, font=("Segoe UI", 9)) # Increased height from 4 to 8
        msg_scroll = ttk.Scrollbar(msg_frame, orient=tk.VERTICAL, command=self.msg_listbox.yview)
        self.msg_listbox.config(yscrollcommand=msg_scroll.set)

        msg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.msg_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)


        # --- Status Bar ---
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        self.status_var.set("Ready")

    def _configure_handler_logging(self):
        """Sets up QueueHandlers for the specific handler loggers."""
        log_formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s', datefmt=LOG_TIMESTAMP_FORMAT)

        # RDS Logger
        rds_logger = logging.getLogger('AutoRDS') # Use the name defined in the handler
        rds_logger.setLevel(logging.INFO) # Set level for this specific logger
        rds_handler = QueueHandler(rds_log_queue)
        rds_handler.setFormatter(log_formatter)
        # Prevent duplicate messages if root logger also has handlers
        rds_logger.propagate = False
        # Remove existing handlers for this logger before adding (safety)
        for handler in rds_logger.handlers[:]: rds_logger.removeHandler(handler)
        rds_logger.addHandler(rds_handler)

        # Loader Logger
        loader_logger = logging.getLogger('IntroLoader') # Use the name defined in the handler
        loader_logger.setLevel(logging.INFO) # Set level back to INFO
        loader_handler = QueueHandler(loader_log_queue)
        loader_handler.setFormatter(log_formatter)
        loader_logger.propagate = False
        for handler in loader_logger.handlers[:]: loader_logger.removeHandler(handler)
        loader_logger.addHandler(loader_handler)

        logging.info("Specific log handlers configured.")


    def _update_log_display(self, text_widget, message):
        """Appends a message to the specified log display widget."""
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, message + '\n')
        text_widget.config(state=tk.DISABLED)
        text_widget.see(tk.END) # Auto-scroll

    def process_log_queues(self):
        """Checks both log queues and updates the respective GUI widgets."""
        # Process RDS queue
        try:
            while True:
                record = rds_log_queue.get_nowait()
                self._update_log_display(self.rds_log_text, record)
        except queue.Empty:
            pass # No RDS logs to process currently

        # Process Loader queue
        try:
            while True:
                record = loader_log_queue.get_nowait()
                self._update_log_display(self.loader_log_text, record)
        except queue.Empty:
            pass # No Loader logs to process currently

        finally:
            # Schedule the next check for both queues
            self.after(100, self.process_log_queues) # Renamed method

    def start_background_tasks(self):
            # Schedule the next check
            self.after(100, self.process_log_queues) # Call the renamed method

    def start_background_tasks(self):
        """Starts the AutoRDS and Intro Loader handlers in separate threads."""
        logging.info("Starting background handlers...")
        # Start handler threads
        try:
            self.auto_rds.start()
            loader_started = self.intro_loader.start()
            if not loader_started:
                 logging.warning("Intro Loader did not start (likely missing MP3 directory). Check logs.")
                 # Optionally disable related UI elements if loader fails to start
            logging.info("Background handlers started.")
        except Exception as e:
             logging.exception("Error starting background handlers.")
             messagebox.showwarning("Handler Error", f"Could not start background handlers:\n{e}")


    def open_config(self):
        """Opens the message configuration window."""
        logging.debug("Configure Messages button clicked.")
        try:
            # Pass self (parent window) and the config manager instance
            config_win = ConfigWindow(self, self.config)
            config_win.wait_window() # Wait for the config window to close
            logging.debug("Config window closed.")
            # Optionally trigger something if config changed, though handlers should reload periodically
        except Exception as e:
            logging.exception("Error opening config window.")
            messagebox.showerror("Error", f"Could not open configuration window:\n{e}")

    def open_missing_artists(self):
        """Opens the missing artists log window."""
        logging.debug("Show Missing Artists button clicked.")
        try:
            # Pass self (parent window) and the intro loader instance
            missing_win = MissingArtistsWindow(self, self.intro_loader)
            missing_win.wait_window()
            logging.debug("Missing Artists window closed.")
        except Exception as e:
            logging.exception("Error opening missing artists window.")
            messagebox.showerror("Error", f"Could not open missing artists window:\n{e}")

    def open_options(self):
        """Opens the options menu/window."""
        logging.debug("Options button clicked.")
        try:
             # Pass self, config manager, and intro loader
             options_win = OptionsWindow(self, self.config, self.intro_loader)
             options_win.wait_window()
             logging.debug("Options window closed.")
        except Exception as e:
            logging.exception("Error opening options window.")
            messagebox.showerror("Error", f"Could not open options window:\n{e}")

    def open_playlist_editor(self):
        """Opens the mini playlist editor window."""
        logging.debug("Mini Playlist Editor button clicked.")
        # messagebox.showinfo("Coming Soon", "Playlist Editor functionality is under development.")
        try:
            # Pass self (parent window) and the config manager instance
            playlist_win = PlaylistEditorWindow(self, self.config) # Use the actual class
            playlist_win.wait_window() # Wait for the editor window to close
            logging.debug("Playlist Editor window closed.")
        except Exception as e:
            logging.exception("Error opening playlist editor window.")
            messagebox.showerror("Error", f"Could not open playlist editor window:\n{e}")


    def on_closing(self):
        """Handles application closing gracefully."""
        logging.info("Application closing...")
        try:
            # Signal handlers to stop
            if hasattr(self, 'auto_rds'):
                self.auto_rds.stop()
            if hasattr(self, 'intro_loader'):
                self.intro_loader.stop()
            # Add brief wait for threads to potentially exit? Daemon threads should exit anyway.
            # time.sleep(0.1)
        except Exception as e:
            logging.exception("Error stopping handlers during close.")
        finally:
            # Stop tray icon if it exists - Removed
            # if self.tray_icon:
            #     self.tray_icon.stop()
            # Ensure main window is destroyed regardless of errors during stop
            self.destroy()

    # --- System Tray Methods --- Removed ---
    # def setup_tray_icon(self):
    #     """Sets up and runs the system tray icon in a separate thread."""
    #     pass # Removed

    def show_window(self): # Removed icon=None, item=None
        """Shows the main application window."""
        logging.debug("Show window requested.")
        self.deiconify()
        self.lift()
        self.focus_force()
        # Geometry is set earlier now


    # Removed hide_window as it's replaced by on_closing for the 'X' button
    # def hide_window(self):
    #     """Hides the main application window (called when closing)."""
    #     logging.debug("Hiding window.")
    #     self.withdraw()

    # def quit_application(self, icon=None, item=None): # Removed
    #     """Stops handlers, stops tray icon, and destroys the window."""
    #     pass # Removed


    # --- Other Methods ---
    def update_current_messages_display(self):
        """Periodically fetches and updates the list of current RDS messages."""
        try:
            if hasattr(self, 'auto_rds') and self.auto_rds.running:
                current_messages = self.auto_rds.get_current_display_messages()

                # Clear existing listbox content
                self.msg_listbox.delete(0, tk.END)

                # Populate with new messages
                if current_messages:
                    for msg in current_messages:
                        self.msg_listbox.insert(tk.END, msg)
                else:
                    self.msg_listbox.insert(tk.END, "(No messages currently scheduled/valid)")
            else:
                 # Handler not running or not initialized
                 if not self.msg_listbox.get(0, tk.END): # Avoid clearing if already showing error
                    self.msg_listbox.delete(0, tk.END)
                    self.msg_listbox.insert(tk.END, "(AutoRDS handler not running)")

        except Exception as e:
            logging.error(f"Error updating current messages display: {e}")
            # Avoid flooding the listbox with errors, just log it
            if not self.msg_listbox.get(0, tk.END) or "Error" not in self.msg_listbox.get(0):
                 self.msg_listbox.delete(0, tk.END)
                 self.msg_listbox.insert(tk.END, "(Error updating message list)")
        finally:
            # Schedule the next update (e.g., every 5 seconds)
            self.after(5000, self.update_current_messages_display)


# --- Main Execution ---
if __name__ == "__main__":
    setup_logging()
    # Removed TkinterDnD Initialization Hack

    app = MainApplication()
    app.mainloop()
