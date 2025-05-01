import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import os
import sys
import json
import shutil
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
from mutagen.flac import FLACNoHeaderError
from mutagen.mp4 import MP4NoTrackError
from mutagen.oggvorbis import OggVorbisHeaderError
import pygame
import threading
import time
import tkinter.font as tkfont
from metadata_utils import load_audio_metadata, save_audio_metadata
import subprocess
import ctypes
from ctypes import wintypes
from ctypes import windll

# --- Constants ---
APP_NAME = "Multi-Playlist Editor"
SETTINGS_FILE = "playlist_editor_settings.json"
DEFAULT_COLUMNS = ['#', 'Artist', 'Title', 'Duration', 'Path', 'Exists']
AVAILABLE_COLUMNS = ['#', 'Artist', 'Title', 'Album', 'Genre', 'TrackNumber', 'Duration', 'Path', 'Exists', 'Bitrate', 'Format']
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

def open_file_location(filepath):
    """Opens the folder containing the file in the default file explorer, selecting the file if it exists."""
    if not os.path.exists(filepath):
        messagebox.showwarning("File Not Found", f"The file '{filepath}' does not exist.")
        return

    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    try:
        if sys.platform == 'win32':
            # Windows API method for selecting file
            def _win_select_file(file_path):
                # Convert file path to wide string
                file_path = os.path.normpath(file_path)
                
                # Load necessary Windows API functions
                shell32 = windll.shell32
                ole32 = windll.ole32

                # Initialize COM library
                ole32.CoInitialize(None)

                try:
                    # Parse the display name
                    pidl = wintypes.PIDL()
                    sfgao = wintypes.ULONG()
                    hr = shell32.SHParseDisplayName(
                        file_path, 
                        None, 
                        ctypes.byref(pidl), 
                        0, 
                        ctypes.byref(sfgao)
                    )

                    if hr == 0:  # S_OK
                        # Get the parent folder
                        pshf = ctypes.POINTER(ctypes.c_void_p)()
                        hr = shell32.SHBindToParent(
                            pidl, 
                            None, 
                            ctypes.byref(pshf), 
                            None
                        )

                        if hr == 0:  # S_OK
                            # Open and select the file
                            shell32.SHOpenFolderAndSelectItems(
                                pidl, 
                                0, 
                                None, 
                                0
                            )
                            return True
                
                except Exception as e:
                    print(f"Windows API file selection failed: {e}")
                
                return False

            # Try Windows API method first
            if _win_select_file(filepath):
                return

            # Fallback to explorer.exe method if Windows API fails
            try:
                subprocess.run(['explorer.exe', '/select,', filepath], check=True)
                return
            except Exception as e:
                print(f"Explorer file selection failed: {e}")
                # If all else fails, open the directory
                os.startfile(directory)

        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', '-R', filepath], check=True)

        else:  # Linux and other POSIX
            # Use xdg-open with file selection for file managers that support it
            try:
                subprocess.run(['nautilus', '--select', filepath], check=False)
            except Exception:
                # Fallback to opening directory
                subprocess.run(['xdg-open', directory], check=True)

    except Exception as e:
        messagebox.showerror("Error Opening Location", f"Could not open file location:\n{e}")

# --- Dialog Classes ---
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
