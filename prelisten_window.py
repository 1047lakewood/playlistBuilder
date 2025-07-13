import tkinter as tk
from tkinter import ttk, Scale, scrolledtext
import pygame
import os
import threading
import time
import logging

# Configure logging once for the module
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(threadName)s: %(message)s')

# Dummy classes/variables for self-contained example
# from font_config import DEFAULT_FONT, BOLD_FONT, DEFAULT_FONT_TUPLE
# from audio_converter import AudioConverter
class DummyTrack:
    def __init__(self, path, artist, title, duration=None):
        self.path = path
        self.artist = artist
        self.title = title
        self.duration = duration

class PrelistenWindow(tk.Frame):
    def __init__(self, parent, track, on_close=None):
        # Custom handler reference placeholder
        self._text_log_handler = None
        super().__init__(parent, borderwidth=2, relief="groove")
        self.parent = parent
        self.track = track
        self.on_close = on_close

        # --- State Variables ---
        self.is_playing = False
        self.is_paused = False
        # This will store the position where playback started or was last sought.
        self.playback_start_offset = 0.0
        # Timestamp of last verbose progress log
        self._last_log_time = 0.0
        self.duration = 0
        
        # --- Threading Control ---
        self.update_thread = None
        self.stop_thread_flag = threading.Event()

        # --- UI Control ---
        # Flag to prevent seek function from being called when we update the slider from code
        self.internal_update = False
        
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        self.create_widgets()
        self.load_audio()
        
        self.bind_all("<Escape>", lambda event: self.close())
        # Start the background thread for updates
        self.start_update_thread()
        
    def create_widgets(self):
        # This method is fine, no changes needed.
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=5, pady=5)
        self.close_button = ttk.Button(top_frame, text="X", width=3, command=self.close)
        self.close_button.pack(side="left", padx=(0, 5))
        track_info = f"{self.track.artist} - {self.track.title}"
        self.track_label = tk.Label(top_frame, text=track_info, anchor="w")
        self.track_label.pack(side="left", fill="x", expand=True)
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill="x", padx=5, pady=5)
        self.play_button = ttk.Button(controls_frame, text="Play", width=8, command=self.toggle_play)
        self.play_button.pack(side="left", padx=5)
        progress_frame = tk.Frame(self)
        progress_frame.pack(fill="x", padx=5, pady=5)
        self.current_time_label = tk.Label(progress_frame, text="0:00")
        self.current_time_label.pack(side="left")
        self.duration_label = tk.Label(progress_frame, text="0:00")
        self.duration_label.pack(side="right")
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_slider = Scale(progress_frame, from_=0, to=100, orient="horizontal", 
                                    variable=self.progress_var, showvalue=0, 
                                    command=self.seek)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=5)

        # --- Log Console ---
        log_frame = tk.Frame(self)
        log_frame.pack(fill="both", padx=5, pady=(0,5), expand=True)
        self.log_widget = scrolledtext.ScrolledText(log_frame, height=6, state="disabled", wrap="word")
        self.log_widget.pack(fill="both", expand=True)

        # Attach logging handler to display logs in this widget
        self._attach_text_logger()


    def load_audio(self):
        try:
            if not os.path.exists(self.track.path):
                raise FileNotFoundError(f"File not found: {self.track.path}")
                
            pygame.mixer.music.load(self.track.path)
            
            # Use pygame.mixer.Sound to reliably get duration, as track.duration might be missing
            sound = pygame.mixer.Sound(self.track.path)
            self.duration = sound.get_length()
            
            self.progress_slider.config(to=self.duration)
            self.update_duration_label()
            logging.debug(f"Loaded audio: {self.track.path}, Duration: {self.duration:.2f}s")
            
        except Exception as e:
            logging.error(f"Error loading audio: {e}")
            self.track_label.config(text=f"Error: {e}")
            self.play_button.config(state="disabled")
            self.progress_slider.config(state="disabled")

    def toggle_play(self):
        if self.is_playing:
            self.pause()
        elif self.is_paused:
            self.unpause()
        else:
            self.play()

    def play(self):
        if self.duration == 0: return # Don't play if nothing is loaded
        logging.debug("Executing Play")
        try:
            pygame.mixer.music.play(start=self.playback_start_offset)
            self.is_playing = True
            self.is_paused = False
            self.play_button.config(text="Pause")
            logging.debug(f"play() invoked | busy={pygame.mixer.music.get_busy()} | get_pos={pygame.mixer.music.get_pos()} ms | start_offset={self.playback_start_offset}s | duration={self.duration:.2f}s")
        except Exception as e:
            logging.error(f"Error on play: {e}")

    def pause(self):
        logging.debug("Executing Pause")
        pygame.mixer.music.pause()
        self.is_playing = False
        self.is_paused = True
        self.play_button.config(text="Play")

    def unpause(self):
        logging.debug("Executing Unpause")
        pygame.mixer.music.unpause()
        self.is_playing = True
        self.is_paused = False
        self.play_button.config(text="Pause")

    def seek(self, value):
        if self.internal_update:
            return

        new_position = float(value)
        logging.debug(f"Seeking to: {new_position:.2f}s")
        
        # Store the new position as the starting offset for our calculation
        self.playback_start_offset = new_position
        self.progress_var.set(new_position) # Manually set slider to new position

        try:
            # Stop the music and restart it from the new position
            pygame.mixer.music.stop()
            pygame.mixer.music.play(start=self.playback_start_offset)
            
            self.is_playing = True
            self.is_paused = False
            self.play_button.config(text="Pause")
        except Exception as e:
            logging.error(f"Error on seek: {e}")

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def update_duration_label(self):
        self.duration_label.config(text=self.format_time(self.duration))

    def _update_ui(self, current_position: float, at_end: bool = False):
        """Safely update UI elements from the Tkinter main thread."""
        self.internal_update = True
        self.progress_var.set(current_position)
        self.current_time_label.config(text=self.format_time(current_position))
        if at_end:
            self.play_button.config(text="Play")
        self.internal_update = False
        logging.debug(f"UI updated | position={current_position:.3f}s | at_end={at_end}")
    
    def _attach_text_logger(self):
        """Create a logging handler that writes to the text widget."""
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                # Simple formatter without time to keep log concise in UI
                self.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

            def emit(self, record):
                msg = self.format(record) + "\n"
                # Ensure thread-safe insert
                self.text_widget.after(0, self._append, msg)

            def _append(self, msg):
                # Append and auto-scroll
                self.text_widget.configure(state="normal")
                self.text_widget.insert("end", msg)
                self.text_widget.yview_moveto(1.0)
                self.text_widget.configure(state="disabled")
        # Instantiate and add to root logger
        self._text_log_handler = TextHandler(self.log_widget)
        logging.getLogger().addHandler(self._text_log_handler)

    def start_update_thread(self):
        self.stop_thread_flag.clear()
        self.update_thread = threading.Thread(target=self.update_progress, daemon=True)
        self.update_thread.start()

    def update_progress(self):
        """BACKGROUND THREAD: Monitors playback and schedules UI updates."""
        logging.debug("Background update thread started.")
        while not self.stop_thread_flag.is_set():
            if self.is_playing:
                # pygame returns elapsed time in ms since play() was called
                elapsed_ms = pygame.mixer.music.get_pos()
                logging.debug(f"pygame.get_pos() -> {elapsed_ms} ms")

                if elapsed_ms != -1:
                    current_position = self.playback_start_offset + (elapsed_ms / 1000.0)
                    logging.debug(f"Computed current_position={current_position:.3f}s")
                    # Throttled detailed progress log every 1s
                    if time.time() - self._last_log_time >= 1.0:
                        self._last_log_time = time.time()
                        logging.debug(f"update_progress | pos={current_position:.3f}s | busy={pygame.mixer.music.get_busy()} | elapsed_ms={elapsed_ms}")
                    # Schedule UI updates on the Tkinter main loop
                    self.after(0, self._update_ui, current_position, False)

                # Detect end of track using get_busy()
                if not pygame.mixer.music.get_busy():
                    logging.debug("Detected end of playback.")
                    self.is_playing = False
                    self.is_paused = False
                    self.playback_start_offset = 0.0
                    self.after(0, self._update_ui, self.duration, True)

            time.sleep(0.1)  # Update 10 times per second
        logging.debug("Background update thread terminating.")

    def close(self):
        logging.debug("Closing window...")
        # Signal the thread to stop
        self.stop_thread_flag.set()
        
        # Stop the music
        pygame.mixer.music.stop()
        
        if self.on_close:
            self.on_close()
        
        # Detach text logging handler if present
        if self._text_log_handler:
            logging.getLogger().removeHandler(self._text_log_handler)
            self._text_log_handler.close()
        self.destroy()

