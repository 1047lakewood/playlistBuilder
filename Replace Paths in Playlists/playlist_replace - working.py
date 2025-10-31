import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

class M3U8PathReplacerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8 Path Replacer")
        self.root.resizable(True, True)
        
        # Configure column/row weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        
        # Create main frame with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        
        # Folder selection
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        folder_frame.columnconfigure(1, weight=1)
        
        self.folder_path = tk.StringVar()
        ttk.Label(folder_frame, text="Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # Recursive option
        self.recursive = tk.BooleanVar(value=False)
        ttk.Checkbutton(folder_frame, text="Process subfolders recursively", variable=self.recursive).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=5, pady=5
        )
        
        # Path replacement settings
        replace_frame = ttk.LabelFrame(main_frame, text="Path Replacement", padding="10")
        replace_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        replace_frame.columnconfigure(1, weight=1)
        
        ttk.Label(replace_frame, text="Find:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.find_text = tk.StringVar(value="F:\\")
        ttk.Entry(replace_frame, textvariable=self.find_text).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        ttk.Label(replace_frame, text="Replace with:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.replace_text = tk.StringVar(value="G:\\Shiurim\\")
        ttk.Entry(replace_frame, textvariable=self.replace_text).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Start button next to replacement fields
        self.start_button = ttk.Button(replace_frame, text="Start Processing", command=self.start_processing)
        self.start_button.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ns")
        
        # Log area (reduced size)
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Make the log expandable but with a smaller initial size
        main_frame.rowconfigure(2, weight=1)
        
        # Create a scrollable text widget with reduced height
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, width=60, height=8)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        
        # Exit button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        button_frame.columnconfigure(0, weight=1)
        
        ttk.Button(button_frame, text="Exit", command=root.destroy).grid(row=0, column=0, sticky="e", padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=5, column=0, sticky="ew", padx=5, pady=5)
        
        # Initialize other variables
        self.processing_thread = None
        self.total_files = 0
        self.processed_files = 0
        self.files_changed = 0
        
        # Set appropriate window size to fit content
        self.root.update_idletasks()
        self.root.geometry("")  # Reset any existing geometry
        self.root.minsize(500, 400)  # Set minimum size
        
    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path.set(folder_path)
            
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def update_progress(self):
        if self.total_files > 0:
            progress = (self.processed_files / self.total_files) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"Processed: {self.processed_files}/{self.total_files} | Changed: {self.files_changed}")
        else:
            self.progress_var.set(0)
            self.status_var.set("No files to process")
            
    def count_m3u8_files(self, folder_path):
        """Count the total number of m3u8 files to process."""
        count = 0
        if self.recursive.get():
            for root, _, files in os.walk(folder_path):
                count += sum(1 for f in files if f.lower().endswith('.m3u8'))
        else:
            if os.path.isdir(folder_path):
                count = sum(1 for f in os.listdir(folder_path) if f.lower().endswith('.m3u8'))
                
        return count
            
    def replace_paths_in_m3u8(self, folder_path):
        """Replace path strings in m3u8 files."""
        if not os.path.isdir(folder_path):
            self.log(f"Error: {folder_path} is not a valid directory.")
            return
        
        find_text = self.find_text.get()
        replace_text = self.replace_text.get()
        
        self.log(f"Processing folder: {folder_path}")
        self.log(f"Replacing '{find_text}' with '{replace_text}'")
        
        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.m3u8'):
                file_path = os.path.join(folder_path, filename)
                
                # Read the file content
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                except UnicodeDecodeError:
                    # Try with a different encoding if UTF-8 fails
                    try:
                        with open(file_path, 'r', encoding='latin-1') as file:
                            content = file.read()
                    except Exception as e:
                        self.log(f"Error reading {file_path}: {e}")
                        self.processed_files += 1
                        self.update_progress()
                        continue
                except Exception as e:
                    self.log(f"Error reading {file_path}: {e}")
                    self.processed_files += 1
                    self.update_progress()
                    continue
                
                # Replace the paths
                new_content = content.replace(find_text, replace_text)
                
                # Only write if changes were made
                if new_content != content:
                    try:
                        with open(file_path, 'w', encoding='utf-8') as file:
                            file.write(new_content)
                        self.log(f"Updated: {file_path}")
                        self.files_changed += 1
                    except Exception as e:
                        self.log(f"Error writing to {file_path}: {e}")
                else:
                    self.log(f"No changes needed in: {file_path}")
                
                self.processed_files += 1
                self.update_progress()
                
    def process_folders(self):
        """Process all folders according to settings."""
        folder_path = self.folder_path.get()
        
        if not folder_path:
            messagebox.showerror("Error", "Please select a folder.")
            return
            
        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", "The selected path is not a valid directory.")
            return
            
        # Clear the log
        self.log_text.delete(1.0, tk.END)
        
        # Reset counters
        self.total_files = self.count_m3u8_files(folder_path)
        self.processed_files = 0
        self.files_changed = 0
        
        self.log(f"Found {self.total_files} .m3u8 files to process.")
        self.update_progress()
        
        if self.recursive.get():
            for root, _, _ in os.walk(folder_path):
                self.replace_paths_in_m3u8(root)
        else:
            self.replace_paths_in_m3u8(folder_path)
            
        self.log(f"\nProcessing complete.")
        self.log(f"Total files processed: {self.processed_files}")
        self.log(f"Files changed: {self.files_changed}")
        
        self.status_var.set("Processing completed")
        # messagebox.showinfo("Complete", f"Processing complete.\nFiles processed: {self.processed_files}\nFiles changed: {self.files_changed}")
            
    def start_processing(self):
        """Start the processing in a separate thread to keep the UI responsive."""
        if self.processing_thread and self.processing_thread.is_alive():
            messagebox.showinfo("Processing in Progress", "Processing is already running.")
            return
            
        self.processing_thread = threading.Thread(target=self.process_folders)
        self.processing_thread.daemon = True
        self.processing_thread.start()

def main():
    root = tk.Tk()
    app = M3U8PathReplacerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()