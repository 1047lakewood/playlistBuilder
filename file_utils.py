import os
import utils
import subprocess
import sys
from tkinter import messagebox
class FileUtils:

    @staticmethod
    def open_file_location(path):
        """Open the file location of the selected track in File Explorer"""
        if not path:
            return
            
        file_path = path
        
        # Open the file location
        utils.open_file_location(file_path)

    @staticmethod
    def open_in_audacity(path):
        if not path:
            messagebox.showerror("Error", "Track path not found")
            return
        file_path = path
        if sys.platform == "win32":
            subprocess.Popen([r"C:\Program Files\Audacity\audacity.exe", file_path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "Audacity", file_path])
        elif sys.platform == "linux":
            subprocess.Popen(["audacity", file_path])
        else:
            messagebox.showerror("Error", "Unsupported platform")
        