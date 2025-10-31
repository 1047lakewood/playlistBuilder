import tkinter as tk
from tkinter import ttk, filedialog
import os
import pygame
from pygame import mixer
import threading
import time
from tkinter import messagebox
from pydub import AudioSegment
import re
import subprocess  # Added for hiding console window

class FileEntry:
    def __init__(self, parent, file_path, remove_callback):
        self.parent = parent
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.remove_callback = remove_callback
        self.frame = tk.Frame(parent, bd=2, relief=tk.GROOVE, padx=10, pady=10)
        self.start_trim = tk.DoubleVar(value=0.0)  # Default 0.0 second trim
        self.end_trim = tk.DoubleVar(value=0.0)    # Default 0.0 second trim
        self.audio_length = self.get_audio_length()
        self.playing = False
        self.play_thread = None
        self.trim_increment = 0.3  # Increment by 0.3 seconds
        
        # Extract sort info from filename (for proper sorting)
        self.sort_info = self.extract_sort_info()
        
        # Create widgets
        self.create_widgets()
    
    def extract_sort_info(self):
        """Extract sorting information from filename"""
        try:
            perek_num = 0
            mishna_num = 0
            
            # Extract Perek number
            perek_match = re.search(r'Perek\s+(\d+)', self.filename)
            if perek_match:
                perek_num = int(perek_match.group(1))
                
            # Extract Mishna number
            mishna_match = re.search(r'Mishna\s+(\d+)', self.filename)
            if mishna_match:
                mishna_num = int(mishna_match.group(1))
                
            # Also try to get range like "Mishna 2-3"
            mishna_range_match = re.search(r'Mishna\s+(\d+)-(\d+)', self.filename)
            if mishna_range_match:
                mishna_num = int(mishna_range_match.group(1))  # Use start of range
                
            return (perek_num, mishna_num)
        except:
            return (0, 0)  # Default sort values if extraction fails
        
    def get_audio_length(self):
        """Get the length of the audio file in seconds"""
        try:
            # More efficient way to get audio length without loading entire file
            audio = AudioSegment.from_file(self.file_path)
            return len(audio) / 1000  # Length in seconds
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get audio length: {str(e)}")
            return 0
            
    def format_duration(self, seconds):
        """Format seconds into minutes and seconds display"""
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes} min {remaining_seconds} seconds"
        
    def create_widgets(self):
        # File name label
        tk.Label(self.frame, text=self.filename, font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # Remove button
        remove_btn = tk.Button(self.frame, text="✕", command=lambda: self.remove_callback(self))
        remove_btn.grid(row=0, column=3, sticky="e")
        
        # Start trim section
        start_frame = tk.Frame(self.frame)
        start_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        
        tk.Label(start_frame, text="Start Trim:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Start trim buttons and entry
        trim_start_controls = tk.Frame(start_frame)
        trim_start_controls.pack(side=tk.LEFT)
        
        tk.Button(trim_start_controls, text="-", width=2, command=lambda: self.adjust_trim(self.start_trim, -self.trim_increment, 0)).pack(side=tk.LEFT)
        self.start_trim_entry = tk.Entry(trim_start_controls, textvariable=self.start_trim, width=5)
        self.start_trim_entry.pack(side=tk.LEFT, padx=2)
        tk.Button(trim_start_controls, text="+", width=2, command=lambda: self.adjust_trim(self.start_trim, self.trim_increment, 0)).pack(side=tk.LEFT)
        
        # Play start button
        self.play_start_btn = tk.Button(start_frame, text="▶", width=2, command=self.play_start)
        self.play_start_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # End trim section
        end_frame = tk.Frame(self.frame)
        end_frame.grid(row=1, column=2, columnspan=2, sticky="e", pady=5)
        
        tk.Label(end_frame, text="End Trim:").pack(side=tk.LEFT, padx=(0, 5))
        
        # End trim buttons and entry
        trim_end_controls = tk.Frame(end_frame)
        trim_end_controls.pack(side=tk.LEFT)
        
        tk.Button(trim_end_controls, text="-", width=2, command=lambda: self.adjust_trim(self.end_trim, -self.trim_increment, 0)).pack(side=tk.LEFT)
        self.end_trim_entry = tk.Entry(trim_end_controls, textvariable=self.end_trim, width=5)
        self.end_trim_entry.pack(side=tk.LEFT, padx=2)
        tk.Button(trim_end_controls, text="+", width=2, command=lambda: self.adjust_trim(self.end_trim, self.trim_increment, 0)).pack(side=tk.LEFT)
        
        # Play end button
        self.play_end_btn = tk.Button(end_frame, text="▶", width=2, command=self.play_end)
        self.play_end_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Duration label
        formatted_duration = self.format_duration(self.audio_length)
        tk.Label(self.frame, text=f"Duration: {formatted_duration}", font=("Arial", 8)).grid(row=2, column=0, columnspan=4, sticky="w", pady=(5, 0))
        
    def adjust_trim(self, var, amount, min_val=0):
        """Adjust trim value with bounds checking"""
        current = var.get()
        new_val = max(min_val, current + amount)
        
        # Round to one decimal place for cleaner display
        new_val = round(new_val, 1)
        
        # Ensure start trim doesn't exceed audio length
        if var == self.start_trim and new_val >= self.audio_length - self.end_trim.get() - 0.5:
            new_val = self.audio_length - self.end_trim.get() - 0.5
            
        # Ensure end trim doesn't exceed audio length
        if var == self.end_trim and new_val >= self.audio_length - self.start_trim.get() - 0.5:
            new_val = self.audio_length - self.start_trim.get() - 0.5
            
        var.set(new_val)
        
    def play_audio(self, start_sec, duration):
        """Play a segment of audio in a separate thread"""
        try:
            # Store which button was pressed (start or end) before thread starts
            is_start_button = start_sec == self.start_trim.get()
            
            # Update UI in main thread
            self.parent.after(0, lambda: self.update_button_ui(is_start_button, "■"))
            
            # Don't reinitialize mixer if already initialized
            if not mixer.get_init():
                mixer.init()
            
            mixer.music.load(self.file_path)
            mixer.music.play(start=start_sec)
            self.playing = True
            
            # Wait for specified duration
            time.sleep(duration)
            
            if self.playing:
                mixer.music.stop()
                # Update UI in main thread
                self.parent.after(0, lambda: self.update_button_ui(is_start_button, "▶"))
                self.playing = False
                
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Playback Error", str(e)))
            
        finally:
            # Ensure button is reset in main thread
            self.parent.after(0, lambda: self.update_button_ui(is_start_button, "▶"))
            self.playing = False
    
    def update_button_ui(self, is_start_button, icon):
        """Update button UI in the main thread"""
        btn = self.play_start_btn if is_start_button else self.play_end_btn
        btn.config(text=icon)
            
    def play_start(self):
        """Play the start section of the audio for preview"""
        if self.playing:
            mixer.music.stop()
            self.play_start_btn.config(text="▶")
            self.play_end_btn.config(text="▶")
            self.playing = False
            if self.play_thread and self.play_thread.is_alive():
                self.play_thread.join(0.1)  # Don't block UI
        else:
            # The start trim value exactly represents where the audio will start after trimming
            start_position = self.start_trim.get()
            
            # Play from the start position for 3 seconds (or until the trimmed end)
            play_duration = min(3, self.audio_length - self.end_trim.get() - start_position)
            
            # Ensure at least 1 second of playback (if possible)
            play_duration = max(1, play_duration)
            
            self.play_thread = threading.Thread(target=self.play_audio, args=(start_position, play_duration))
            self.play_thread.daemon = True
            self.play_thread.start()
            
    def play_end(self):
        """Play the end section of the audio for preview"""
        if self.playing:
            mixer.music.stop()
            self.play_start_btn.config(text="▶")
            self.play_end_btn.config(text="▶")
            self.playing = False
            if self.play_thread and self.play_thread.is_alive():
                self.play_thread.join(0.1)  # Don't block UI
        else:
            # Calculate the exact position where the audio will end after trimming
            end_position = self.audio_length - self.end_trim.get()
            
            # Start playing a bit before that position (3 seconds) to give context
            # but make sure we don't go before the start trim
            preview_start = max(self.start_trim.get(), end_position - 3)
            
            # Play duration should be exactly to the end position
            play_duration = end_position - preview_start
            
            # Ensure at least 1 second of playback (if possible)
            play_duration = max(1, play_duration)
            
            self.play_thread = threading.Thread(target=self.play_audio, args=(preview_start, play_duration))
            self.play_thread.daemon = True
            self.play_thread.start()
            
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
        
    def grid(self, **kwargs):
        self.frame.grid(**kwargs)
        
    def destroy(self):
        """Clean up resources when removing this entry"""
        if self.playing:
            mixer.music.stop()
            self.playing = False
        # Ensure thread is properly terminated
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(0.1)  # Don't block UI
        self.frame.destroy()


class MishnayosCombiner:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Combine")
        self.root.geometry("700x600")
        self.root.minsize(750, 400)
        
        self.file_entries = []
        self.export_name = tk.StringVar(value="Combined_Mishnayos")
        self.initial_directory = None # Store the directory of the first file
        self.current_trim_target = 0.0 # Track the current global trim target for toggling
        
        # Initialize DnD support after the root window is created but before widgets
        self.has_dnd = self.setup_drag_drop()
        
        self.create_widgets()
        
    def setup_drag_drop(self):
        """Setup drag and drop functionality if available"""
        try:
            # Check if we're already using a TkinterDnD root window
            if hasattr(self.root, 'drop_target_register'):
                # Ensure the required DND_FILES constant is available in this context
                from tkinterdnd2 import DND_FILES
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self.on_drop)
                return True
            return False
        except (AttributeError, NameError, ImportError) as e:
            print(f"Drag and drop not available: {e}")
            return False
        
    def create_widgets(self):
        """Create all UI elements"""
        # Main container
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top section
        top_frame = tk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Instruction label
        if self.has_dnd:
            instruction_text = "Drag audio files here or click Add Files"
        else:
            instruction_text = "Click Add Files to select audio files"
        
        tk.Label(top_frame, text=instruction_text, font=("Arial", 12)).pack(side=tk.LEFT)
        
        # Add files button
        add_btn = tk.Button(top_frame, text="Add Files", command=self.add_files)
        add_btn.pack(side=tk.RIGHT)
        
        # Toggle all trims button
        self.toggle_trim_btn = tk.Button(top_frame, text="Set Trims to 5.0", command=self.toggle_all_trims)
        self.toggle_trim_btn.pack(side=tk.RIGHT, padx=10)
        
        # Sort button
        sort_btn = tk.Button(top_frame, text="Sort Files", command=self.sort_files)
        sort_btn.pack(side=tk.RIGHT, padx=10)
        
        # Files container with scrollbar
        files_container = tk.Frame(main_frame)
        files_container.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable frame for files
        self.canvas = tk.Canvas(files_container)
        scrollbar = ttk.Scrollbar(files_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bottom section
        bottom_frame = tk.Frame(main_frame, pady=10)
        bottom_frame.pack(fill=tk.X)
        
        # Export name section
        name_frame = tk.Frame(bottom_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(name_frame, text="Export filename:").pack(side=tk.LEFT)
        tk.Entry(name_frame, textvariable=self.export_name, width=40).pack(side=tk.LEFT, padx=5)
        tk.Label(name_frame, text=".mp3").pack(side=tk.LEFT)
        
        # Export button
        export_btn = tk.Button(bottom_frame, text="Export Combined Audio", command=self.export_combined)
        export_btn.pack()
        
    def toggle_all_trims(self):
        """Toggle all trim values between 0.0 and 5.0"""
        if not self.file_entries:
            # No message box needed, just do nothing
            print("No files to set trims for.")
            return

        # Determine the target trim value based on the current state
        next_target_trim = 5.0 if self.current_trim_target == 0.0 else 0.0

        # Update all trim values
        for file_entry in self.file_entries:
            file_entry.start_trim.set(next_target_trim)
            file_entry.end_trim.set(next_target_trim)

        # Update the current target and button text
        self.current_trim_target = next_target_trim
        next_button_text = "Set Trims to 0.0" if next_target_trim == 5.0 else "Set Trims to 5.0"
        self.toggle_trim_btn.config(text=next_button_text)

        print(f"All trim values set to {next_target_trim}.")
        # No success messagebox needed

    def reset_all_trims(self):
        """Reset all trim values to 0"""
        if not self.file_entries:
            # messagebox.showinfo("Info", "No files to reset. Please add some audio files first.") # Removed
            return
            
        # Confirm with user - Keep confirmation for safety? User asked for no alerts, maybe remove this too?
        # Let's remove confirmation for now as per "I dont want alerts"
        # confirm = messagebox.askyesno(
        #     "Confirm Reset", 
        #     "This will set all trim values to 0, meaning no parts of the audio files will be trimmed. Continue?"
        # )
        # 
        # if not confirm:
        #     return
            
        # Reset all trim values
        for file_entry in self.file_entries:
            file_entry.start_trim.set(0.0)
            file_entry.end_trim.set(0.0)
            
        # messagebox.showinfo("Success", "All trim values have been reset to 0.") # Removed
        
    def sort_files(self):
        """Sort files by perek and mishna numbers"""
        if len(self.file_entries) <= 1:
            return  # No need to sort
            
        # Sort file entries based on extracted sort info
        self.file_entries.sort(key=lambda entry: entry.sort_info)
        
        # Clear the scrollable frame and re-add entries in sorted order
        for entry in self.file_entries:
            entry.frame.pack_forget()
            
        for entry in self.file_entries:
            entry.pack(fill=tk.X, padx=5, pady=5)
            
        # Update the default export name based on the first file
        if self.file_entries:
            self.update_export_name(self.file_entries[0].file_path)
            # Also ensure initial directory is set if it wasn't (e.g., if files were added before this was implemented)
            if self.initial_directory is None:
                 self.initial_directory = os.path.dirname(self.file_entries[0].file_path)
        
    def on_drop(self, event):
        """Handle drag and drop events"""
        try:
            data = event.data
            print(f"Drop event received with data: {data}")
            
            # Handle different formats of drag and drop data
            if data.startswith('{'):
                # Windows format
                files = self.parse_windows_drop(data)
            else:
                # Unix format
                files = data.split()
            
            # Store valid files
            valid_files = []
            
            # Process each file
            for file_path in files:
                print(f"Processing dropped file: {file_path}")
                if self.is_valid_audio_file(file_path):
                    valid_files.append(file_path)
                else:
                    print(f"Invalid file type or inaccessible: {file_path}")
            
            # Sort files by name before adding (helps with natural ordering)
            valid_files.sort(key=lambda path: os.path.basename(path))
            
            # Add the files in sorted order
            for file_path in valid_files:
                self.add_file_entry(file_path)
                
            # Now sort files by Perek and Mishna if possible
            self.sort_files()
                    
        except Exception as e:
            print(f"Error in on_drop: {e}")
            messagebox.showerror("Error", f"Failed to process dropped files: {str(e)}")
                
    def is_valid_audio_file(self, file_path):
        """Check if file is a valid audio file that can be processed"""
        valid_extensions = ('.mp3', '.wav', '.m4a', '.ogg', '.flac')
        if not file_path.lower().endswith(valid_extensions):
            return False
            
        # Basic check that file exists and is accessible
        if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
            return False
            
        return True
                
    def parse_windows_drop(self, data):
        """Parse Windows Explorer drag-drop format"""
        files = []
        # Windows Explorer DnD format can be complex with curly braces
        # First, try to handle the simplest case with one file
        if data.startswith('{') and data.endswith('}'):
            path = data.strip('{}').replace('\\', '/')
            if os.path.isfile(path):
                files.append(path)
                return files
                
        # Handle multiple files
        for item in data.strip('{}').split('} {'):
            path = item.strip('{}').replace('\\', '/')
            if os.path.isfile(path) and path.lower().endswith(('.mp3', '.wav', '.m4a', '.ogg', '.flac')):
                files.append(path)
        
        return files
        
    def add_files(self):
        """Open file dialog to add audio files"""
        file_paths = filedialog.askopenfilenames(
            title="Select Audio Files",
            filetypes=(
                ("Audio Files", "*.mp3 *.wav *.m4a *.ogg *.flac"),
                ("All Files", "*.*")
            )
        )
        
        # Convert to list and sort by filename
        file_paths_list = list(file_paths)
        file_paths_list.sort(key=lambda path: os.path.basename(path))
        
        for file_path in file_paths_list:
            if self.is_valid_audio_file(file_path):
                self.add_file_entry(file_path)
                
        # Sort by Perek and Mishna if possible
        self.sort_files()
            
    def add_file_entry(self, file_path):
        """Add a new file entry to the UI"""
        file_entry = FileEntry(self.scrollable_frame, file_path, self.remove_file_entry)
        file_entry.pack(fill=tk.X, padx=5, pady=5)
        self.file_entries.append(file_entry)
        
        # Update the default export name and initial directory based on the first file
        if len(self.file_entries) == 1:
            self.update_export_name(file_path)
            self.initial_directory = os.path.dirname(file_path)
        
    def remove_file_entry(self, file_entry):
        """Remove a file entry from the UI and the list"""
        if file_entry in self.file_entries:
            self.file_entries.remove(file_entry)
            file_entry.destroy()
            
            # If we removed the first file and there are still files left,
            # update the export name based on the new first file
            if self.file_entries and file_entry == self.file_entries[0]:
                self.update_export_name(self.file_entries[0].file_path)
            # Update initial directory if the first file was removed
            elif self.file_entries:
                 self.initial_directory = os.path.dirname(self.file_entries[0].file_path)
            else:
                 self.initial_directory = None # Reset if no files left
            
    def export_combined(self):
        """Export the combined audio file"""
        if not self.file_entries:
            # messagebox.showinfo("Info", "No files to combine. Please add some audio files first.") # Removed
            print("No files to combine.")
            return
            
        export_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            initialfile=f"{self.export_name.get()}.mp3",
            initialdir=self.initial_directory, # Set initial directory
            filetypes=[("MP3 Files", "*.mp3")]
        )
        
        if not export_path:
            return  # User cancelled
            
        try:
            # Show progress window
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Exporting...")
            progress_window.geometry("300x100")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # Add a label with a unique name so we can reference it from threads
            progress_label = tk.Label(progress_window, text="Processing files...", name="progress_label")
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, mode="determinate", name="progress_bar")
            progress_bar.pack(fill=tk.X, padx=20)
            progress_bar["maximum"] = len(self.file_entries)
            
            # Store references to file entries to prevent thread issues
            file_entries_copy = self.file_entries.copy()
            
            # Run export in a thread to keep UI responsive
            threading.Thread(target=self._process_export, args=(export_path, progress_window, file_entries_copy), daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred during export: {str(e)}")
            
    def update_export_name(self, file_path):
        """Extract information from filename to create a default export name"""
        filename = os.path.basename(file_path)
        
        # Default fallback
        default_name = "Combined_Mishnayos"
        
        try:
            # Extract details from filename
            # Format: "Perek 4 Mishna 2-3, Masechet Berachos, Sefer Mishnayos, Chapter 4 - Harav Ezer Shwalbe - 45062.mp3"
            
            # Extract Masechet name
            masechet_match = None
            if "Masechet " in filename:
                masechet_parts = filename.split("Masechet ")[1].split(",")[0].strip()
                masechet_match = masechet_parts
                
            # Extract Perek number
            perek_match = None
            if "Perek " in filename:
                perek_parts = filename.split("Perek ")[1].split(" ")[0].strip()
                perek_match = perek_parts
                
            # Extract Rabbi name
            rabbi_match = None
            if "Harav " in filename:
                rabbi_parts = filename.split("Harav ")[1].split(" - ")[0].strip()
                rabbi_match = rabbi_parts
            
            # Create new export name
            if masechet_match and perek_match and rabbi_match:
                new_name = f"Masechet {masechet_match} Perek {perek_match} Mishna Harav {rabbi_match} M"
                self.export_name.set(new_name)
            else:
                self.export_name.set(default_name)
                
        except Exception as e:
            # If anything goes wrong, use the default name
            print(f"Error parsing filename: {e}")
            self.export_name.set(default_name)
            
    def _process_export(self, export_path, progress_window, file_entries):
        """Process and export the combined audio file"""
        try:
            combined = AudioSegment.empty()
            
            for idx, file_entry in enumerate(file_entries):
                # Update progress label and bar safely through the main thread
                self.root.after(0, lambda i=idx, total=len(file_entries): 
                    (progress_window.nametowidget("progress_label").config(
                        text=f"Processing file {i+1} of {total}..."),
                    progress_window.nametowidget("progress_bar").config(value=i)))
                
                try:
                    # Process one file at a time to reduce memory usage
                    audio = AudioSegment.from_file(file_entry.file_path)
                    
                    # Apply trimming with a small buffer to prevent artifacts
                    start_ms = int(file_entry.start_trim.get() * 1000)
                    end_ms = int(file_entry.end_trim.get() * 1000)
                    
                    # Calculate the end position in milliseconds
                    end_position = len(audio) - end_ms
                    
                    # Apply trimming: start from start_ms and stop at end_position
                    trimmed_audio = audio[start_ms:end_position]
                    
                    # Add a small gap of silence between files to prevent any audio artifacts
                    if idx > 0:
                        # Add 50ms of silence between audio files
                        silence = AudioSegment.silent(duration=50)
                        combined += silence
                    
                    combined += trimmed_audio
                    
                    # Clear reference to original audio to free memory
                    audio = None
                except Exception as e:
                    # If processing a single file fails, show warning but continue with other files
                    error_msg = f"Error processing {os.path.basename(file_entry.file_path)}: {str(e)}"
                    print(f"Warning: {error_msg}") # Replaced messagebox.showwarning
                    # self.root.after(0, lambda msg=error_msg: messagebox.showwarning("Processing Warning", msg))
            
            # Export the combined audio
            self.root.after(0, lambda: 
                (progress_window.nametowidget("progress_label").config(text="Saving combined file..."),
                progress_window.nametowidget("progress_bar").config(value=len(file_entries))))
                
            combined.export(export_path, format="mp3")

            # --- Set metadata using mutagen ---
            try:
                from mutagen.easyid3 import EasyID3
                from mutagen.mp3 import MP3
                # Get Artist from first file
                from mutagen.id3 import ID3NoHeaderError
                first_file = file_entries[0].file_path if file_entries else None
                artist = None
                if first_file:
                    try:
                        audio_tags = EasyID3(first_file)
                        artist = audio_tags.get('artist', [None])[0]
                    except ID3NoHeaderError:
                        artist = None
                # Remove Rabbi name from export name for Title
                export_title = self.export_name.get()
                import re
                export_title = re.sub(r" ?Harav [^ ]+", "", export_title).strip()
                # Set metadata
                audio = MP3(export_path, ID3=EasyID3)
                if artist:
                    audio['artist'] = artist
                audio['title'] = export_title
                audio.save()
                print(f"Set metadata: Artist='{artist}', Title='{export_title}'")
            except Exception as meta_e:
                print(f"Warning: Could not set metadata: {meta_e}")
            
            # Close progress window and show success in main thread
            def on_export_complete():
                try:
                    if progress_window.winfo_exists():
                        progress_window.destroy()
                    # messagebox.showinfo("Success", f"Combined audio saved to:\n{export_path}") # Removed
                    print(f"Success! Combined audio saved to: {export_path}")
                except:
                    pass  # Window might already be destroyed
                    
            self.root.after(0, on_export_complete)
            
        except Exception as e:
            # Close progress window and show error in main thread
            def on_export_error(error_msg):
                try:
                    if progress_window.winfo_exists():
                        progress_window.destroy()
                    messagebox.showerror("Export Error", f"An error occurred during export: {error_msg}")
                except:
                    pass  # Window might already be destroyed
                    
            self.root.after(0, lambda: on_export_error(str(e)))


if __name__ == "__main__":
    # --- Configuration for hiding console window on Windows ---
    startupinfo = None
    if os.name == 'nt':
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            # You might also need creationflags=subprocess.CREATE_NO_WINDOW
            # but setting startupinfo.wShowWindow often suffices.
            # Pydub internally uses subprocess, this might influence its calls.
        except AttributeError:
             print("Could not configure subprocess startup info (likely not on Windows or old Python).")
             startupinfo = None # Ensure it's None if setup fails
    # ----------------------------------------------------------

    # Initialize only pygame mixer (not all of pygame)
    pygame.mixer.init()
    
    # Setup tkinter with drag and drop
    try:
        # Import TkinterDnD before creating the root window
        from tkinterdnd2 import DND_FILES, TkinterDnD
        print("TkinterDnD2 imported successfully")
        
        # Create a root window with TkinterDnD
        root = TkinterDnD.Tk()
        print("TkinterDnD root window created")
        
    except ImportError as e:
        # Fallback to regular Tk
        print(f"TkinterDnD import failed: {e}")
        root = tk.Tk()
        # root.after(1000, lambda: messagebox.showwarning("Feature Limited", # Removed
        #                    "Drag and drop functionality is not available.\n"
        #                    "Please install tkinterdnd2 for full functionality."))
        print("Warning: Drag and drop functionality is not available. Install tkinterdnd2 for this feature.")
    
    # Create the application with the root window
    app = MishnayosCombiner(root)
    
    # Start the main event loop
    root.mainloop()