# Example usage (for testing)
if __name__ == '__main__':
    # --- Create a dummy audio file for testing ---
    # You MUST have 'pygame' and 'pydub' installed: pip install pygame pydub
    try:
        from pydub import AudioSegment
        from pydub.generators import Sine
        
        # Generate a 30-second sine wave and save as "test_audio.ogg"
        # OGG is highly recommended for pygame as it's more reliable for seeking.
        if not os.path.exists("test_audio.ogg"):
            print("Creating dummy audio file 'test_audio.ogg'...")
            sine_wave = Sine(440).to_audio_segment(duration=30000) # 30 seconds
            sine_wave.export("test_audio.ogg", format="ogg")
            print("Dummy file created.")
        
        AUDIO_FILE = "test_audio.ogg"

    except ImportError:
        print("\n--- Pydub not found. Please create a test audio file manually. ---")
        print("--- Name it 'test_audio.mp3' or 'test_audio.ogg' and place it in this directory. ---")
        AUDIO_FILE = "test_audio.mp3" # Fallback to mp3 if pydub isn't there


    if os.path.exists(AUDIO_FILE):
        root = tk.Tk()
        root.title("Prelisten Test")
        root.geometry("400x150")

        # Create a dummy track object
        track_obj = DummyTrack(path=AUDIO_FILE, artist="Test Artist", title="Test Song")

        # Create and display the PrelistenWindow
        prelisten_frame = PrelistenWindow(root, track_obj, on_close=root.quit)
        prelisten_frame.pack(padx=10, pady=10, fill="x", expand=True)

        root.mainloop()
    else:
        print(f"ERROR: Test audio file '{AUDIO_FILE}' not found. Cannot run example.")