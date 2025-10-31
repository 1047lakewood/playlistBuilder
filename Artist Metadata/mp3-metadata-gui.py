import tkinter as tk
from tkinter import filedialog, scrolledtext
import os
import subprocess
import sys
from tkinter import ttk
import threading
import queue

class FolderEntry:
    def __init__(self, parent, frame, folder_path="", on_delete=None):
        self.parent = parent
        self.frame = frame
        self.folder_path = folder_path
        self.on_delete = on_delete
        
        # Main container for this entry
        self.container = tk.Frame(self.frame, bd=1, relief=tk.RAISED, padx=5, pady=5)
        self.container.pack(fill=tk.X, padx=5, pady=5)
        
        # Top row: folder path and browse button
        self.top_row = tk.Frame(self.container)
        self.top_row.pack(fill=tk.X, padx=2, pady=2)
        
        self.folder_label = tk.Label(self.top_row, text="Folder:", width=6, anchor=tk.W)
        self.folder_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.folder_entry = tk.Entry(self.top_row)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.folder_entry.insert(0, folder_path)
        
        self.browse_button = tk.Button(self.top_row, text="Browse", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_button = tk.Button(self.top_row, text="Remove", command=self.delete_self)
        self.delete_button.pack(side=tk.LEFT)
        
        # Middle row: artist name entry
        self.middle_row = tk.Frame(self.container)
        self.middle_row.pack(fill=tk.X, padx=2, pady=2)
        
        self.artist_label = tk.Label(self.middle_row, text="Artist:", width=6, anchor=tk.W)
        self.artist_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.artist_entry = tk.Entry(self.middle_row)
        self.artist_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Extract folder name for default artist name
        if folder_path:
            folder_name = os.path.basename(folder_path)
            self.artist_entry.insert(0, folder_name)
        
        # Bottom row: action buttons
        self.bottom_row = tk.Frame(self.container)
        self.bottom_row.pack(fill=tk.X, padx=2, pady=2)
        
        self.read_button = tk.Button(self.bottom_row, text="Read Metadata", command=self.read_metadata)
        self.read_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.write_button = tk.Button(self.bottom_row, text="Write Metadata", command=self.write_metadata)
        self.write_button.pack(side=tk.LEFT)
    
    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path = folder_path
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)
            
            # Update artist name field with folder name
            folder_name = os.path.basename(folder_path)
            self.artist_entry.delete(0, tk.END)
            self.artist_entry.insert(0, folder_name)
    
    def delete_self(self):
        self.container.destroy()
        if self.on_delete:
            self.on_delete(self)
    
    def read_metadata(self):
        folder_path = self.folder_entry.get()
        if not folder_path:
            self.parent.add_log("Error: No folder selected")
            return
        
        # Disable buttons while command is running
        self.read_button.config(state=tk.DISABLED)
        self.write_button.config(state=tk.DISABLED)
        
        command = [
            "python", 
            r"G:\Misc\Dev\Artist Metadata\mp3_metadata_batch_processor.py", 
            folder_path, 
            "--read-only"
        ]
        
        thread = threading.Thread(target=self.run_command_and_reenable, args=(command,))
        thread.daemon = True
        thread.start()
    
    def write_metadata(self):
        folder_path = self.folder_entry.get()
        artist_name = self.artist_entry.get()
        
        if not folder_path:
            self.parent.add_log("Error: No folder selected")
            return
        
        if not artist_name:
            self.parent.add_log("Error: Artist name is empty")
            return
        
        # Disable buttons while command is running
        self.read_button.config(state=tk.DISABLED)
        self.write_button.config(state=tk.DISABLED)
        
        command = [
            "python", 
            r"G:\Misc\Dev\Artist Metadata\mp3_metadata_batch_processor.py", 
            folder_path, 
            "-a", 
            artist_name
        ]
        
        thread = threading.Thread(target=self.run_command_and_reenable, args=(command,))
        thread.daemon = True
        thread.start()
        
    def run_command_and_reenable(self, command):
        """Run the command and re-enable buttons when done"""
        try:
            self.run_command(command)
        finally:
            # Re-enable buttons in the main thread
            self.parent.after(0, self.enable_buttons)
            
    def enable_buttons(self):
        """Re-enable the buttons"""
        self.read_button.config(state=tk.NORMAL)
        self.write_button.config(state=tk.NORMAL)
    
    def run_command(self, command):
        self.parent.add_log(f"Running: {' '.join(command)}")
        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            stdout, stderr = process.communicate()
            
            if stdout:
                self.parent.add_log(f"Output: {stdout}")
            if stderr:
                self.parent.add_log(f"Error: {stderr}")
                
            self.parent.add_log(f"Command completed with exit code: {process.returncode}")
        except Exception as e:
            self.parent.add_log(f"Exception occurred: {str(e)}")


