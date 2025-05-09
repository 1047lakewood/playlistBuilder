from tkinter import messagebox
import os
import sys

import subprocess
import logging

# --- Constants ---
APP_NAME = "Multi-Playlist Editor"
SETTINGS_FILE = "playlist_editor_settings.json"
DEFAULT_COLUMNS = ['#', 'Intro', 'Artist', 'Title', 'Duration', 'Path', 'Exists']
AVAILABLE_COLUMNS = ['#', 'Intro', 'Artist', 'Title', 'Album', 'Genre', 'TrackNumber', 'Duration', 'Path', 'Exists', 'Bitrate', 'Format']
M3U_ENCODING = 'utf-8'  # Use M3U8 standard

# --- Helper Functions ---
def format_duration(seconds):
    """Formats seconds into MM:SS or HH:MM:SS"""
    if seconds is None:
        return "--:--"
    try:
        secs = int(seconds)
        mins, secs = divmod(secs, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        else:
            return f"{mins:02d}:{secs:02d}"
    except (TypeError, ValueError):
        return "--:--"

def format_start_time(dt):
    """Format datetime as 'Sun 02:42:57 PM'"""
    return dt.strftime('%a %I:%M:%S %p')

def open_file_location(filepath):
    """Opens the folder containing the file in the default file explorer, selecting the file if it exists."""
    logger = logging.getLogger(__name__)
    if not os.path.exists(filepath):
        messagebox.showwarning("File Not Found", f"The file '{filepath}' does not exist.")
        return

    directory = os.path.dirname(filepath)
    try:
        if sys.platform == 'win32':
            # Use explorer.exe with /select, and proper quoting
            try:
                quoted_path = os.path.normpath(filepath)
                cmd = ["explorer.exe", f'/select,"{quoted_path}"']
                completed = subprocess.run(" ".join(cmd), shell=True, check=True)
                return
            except Exception as e:
                logger.error(f"Explorer file selection failed: {e}")
                # As a last resort, open the directory
                try:
                    os.startfile(directory)
                except Exception as e2:
                    logger.error(f"Failed to open directory as fallback: {e2}")
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', '-R', filepath], check=True)
        else:  # Linux and other POSIX
            try:
                subprocess.run(['nautilus', '--select', filepath], check=False)
            except Exception:
                subprocess.run(['xdg-open', directory], check=True)
    except Exception as e:
        logger.error(f"Could not open file location: {e}")
        messagebox.showerror("Error Opening Location", f"Could not open file location:\n{e}")
