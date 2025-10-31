import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyaudio
import wave
import os
import threading
import time
import numpy as np
from datetime import datetime
from pydub import AudioSegment
from pydub.playback import play as pydub_play
import io
import tempfile

class QuickRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quick Audio Recorder")
        self.root.geometry("480x600")  # Increased height for new controls
        self.root.resizable(False, False)
        
        # Audio recording parameters
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.frames = []
        self.recording = False
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording_thread = None
        self.recording_time = 0
        self.timer_thread = None
        self.timer_running = False
        self.recording_counter = 1
        self.is_playing = False  # Flag to prevent multiple playbacks
        
        # Get available input devices and find default
        self.input_devices = self.get_filtered_input_devices()
        self.default_device_index = self.get_default_device_index()
        
        # Set default recordings folder
        self.recordings_folder = os.path.join(os.path.expanduser("~"), "recordings")
        if not os.path.exists(self.recordings_folder):
            os.makedirs(self.recordings_folder)
        
        # Create GUI
        self.create_widgets()
        
    def get_filtered_input_devices(self):
        """Get all available input devices with filtering for duplicates"""
        devices = []
        seen_names = set()
        
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # Input device
                name = device_info['name']
                # Simple filtering - if we haven't seen this exact name before
                if name not in seen_names:
                    devices.append((i, name))
                    seen_names.add(name)
        
        return devices
    
    def get_default_device_index(self):
        """Find the system default input device"""
        try:
            default_index = self.audio.get_default_input_device_info()['index']
            # Find the position in our filtered list
            for i, (device_index, _) in enumerate(self.input_devices):
                if device_index == default_index:
                    return i
        except Exception:
            pass
        
        return 0  # Fallback to first device if default not found
    
    def create_widgets(self):
        # Main frame with padding
        style = ttk.Style()
        style.configure("TFrame", padding=5)
        style.configure("TLabelframe", padding=5)
        style.configure("TButton", padding=5)
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title and instructions
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="Quick Audio Recorder", font=("Helvetica", 14, "bold"))
        title_label.pack(side=tk.TOP)
        
        # Status and timer in a frame
        status_frame = ttk.LabelFrame(main_frame, text="Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Ready to record")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.timer_label = ttk.Label(status_frame, text="00:00", font=("Helvetica", 12, "bold"))
        self.timer_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Audio visualization canvas
        viz_frame = ttk.LabelFrame(main_frame, text="Audio Visualization")
        viz_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.viz_canvas = tk.Canvas(viz_frame, height=60, bg="black", highlightthickness=0)
        self.viz_canvas.pack(fill=tk.X, padx=5, pady=5)
        
        # Create initial visualization background
        self.viz_canvas.create_line(0, 30, 480, 30, fill="#333333", width=1)  # Center line
        
        # Input device selection
        device_frame = ttk.Frame(main_frame)
        device_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(device_frame, text="Input Source:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.device_var = tk.StringVar()
        self.device_combobox = ttk.Combobox(device_frame, textvariable=self.device_var, state="readonly")
        self.device_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Populate input devices
        if self.input_devices:
            device_names = [device[1] for device in self.input_devices]
            self.device_combobox['values'] = device_names
            self.device_combobox.current(self.default_device_index)
            self.device_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)

        # Name entry
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(name_frame, text="Recording name:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.name_entry = ttk.Entry(name_frame)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Trim options
        trim_frame = ttk.LabelFrame(main_frame, text="Trimming Options")
        trim_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Enable trim checkbox
        self.trim_var = tk.BooleanVar(value=True)
        self.trim_check = ttk.Checkbutton(
            trim_frame, 
            text="Enable trimming", 
            variable=self.trim_var
        )
        self.trim_check.pack(side=tk.TOP, anchor=tk.W, padx=5, pady=(5,0))
        
        # Start trim controls
        start_trim_frame = ttk.Frame(trim_frame)
        start_trim_frame.pack(fill=tk.X, padx=5, pady=(5,0))
        
        ttk.Label(start_trim_frame, text="Start trim (seconds):").pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_trim_var = tk.DoubleVar(value=1.0)
        self.start_trim_spinner = ttk.Spinbox(
            start_trim_frame,
            from_=0.0,
            to=10.0,
            increment=0.1,
            textvariable=self.start_trim_var,
            width=5
        )
        self.start_trim_spinner.pack(side=tk.LEFT)
        
        # End trim controls
        end_trim_frame = ttk.Frame(trim_frame)
        end_trim_frame.pack(fill=tk.X, padx=5, pady=(5,5))
        
        ttk.Label(end_trim_frame, text="End trim (seconds):").pack(side=tk.LEFT, padx=(0, 5))
        
        self.end_trim_var = tk.DoubleVar(value=0.0)
        self.end_trim_spinner = ttk.Spinbox(
            end_trim_frame,
            from_=0.0,
            to=10.0,
            increment=0.1,
            textvariable=self.end_trim_var,
            width=5
        )
        self.end_trim_spinner.pack(side=tk.LEFT)
        
        # Record/Stop button with clear color indicators
        self.record_button = ttk.Button(
            main_frame, 
            text="⏺️ Record", 
            command=self.toggle_recording,
            style="Record.TButton"
        )
        self.record_button.pack(fill=tk.X, pady=(0, 10))
        
        # Configure styles for record/stop button
        style.configure("Record.TButton", background="#ff4d4d", foreground="white")
        style.map("Record.TButton", background=[("active", "#ff6666")])
        style.configure("Stop.TButton", background="#4CAF50", foreground="white")
        style.map("Stop.TButton", background=[("active", "#66BB6A")])
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Save button
        self.save_button = ttk.Button(button_frame, text="Save", command=self.save_recording)
        self.save_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.save_button["state"] = "disabled"
        
        # Play button
        self.play_button = ttk.Button(button_frame, text="Play", command=self.play_recording)
        self.play_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        self.play_button["state"] = "disabled"
        
        # Folder selection frame
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(fill=tk.X, pady=(15, 15))
        
        ttk.Label(folder_frame, text="Save to folder:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Folder path display (truncated if too long)
        self.folder_var = tk.StringVar(value=self.recordings_folder)
        self.folder_label = ttk.Label(folder_frame, textvariable=self.folder_var, 
                                     anchor=tk.W, background="#f0f0f0")
        self.folder_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Browse button
        self.browse_button = ttk.Button(folder_frame, text="Browse...", 
                                       command=self.select_folder, width=10)
        self.browse_button.pack(side=tk.RIGHT)
        
        # Recent recordings label
        ttk.Label(main_frame, text="Recent recordings:").pack(anchor=tk.W, pady=(10, 5))
        
        # Recent recordings list
        self.recent_list = tk.Listbox(main_frame, height=3)
        self.recent_list.pack(fill=tk.X)
        
        # Update the recent recordings list
        self.update_recent_list()
        
    def on_device_selected(self, event):
        """Handle input device selection"""
        selection = self.device_combobox.current()
        if selection >= 0 and selection < len(self.input_devices):
            self.selected_device_index = self.input_devices[selection][0]
    
    def select_folder(self):
        """Open dialog to select folder for recordings"""
        folder = filedialog.askdirectory(
            initialdir=self.recordings_folder,
            title="Select folder for recordings"
        )
        
        if folder:  # If user didn't cancel
            self.recordings_folder = folder
            
            # Create the folder if it doesn't exist
            if not os.path.exists(self.recordings_folder):
                os.makedirs(self.recordings_folder)
            
            # Update display (truncate if too long)
            max_length = 40
            if len(folder) > max_length:
                display_path = "..." + folder[-(max_length-3):]
            else:
                display_path = folder
            self.folder_var.set(display_path)
            
            # Update recent recordings list for the new folder
            self.update_recent_list()
    
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.frames = []
        self.recording = True
        self.recording_time = 0
        
        # Clear visualization
        self.viz_canvas.delete("all")
        
        # Update UI
        self.record_button.config(text="Stop")
        self.status_label.config(text="Recording...")
        self.save_button["state"] = "disabled"
        
        # Start audio stream with selected input device
        try:
            self.selected_device_index = self.input_devices[self.device_combobox.current()][0]
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.selected_device_index,
                frames_per_buffer=self.chunk
            )
            
            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            # Start timer
            self.timer_running = True
            self.timer_thread = threading.Thread(target=self.update_timer)
            self.timer_thread.daemon = True
            self.timer_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start recording: {e}")
            self.recording = False
            self.status_label.config(text="Recording failed")
            self.record_button.config(text="Record")
    
    def record_audio(self):
        while self.recording:
            try:
                data = self.stream.read(self.chunk)
                self.frames.append(data)
                
                # Update visualization in main thread
                self.update_audio_viz(data)
                
            except Exception as e:
                print(f"Error recording: {e}")
                self.recording = False
                break
    
    def update_audio_viz(self, data):
        """Update the audio visualization"""
        if not self.recording or not self.viz_canvas.winfo_exists():
            return
            
        try:
            # Convert to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Compute RMS amplitude
            rms = np.sqrt(np.mean(np.square(audio_data))) / 32768.0  # Normalize to 0-1
            
            # Check for NaN values and constrain
            if np.isnan(rms):
                bar_height = 0
            else:
                # Scale to visualization height (0-25)
                bar_height = int(min(max(rms * 25, 0), 25))  # Constrain to 0-25
            
            # Plot on canvas in main thread
            self.root.after(0, lambda h=bar_height: self.draw_viz_bar(h))
        except Exception as e:
            print(f"Visualization error: {e}")
            # Just skip this frame on error
    
    def draw_viz_bar(self, height):
        """Draw a visualization bar on the canvas"""
        if not self.viz_canvas.winfo_exists():
            return
            
        try:
            canvas_width = self.viz_canvas.winfo_width()
            if canvas_width <= 1:  # Canvas not ready yet
                canvas_width = 480  # Default width
                
            canvas_height = self.viz_canvas.winfo_height()
            center_y = canvas_height // 2
            
            # Shift existing bars to the left
            self.viz_canvas.move("bar", -2, 0)
            
            # Remove bars that are now off-screen
            for item in self.viz_canvas.find_withtag("bar"):
                if self.viz_canvas.coords(item)[2] < 0:
                    self.viz_canvas.delete(item)
            
            # Add new bar at right edge (centered vertically)
            self.viz_canvas.create_rectangle(
                canvas_width - 2, center_y - height,
                canvas_width, center_y + height,
                fill="#00FF00", tags="bar", outline=""
            )
        except Exception as e:
            print(f"Draw visualization error: {e}")
    
    def update_timer(self):
        while self.timer_running:
            mins, secs = divmod(self.recording_time, 60)
            timer_text = f"{mins:02d}:{secs:02d}"
            
            # Update the timer label in the main thread
            self.root.after(0, lambda t=timer_text: self.timer_label.config(text=t))
            
            time.sleep(1)
            self.recording_time += 1
    
    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.timer_running = False
            
            # Stop and close the stream
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Update UI
            self.record_button.config(text="⏺️ Record", style="Record.TButton")
            self.status_label.config(text="Recording stopped")
            self.save_button["state"] = "normal"
            self.play_button["state"] = "normal"
            
            # Set default name with "R " prefix and counter
            default_name = f"R {self.recording_counter}"
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, default_name)
            self.recording_counter += 1
            self.name_entry.focus()
    
    def trim_audio(self, audio_segment):
        """Trim the specified seconds from beginning and end of the audio"""
        if not self.trim_var.get():
            return audio_segment
            
        # Get trim values
        start_trim = self.start_trim_var.get() * 1000  # Convert to milliseconds
        end_trim = self.end_trim_var.get() * 1000
        
        # Get total audio length
        total_length = len(audio_segment)
        
        # Make sure we don't trim too much
        if start_trim + end_trim >= total_length:
            # If the trim would remove everything, just trim half from the start
            start_trim = min(start_trim, total_length / 2)
            end_trim = 0
            
        # Return trimmed audio
        if end_trim > 0:
            # Trim from both start and end
            return audio_segment[start_trim:total_length-end_trim]
        else:
            # Trim from start only
            return audio_segment[start_trim:]
    
    def save_recording(self):
        if not self.frames:
            messagebox.showwarning("Warning", "No recording to save!")
            return
        
        # Check if the recordings folder exists and is writable
        if not os.path.exists(self.recordings_folder):
            try:
                os.makedirs(self.recordings_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create recordings folder: {e}")
                return
        
        # Test if folder is writable
        if not os.access(self.recordings_folder, os.W_OK):
            messagebox.showerror("Error", f"Cannot write to folder: {self.recordings_folder}")
            return
        
        name = self.name_entry.get().strip()
        if not name:
            name = f"R {self.recording_counter}"
            self.recording_counter += 1
        elif not name.startswith("R "):
            name = "R " + name
        
        # Ensure valid filename
        name = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in name)
        
        # Save as temporary WAV file first
        temp_wav = io.BytesIO()
        
        try:
            # Create WAV in memory
            wf = wave.open(temp_wav, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            
            # Convert to MP3
            temp_wav.seek(0)
            audio_segment = AudioSegment.from_wav(temp_wav)
            
            # Apply trimming if option is checked
            if self.trim_var.get():
                audio_segment = self.trim_audio(audio_segment)
                
                # Build trim text for status
                start_trim = self.start_trim_var.get()
                end_trim = self.end_trim_var.get()
                trim_text = f" (trimmed {start_trim}s from start"
                if end_trim > 0:
                    trim_text += f", {end_trim}s from end"
                trim_text += ")"
            else:
                trim_text = ""
            
            # Save as MP3
            mp3_filename = os.path.join(self.recordings_folder, f"{name}.mp3")
            audio_segment.export(mp3_filename, format="mp3")
            
            # Update UI
            self.status_label.config(text=f"Saved as {name}.mp3{trim_text}")
            self.name_entry.delete(0, tk.END)
            self.save_button["state"] = "disabled"
            self.play_button["state"] = "disabled"
            self.frames = []
            self.timer_label.config(text="00:00")
            
            # Save the last recorded file path for playback
            self.last_saved_file = mp3_filename
            
            # Update recent recordings list
            self.update_recent_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save recording: {e}")
    
    def update_recent_list(self):
        self.recent_list.delete(0, tk.END)
        
        if not os.path.exists(self.recordings_folder):
            try:
                os.makedirs(self.recordings_folder)
            except Exception as e:
                self.recent_list.insert(tk.END, f"Error creating folder: {e}")
                return
        
        try:
            # Get the 5 most recent recordings
            files = sorted(
                [f for f in os.listdir(self.recordings_folder) if f.endswith('.mp3')],
                key=lambda x: os.path.getmtime(os.path.join(self.recordings_folder, x)),
                reverse=True
            )[:5]
            
            # Update the listbox
            if files:
                for file in files:
                    self.recent_list.insert(tk.END, file)
            else:
                self.recent_list.insert(tk.END, "No recordings found")
        except Exception as e:
            self.recent_list.insert(tk.END, f"Error reading folder: {e}")
    
    def play_recording(self):
        """Play the current recording or last saved file"""
        if self.is_playing:
            self.status_label.config(text="Already playing")
            return
            
        if not self.frames and not hasattr(self, 'last_saved_file'):
            messagebox.showwarning("Warning", "No recording to play!")
            return
            
        # Set flag to prevent multiple playbacks
        self.is_playing = True
        self.status_label.config(text="Playing...")
        
        # Disable buttons during playback
        self.play_button["state"] = "disabled"
        
        # Start playback in a separate thread
        threading.Thread(target=self._play_audio_thread, daemon=True).start()
    
    def _play_audio_thread(self):
        """Play audio in a separate thread"""
        try:
            # Update status to show playing
            self.root.after(0, lambda: self.status_label.config(text="Playing..."))
            
            if self.frames:  # Play current recording in memory
                # Create WAV in memory
                temp_wav = io.BytesIO()
                wf = wave.open(temp_wav, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))
                wf.close()
                
                # Play using pydub
                temp_wav.seek(0)
                audio_segment = AudioSegment.from_wav(temp_wav)
                
                # Apply trimming if option is checked
                if self.trim_var.get():
                    start_trim = self.start_trim_var.get()
                    end_trim = self.end_trim_var.get()
                    
                    # Update status with trim info
                    trim_info = f"Playing (trimmed {start_trim}s start"
                    if end_trim > 0:
                        trim_info += f", {end_trim}s end"
                    trim_info += ")"
                    self.root.after(0, lambda: self.status_label.config(text=trim_info))
                    
                    audio_segment = self.trim_audio(audio_segment)
                
                pydub_play(audio_segment)
                
            elif hasattr(self, 'last_saved_file'):  # Play last saved file
                if os.path.exists(self.last_saved_file):
                    audio_segment = AudioSegment.from_file(self.last_saved_file)
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"Playing: {os.path.basename(self.last_saved_file)}"
                    ))
                    pydub_play(audio_segment)
                else:
                    self.root.after(0, lambda: messagebox.showwarning("Warning", "File not found!"))
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to play: {e}"))
        
        finally:
            # Re-enable buttons after playback
            self.root.after(0, lambda: self.play_button.config(state="normal"))
            self.root.after(0, lambda: self.status_label.config(text="Ready"))
            self.is_playing = False
    
    def play_selected_recording(self, event):
        """Play a recording selected from the recent list"""
        selection = self.recent_list.curselection()
        if not selection:
            return
            
        filename = self.recent_list.get(selection[0])
        filepath = os.path.join(self.recordings_folder, filename)
        
        if not os.path.exists(filepath):
            messagebox.showwarning("Warning", "File not found!")
            return
            
        # Set as last saved file for playback
        self.last_saved_file = filepath
        
        # Play the file
        self.play_recording()
        
    def cleanup(self):
        if self.recording:
            self.recording = False
            self.timer_running = False
            
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
        self.audio.terminate()

if __name__ == "__main__":
    root = tk.Tk()
    app = QuickRecorderApp(root)
    
    # Handle window close
    root.protocol("WM_DELETE_WINDOW", lambda: [app.cleanup(), root.destroy()])
    
    root.mainloop()