class FolderProcessor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MP3 Metadata Batch Processor")
        self.geometry("800x600")
        self.minsize(600, 400)
        
        self.folder_entries = []
        self.log_queue = queue.Queue()
        
        # Drag and drop setup
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)
        
        # Create main frames
        self.create_frames()
        
        # Start log updater
        self.after(100, self.update_log_from_queue)
    
    def create_frames(self):
        # Top frame for controls
        self.top_frame = tk.Frame(self)
        self.top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.add_folder_button = tk.Button(self.top_frame, text="Add Folder", command=self.add_folder)
        self.add_folder_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_all_button = tk.Button(self.top_frame, text="Clear All", command=self.clear_all)
        self.clear_all_button.pack(side=tk.LEFT, padx=5)
        
        # Middle frame with scrollbar for folder entries
        self.middle_frame_container = tk.Frame(self)
        self.middle_frame_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.middle_frame_canvas = tk.Canvas(self.middle_frame_container)
        self.scrollbar = tk.Scrollbar(self.middle_frame_container, orient=tk.VERTICAL, command=self.middle_frame_canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.middle_frame_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.middle_frame_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.middle_frame = tk.Frame(self.middle_frame_canvas)
        self.middle_frame_canvas.create_window((0, 0), window=self.middle_frame, anchor=tk.NW)
        
        self.middle_frame.bind("<Configure>", lambda e: self.middle_frame_canvas.configure(
            scrollregion=self.middle_frame_canvas.bbox("all")
        ))
        
        # Bottom frame for logs
        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_label = tk.Label(self.bottom_frame, text="Logs:")
        self.log_label.pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(self.bottom_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
    
    def add_folder(self, folder_path=""):
        folder_entry = FolderEntry(self, self.middle_frame, folder_path, on_delete=self.remove_folder_entry)
        self.folder_entries.append(folder_entry)
        
        # Update scrollregion
        self.middle_frame.update_idletasks()
        self.middle_frame_canvas.configure(scrollregion=self.middle_frame_canvas.bbox("all"))
    
    def remove_folder_entry(self, entry):
        if entry in self.folder_entries:
            self.folder_entries.remove(entry)
    
    def clear_all(self):
        for entry in self.folder_entries[:]:  # Make a copy of the list to iterate
            entry.delete_self()
        self.folder_entries = []
    
    def handle_drop(self, event):
        file_paths = self.tk.splitlist(event.data)
        
        for path in file_paths:
            # Convert TkDND path format to normal path
            path = path.strip('{}')
            
            # Check if it's a directory
            if os.path.isdir(path):
                self.add_folder(path)
    
    def add_log(self, message):
        # Add message to queue for thread safety
        self.log_queue.put(message)
    
    def update_log_from_queue(self):
        # Process all messages in the queue
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        # Schedule next update
        self.after(100, self.update_log_from_queue)


# Add this before running - required for drag and drop functionality
try:
    # Try to import TkinterDnD2
    from tkinterdnd2 import DND_FILES, TkinterDnD
    
    class FolderProcessor(FolderProcessor, TkinterDnD.Tk):
        pass
except ImportError:
    # Fallback if TkinterDnD2 is not available
    DND_FILES = '<<Drop>>'  # Dummy value
    
    # Show a warning
    import tkinter.messagebox as messagebox
    messagebox.showwarning(
        "Missing Package", 
        "TkinterDnD2 is not installed. Drag and drop functionality will be disabled.\n"
        "Install it with: pip install tkinterdnd2"
    )


if __name__ == "__main__":
    app = FolderProcessor()
    app.mainloop()