import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import threading
import json
from pathlib import Path

# TkinterDnD for drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_SUPPORTED = True
except ImportError:
    DRAG_DROP_SUPPORTED = False

class SimpleMp3TrimmerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple MP3 Trimmer")
        self.root.geometry("900x730")
        
        # Variables
        self.files = []
        self.files_custom_trims = {}  # To store custom trim values for specific files
        self.start_trim_var = tk.DoubleVar(value=0.0)
        self.end_trim_var = tk.DoubleVar(value=0.0)
        self.suffix_var = tk.StringVar(value="  TRM")
        
        # Load presets
        self.presets = self.load_presets()
        self.current_preset = tk.StringVar(value="")
        
        # Set initial preset if any exist
        if self.presets:
            self.current_preset.set(list(self.presets.keys())[0])
        
        # Create UI
        self.create_ui()
        
        # Setup drag and drop
        self.setup_drag_drop()
        
        # Processing flag
        self.processing = False
        
        # Preview-related variables
        self.preview_process = None
        self.is_previewing = False
        self.selected_file = None
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality if available"""
        # Check if we're using TkinterDnD
        if DRAG_DROP_SUPPORTED:
            self.file_listbox_dnd_setup = False  # Will be set up when listbox is created
        else:
            print("Drag and drop not available - install tkinterdnd2 package")
    
    def create_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Preset selection frame
        preset_frame = ttk.LabelFrame(main_frame, text="Presets", padding="10")
        preset_frame.pack(fill=tk.X, pady=5)
        
        # Preset dropdown
        ttk.Label(preset_frame, text="Select Preset:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.preset_dropdown = ttk.Combobox(preset_frame, textvariable=self.current_preset, state="readonly", width=20)
        self.preset_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.preset_dropdown.bind('<<ComboboxSelected>>', self.load_preset_values)
        
        # Preset buttons
        preset_btn_frame = ttk.Frame(preset_frame)
        preset_btn_frame.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Button(preset_btn_frame, text="Save", command=self.save_preset).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_btn_frame, text="Delete", command=self.delete_preset).pack(side=tk.LEFT, padx=2)
        
        # Update preset dropdown
        self.update_preset_dropdown()
        
        # Trim settings frame
        trim_frame = ttk.LabelFrame(main_frame, text="Trim Settings", padding="10")
        trim_frame.pack(fill=tk.X, pady=5)
        
        # Start trim
        start_frame = ttk.Frame(trim_frame)
        start_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(start_frame, text="Trim from start:").pack(side=tk.LEFT, padx=2)
        
        # Increment/decrement buttons
        ttk.Button(start_frame, text="-", width=2, 
                   command=lambda: self.adjust_trim('start', -0.1)).pack(side=tk.LEFT)
        
        ttk.Spinbox(start_frame, from_=0, to=300, increment=0.1, 
                    textvariable=self.start_trim_var, width=8).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(start_frame, text="+", width=2, 
                   command=lambda: self.adjust_trim('start', 0.1)).pack(side=tk.LEFT)
        
        ttk.Label(start_frame, text="seconds").pack(side=tk.LEFT, padx=2)
        
        self.start_preview_btn = ttk.Button(start_frame, text="▶ Play", 
                                            command=lambda: self.preview_trim('start'))
        self.start_preview_btn.pack(side=tk.LEFT, padx=5)
        
        # End trim
        end_frame = ttk.Frame(trim_frame)
        end_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.E)
        
        ttk.Label(end_frame, text="Trim from end:").pack(side=tk.LEFT, padx=2)
        
        # Increment/decrement buttons
        ttk.Button(end_frame, text="-", width=2, 
                   command=lambda: self.adjust_trim('end', -0.1)).pack(side=tk.LEFT)
        
        ttk.Spinbox(end_frame, from_=0, to=300, increment=0.1, 
                   textvariable=self.end_trim_var, width=8).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(end_frame, text="+", width=2, 
                   command=lambda: self.adjust_trim('end', 0.1)).pack(side=tk.LEFT)
        
        ttk.Label(end_frame, text="seconds").pack(side=tk.LEFT, padx=2)
        
        self.end_preview_btn = ttk.Button(end_frame, text="▶ Play", 
                                           command=lambda: self.preview_trim('end'))
        self.end_preview_btn.pack(side=tk.LEFT, padx=5)
        
        # Output suffix
        ttk.Label(trim_frame, text="Output suffix:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(trim_frame, textvariable=self.suffix_var, width=15).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # File list frame
        files_frame = ttk.LabelFrame(main_frame, text="MP3 Files", padding="10")
        files_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # File list with scrollbar
        scrollbar = ttk.Scrollbar(files_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(files_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        self.file_listbox.bind('<<ListboxSelect>>', self.file_selected)
        
        # Set up drag and drop for the listbox if supported
        if DRAG_DROP_SUPPORTED:
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self.on_drop)
            self.file_listbox_dnd_setup = True
            # Add indicator that drag and drop is available
            ttk.Label(files_frame, text="Drop MP3 files here").pack(pady=5)
        
        # Custom trim controls
        custom_frame = ttk.LabelFrame(main_frame, text="Custom Trim for Selected File", padding="5")
        custom_frame.pack(fill=tk.X, pady=5)
        
        self.custom_trim_var = tk.BooleanVar(value=False)
        custom_check = ttk.Checkbutton(custom_frame, text="Use custom trim values for selected file", 
                                       variable=self.custom_trim_var,
                                       command=self.toggle_custom_trim)
        custom_check.grid(row=0, column=0, columnspan=4, padx=5, pady=2, sticky=tk.W)
        
        # Custom trim values
        ttk.Label(custom_frame, text="Start:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.custom_start_var = tk.DoubleVar(value=0.0)
        self.custom_start_spin = ttk.Spinbox(custom_frame, from_=0, to=300, increment=0.1, 
                                            textvariable=self.custom_start_var, width=8, state="disabled")
        self.custom_start_spin.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(custom_frame, text="End:").grid(row=1, column=2, padx=5, pady=2, sticky=tk.W)
        self.custom_end_var = tk.DoubleVar(value=0.0)
        self.custom_end_spin = ttk.Spinbox(custom_frame, from_=0, to=300, increment=0.1, 
                                          textvariable=self.custom_end_var, width=8, state="disabled")
        self.custom_end_spin.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)
        
        ttk.Button(custom_frame, text="Apply Custom Values", command=self.apply_custom_values, 
                  state="disabled").grid(row=1, column=4, padx=5, pady=2)
        self.apply_custom_btn = custom_frame.winfo_children()[-1]  # Get the button we just created
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Add MP3 Files", command=self.add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Trim Files", command=self.process_files).pack(side=tk.RIGHT, padx=5)
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.progress_bar = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(pady=5)
    
    def update_preset_dropdown(self):
        """Update the preset dropdown with current presets"""
        self.preset_dropdown['values'] = list(self.presets.keys())
        if self.presets and not self.current_preset.get():
            self.current_preset.set(list(self.presets.keys())[0])
            self.load_preset_values()
    
    def load_presets(self):
        """Load presets from file"""
        preset_file = Path.home() / '.mp3_trimmer_presets.json'
        if preset_file.exists():
            try:
                with open(preset_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load presets: {str(e)}")
                return {}
        else:
            # Create default preset
            default_presets = {
                "Default": {"start_trim": 0.0, "end_trim": 0.0}
            }
            self.save_presets(default_presets)
            return default_presets
    
    def save_presets(self, presets=None):
        """Save presets to file"""
        if presets is None:
            presets = self.presets
        
        preset_file = Path.home() / '.mp3_trimmer_presets.json'
        try:
            with open(preset_file, 'w') as f:
                json.dump(presets, f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save presets: {str(e)}")
    
    def load_preset_values(self, event=None):
        """Load values from the selected preset"""
        preset_name = self.current_preset.get()
        if preset_name and preset_name in self.presets:
            preset = self.presets[preset_name]
            self.start_trim_var.set(preset['start_trim'])
            self.end_trim_var.set(preset['end_trim'])
    
    def save_preset(self):
        """Save current values as a preset"""
        # Create dialog to get preset name
        preset_dialog = tk.Toplevel(self.root)
        preset_dialog.title("Save Preset")
        preset_dialog.geometry("300x100")
        preset_dialog.transient(self.root)
        preset_dialog.grab_set()
        
        # Dialog content
        frame = ttk.Frame(preset_dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Preset Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        preset_name_var = tk.StringVar(value=self.current_preset.get())
        name_entry = ttk.Entry(frame, textvariable=preset_name_var, width=20)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        name_entry.select_range(0, tk.END)
        name_entry.focus()
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        def save():
            name = preset_name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a preset name")
                return
            
            # Confirm if overwriting existing preset
            if name in self.presets and name != self.current_preset.get():
                if not messagebox.askyesno("Confirm", f"Preset '{name}' already exists. Overwrite?"):
                    return
            
            # Save preset
            self.presets[name] = {
                "start_trim": self.start_trim_var.get(),
                "end_trim": self.end_trim_var.get()
            }
            self.save_presets()
            self.current_preset.set(name)
            self.update_preset_dropdown()
            preset_dialog.destroy()
        
        ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=preset_dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def delete_preset(self):
        """Delete the currently selected preset"""
        preset_name = self.current_preset.get()
        if not preset_name:
            return
        
        if len(self.presets) <= 1:
            messagebox.showinfo("Info", "Cannot delete the last preset")
            return
            
        if messagebox.askyesno("Confirm", f"Delete preset '{preset_name}'?"):
            del self.presets[preset_name]
            self.save_presets()
            self.current_preset.set(list(self.presets.keys())[0])
            self.update_preset_dropdown()
            self.load_preset_values()
    
    def add_files(self):
        """Add MP3 files to the list"""
        files = filedialog.askopenfilenames(
            title="Select MP3 files to trim",
            filetypes=(("MP3 files", "*.mp3"), ("All files", "*.*"))
        )
        
        for file in files:
            if file not in self.files:
                self.files.append(file)
                self.file_listbox.insert(tk.END, os.path.basename(file))
    
    def remove_selected(self):
        """Remove selected files from the list"""
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            return
        
        # Remove in reverse order to avoid index shifting
        for index in sorted(selected_indices, reverse=True):
            file = self.files[index]
            
            # Also remove from custom trims if present
            if file in self.files_custom_trims:
                del self.files_custom_trims[file]
                
            del self.files[index]
            self.file_listbox.delete(index)
        
        # Clear selected file if it was removed
        if self.selected_file not in self.files:
            self.selected_file = None
            self.custom_trim_var.set(False)
            self.toggle_custom_trim()
    
    def file_selected(self, event):
        """Handle file selection in listbox"""
        selection = self.file_listbox.curselection()
        if not selection:
            self.selected_file = None
            self.custom_trim_var.set(False)
            self.toggle_custom_trim()
            return
            
        index = selection[0]
        self.selected_file = self.files[index]
        
        # Check if this file has custom trim values
        if self.selected_file in self.files_custom_trims:
            custom_values = self.files_custom_trims[self.selected_file]
            self.custom_trim_var.set(True)
            self.custom_start_var.set(custom_values['start_trim'])
            self.custom_end_var.set(custom_values['end_trim'])
        else:
            self.custom_trim_var.set(False)
            self.custom_start_var.set(self.start_trim_var.get())
            self.custom_end_var.set(self.end_trim_var.get())
        
        self.toggle_custom_trim()
        
        # Stop any running preview
        self.stop_preview()
    
    def toggle_custom_trim(self):
        """Enable/disable custom trim controls based on checkbox"""
        if self.custom_trim_var.get() and self.selected_file:
            self.custom_start_spin.config(state="normal")
            self.custom_end_spin.config(state="normal")
            self.apply_custom_btn.config(state="normal")
        else:
            self.custom_start_spin.config(state="disabled")
            self.custom_end_spin.config(state="disabled")
            self.apply_custom_btn.config(state="disabled")
    
    def apply_custom_values(self):
        """Apply custom trim values to the selected file"""
        if not self.selected_file:
            return
        
        self.files_custom_trims[self.selected_file] = {
            'start_trim': self.custom_start_var.get(),
            'end_trim': self.custom_end_var.get()
        }
        
        messagebox.showinfo("Info", f"Custom trim values applied to: {os.path.basename(self.selected_file)}")
    
    def adjust_trim(self, trim_type, amount):
        """Adjust trim value by the given amount"""
        var = self.start_trim_var if trim_type == 'start' else self.end_trim_var
        current = var.get()
        # Round to nearest 0.1 second
        new_value = max(0, round((current + amount) * 10) / 10)
        var.set(new_value)
    
    def preview_trim(self, trim_type):
        """Preview the trim effect by playing 2 seconds at the trim point"""
        if self.is_previewing:
            self.stop_preview()
            return
            
        if not self.selected_file:
            messagebox.showinfo("Info", "Please select a file to preview")
            return
        
        # Update button text
        btn = self.start_preview_btn if trim_type == 'start' else self.end_preview_btn
        btn.config(text="■ Stop")
        self.is_previewing = True
        
        try:
            # Get appropriate trim values (custom or general)
            if self.selected_file in self.files_custom_trims and self.custom_trim_var.get():
                custom_values = self.files_custom_trims[self.selected_file]
                start_trim = custom_values['start_trim']
                end_trim = custom_values['end_trim']
            else:
                start_trim = self.start_trim_var.get()
                end_trim = self.end_trim_var.get()
            
            # Get file duration
            duration_cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                self.selected_file
            ]
            
            duration = float(subprocess.check_output(duration_cmd).decode().strip())
            
            if start_trim + end_trim >= duration:
                raise ValueError("The trim values exceed the file duration")
            
            # Preview settings - 2 seconds as requested
            preview_duration = 2.0
            
            if trim_type == 'start':
                # For start preview, play 2 seconds from the start_trim point
                preview_start = start_trim
            else:  # end preview
                # For end preview, play the last 2 seconds before the end trim
                preview_start = duration - end_trim - preview_duration
                if preview_start < 0:
                    preview_start = 0
                    preview_duration = duration - end_trim
            
            # Set up FFplay command for preview
            ffplay_cmd = [
                'ffplay',
                '-nodisp',  # No display window, just audio
                '-autoexit',
                '-ss', str(preview_start),
                '-t', str(preview_duration),
                self.selected_file
            ]
            
            self.preview_process = subprocess.Popen(ffplay_cmd)
            
            # Start a thread to wait for the preview to finish and reset the button
            threading.Thread(target=self.wait_for_preview_end, args=(btn,), daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Preview Error", str(e))
            btn.config(text="▶ Play")
            self.is_previewing = False
    
    def wait_for_preview_end(self, button):
        """Wait for preview process to end and reset button state"""
        if self.preview_process:
            self.preview_process.wait()
            
        # Reset button state
        self.root.after(0, lambda: button.config(text="▶ Play"))
        self.is_previewing = False
    
    def stop_preview(self):
        """Stop any running preview"""
        if self.preview_process and self.preview_process.poll() is None:
            self.preview_process.terminate()
            self.preview_process = None
            
        # Reset button states
        self.start_preview_btn.config(text="▶ Play")
        self.end_preview_btn.config(text="▶ Play")
        self.is_previewing = False
    
    def process_files(self):
        """Start processing files with the trim settings"""
        if not self.files:
            messagebox.showinfo("Info", "Please add MP3 files to process.")
            return
        
        if self.processing:
            messagebox.showinfo("Info", "Processing is already in progress.")
            return
        
        # Get default trim values from main controls
        default_start_trim = self.start_trim_var.get()
        default_end_trim = self.end_trim_var.get()
        suffix = self.suffix_var.get()
        
        # Start processing thread
        threading.Thread(target=self.process_files_thread, 
                        args=(default_start_trim, default_end_trim, suffix), 
                        daemon=True).start()
        
        self.processing = True
        self.progress_bar['value'] = 0
        self.status_label.config(text="Processing files...")
    
    def on_drop(self, event):
        """Handle files dropped onto the listbox"""
        try:
            # Get the dropped data
            data = event.data
            
            # Process the data based on format
            if '{' in data:  # For Windows/Linux with curly braces
                files = self.root.tk.splitlist(data)
                # Strip curly braces
                files = [f.strip('{}') for f in files]
            elif data.startswith('file:'):  # For macOS with file:// URLs
                # Split and decode file:// URLs
                files = [f.strip() for f in data.split()]
                files = [f.replace('file://', '') for f in files]
                # URL decode
                import urllib.parse
                files = [urllib.parse.unquote(f) for f in files]
            else:
                # Just treat as space-separated file paths
                files = data.split()
            
            # Add each file to the list if it's not already there
            for file in files:
                if os.path.isfile(file) and file.lower().endswith('.mp3') and file not in self.files:
                    self.files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
                    
            return 'ok'  # Return the acceptance value for the drop
            
        except Exception as e:
            messagebox.showerror("Drop Error", f"Error processing dropped files: {str(e)}")
            return 'cancel'  # Reject the drop
    
    def process_files_thread(self, default_start_trim, default_end_trim, suffix):
        """Thread to process files in background"""
        total_files = len(self.files)
        processed = 0
        errors = 0
        
        for file in self.files:
            try:
                # Update status
                filename = os.path.basename(file)
                self.root.after(0, lambda name=filename: self.status_label.config(text=f"Processing: {name}"))
                
                # Determine if using custom trim for this file
                if file in self.files_custom_trims:
                    custom_values = self.files_custom_trims[file]
                    start_trim = custom_values['start_trim']
                    end_trim = custom_values['end_trim']
                else:
                    start_trim = default_start_trim
                    end_trim = default_end_trim
                
                # Get file duration
                duration_cmd = [
                    'ffprobe', 
                    '-v', 'error', 
                    '-show_entries', 'format=duration', 
                    '-of', 'default=noprint_wrappers=1:nokey=1', 
                    file
                ]
                
                duration = float(subprocess.check_output(duration_cmd).decode().strip())
                new_duration = duration - start_trim - end_trim
                
                if new_duration <= 0:
                    self.root.after(0, lambda name=filename: 
                        messagebox.showerror("Error", f"The file {name} is too short to trim with these settings"))
                    errors += 1
                    continue
                
                # Create output filename
                base, ext = os.path.splitext(file)
                output_file = f"{base}{suffix}{ext}"
                
                # Execute ffmpeg command
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output file if exists
                    '-i', file,
                    '-ss', str(start_trim),
                    '-t', str(new_duration),
                    '-c:a', 'copy',  # Copy audio codec without re-encoding
                    output_file
                ]
                
                subprocess.check_call(ffmpeg_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                
                # Update progress
                processed += 1
                progress = int((processed / total_files) * 100)
                self.root.after(0, lambda p=progress: self.progress_bar.config(value=p))
                
            except Exception as e:
                self.root.after(0, lambda err=str(e), name=filename: 
                    messagebox.showerror("Error", f"Failed to process {name}: {err}"))
                errors += 1
        
        # Processing complete
        self.processing = False
        completion_message = f"Processing complete. {processed}/{total_files} files processed."
        if errors > 0:
            completion_message += f" ({errors} errors)"
            
        self.root.after(0, lambda msg=completion_message: self.status_label.config(text=msg))
        self.root.after(0, lambda msg=completion_message: messagebox.showinfo("Complete", msg))

# Run the application
if __name__ == "__main__":
    # Check if ffmpeg and ffprobe are installed
    try:
        subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
        subprocess.check_output(['ffprobe', '-version'], stderr=subprocess.STDOUT)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: ffmpeg and ffprobe are required. Please install them and make sure they are in your PATH.")
        messagebox.showerror("Error", "ffmpeg and ffprobe are required. Please install them and make sure they are in your PATH.")
        exit(1)
    
    # Use TkinterDnD for drag and drop if available
    if DRAG_DROP_SUPPORTED:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        
    app = SimpleMp3TrimmerApp(root)
    root.mainloop()