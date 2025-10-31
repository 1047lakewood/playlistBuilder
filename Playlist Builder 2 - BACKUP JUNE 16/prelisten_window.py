import tkinter as tk
from tkinter import ttk, Scale, messagebox
import pygame
import os
import threading
import time
import logging
from font_config import DEFAULT_FONT, BOLD_FONT, DEFAULT_FONT_TUPLE
from audio_converter import AudioConverter

class PrelistenWindow(tk.Frame):
    def __init__(self, parent, track, on_close=None):
        super().__init__(parent, borderwidth=2, relief="groove")
        self.parent = parent
        self.track = track
        self.on_close = on_close
        self.is_playing = False
        self.current_position = 0
        self.duration = 0
        self.update_thread = None
        self.stop_thread = False
        
        # Initialize pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        self.create_widgets()
        self.load_audio()
        
        # Bind Esc key to close the window
        self.bind_all("<Escape>", lambda event: self.close())
        
    def create_widgets(self):
        # Top frame for title and close button
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=5, pady=5)
        
        # Close button (moved to left side)
        self.close_button = ttk.Button(top_frame, text="X", width=3, command=self.close)
        self.close_button.pack(side="left", padx=(0, 5))
        
        # Track info label
        track_info = f"{self.track.artist} - {self.track.title}"
        self.track_label = tk.Label(top_frame, text=track_info, anchor="w", font=BOLD_FONT)
        self.track_label.pack(side="left", fill="x", expand=True)
        
        # Controls frame
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill="x", padx=5, pady=5)
        
        # Play/Pause button
        self.play_button = ttk.Button(controls_frame, text="Play", width=8, command=self.toggle_play)
        self.play_button.pack(side="left", padx=5)
        
        # Progress bar frame
        progress_frame = tk.Frame(self)
        progress_frame.pack(fill="x", padx=5, pady=5)
        
        # Time labels
        self.current_time_label = tk.Label(progress_frame, text="0:00", font=DEFAULT_FONT)
        self.current_time_label.pack(side="left")
        
        self.duration_label = tk.Label(progress_frame, text="0:00", font=DEFAULT_FONT)
        self.duration_label.pack(side="right")
        
        # Progress slider
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_slider = Scale(progress_frame, from_=0, to=100, orient="horizontal", 
                                    variable=self.progress_var, showvalue=0, 
                                    command=self.seek)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=5)
        
    def load_audio(self):
        try:
            if not os.path.exists(self.track.path):
                print(f"File not found: {self.track.path}")
                self.track_label.config(text=f"File not found: {os.path.basename(self.track.path)}")
                return
                
            # Check if the file format is supported by pygame
            if not AudioConverter.is_format_supported_by_pygame(self.track.path):
                print(f"Unsupported format for prelisten: {self.track.path}")
                self.track_label.config(text=f"Unsupported format: {os.path.basename(self.track.path)}")
                
                # Offer to convert the file
                converted_path = AudioConverter.offer_conversion_dialog(self.parent, self.track.path, self.track)
                
                if converted_path:
                    # Update the track path if conversion was successful
                    self.track.path = converted_path
                    print(f"Using converted file: {self.track.path}")
                else:
                    # User cancelled conversion
                    print("Conversion cancelled or failed")
                    self.track_label.config(text=f"Conversion cancelled: {os.path.basename(self.track.path)}")
            
            # Try to load the audio file
            pygame.mixer.music.load(self.track.path)
            
            # Get duration if available from track, otherwise estimate
            if self.track.duration:
                self.duration = self.track.duration
            else:
                # Try to get duration from audio file
                sound = pygame.mixer.Sound(self.track.path)
                self.duration = sound.get_length()
            
            self.progress_slider.config(to=self.duration)
            self.update_duration_label()
            print(f"Loaded audio: {self.track.path}")
            
        except Exception as e:
            print(f"Error loading audio: {e}")
            self.track_label.config(text=f"Error loading audio: {str(e)[:50]}")
            
            # If the error might be due to an unsupported format, offer conversion
            if "mixer" in str(e).lower() or "format" in str(e).lower() or "load" in str(e).lower():
                try:
                    print("Error playing file. Trying conversion...")
                    self.track_label.config(text="Error playing file. Trying conversion...")
                    
                    converted_path = AudioConverter.offer_conversion_dialog(self.parent, self.track.path, self.track)
                    
                    if converted_path:
                        # Update the track path if conversion was successful
                        self.track.path = converted_path
                        print(f"Using converted file after error: {self.track.path}")
                        
                        # Try loading again
                        self.load_audio()
                except Exception as conv_error:
                    print(f"Error during conversion attempt: {str(conv_error)}")
                    self.track_label.config(text=f"Conversion failed: {str(conv_error)[:50]}")
    
    def toggle_play(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()
    
    def play(self):
        try:
            pygame.mixer.music.play(start=self.current_position)
            self.is_playing = True
            self.play_button.config(text="Pause")
            
            # Start update thread if not already running
            if not self.update_thread or not self.update_thread.is_alive():
                self.stop_thread = False
                self.update_thread = threading.Thread(target=self.update_progress)
                self.update_thread.daemon = True
                self.update_thread.start()
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def pause(self):
        try:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_button.config(text="Play")
            self.current_position = self.progress_var.get()
        except Exception as e:
            print(f"Error pausing audio: {e}")
    
    def seek(self, value):
        try:
            position = float(value)
            self.current_position = position
            self.update_current_time_label()
            
            if self.is_playing:
                pygame.mixer.music.stop()
                pygame.mixer.music.play(start=position)
        except Exception as e:
            print(f"Error seeking: {e}")
  
    def update_progress(self):
        try:
            while self.is_playing and not self.stop_thread:
                if not pygame.mixer.music.get_busy():
                    # Music has finished playing
                    self.is_playing = False
                    self.play_button.config(text="Play")
                    self.progress_var.set(0)
                    self.current_position = 0
                    self.update_current_time_label()
                    break
                
                # Update current position
                if self.is_playing:
                    self.current_position = pygame.mixer.music.get_pos() / 1000
                    if self.current_position >= 0:
                        self.progress_var.set(self.current_position)
                        self.update_current_time_label()
                
                time.sleep(0.1)
        except Exception as e:
            print(f"Error in update thread: {e}")
    
    def update_current_time_label(self):
        minutes = int(self.current_position // 60)
        seconds = int(self.current_position % 60)
        self.current_time_label.config(text=f"{minutes}:{seconds:02d}")
    
    def update_duration_label(self):
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        self.duration_label.config(text=f"{minutes}:{seconds:02d}")
    
    def close(self):
        try:
            # Stop playback and cleanup
            self.stop_thread = True
            if self.is_playing:
                pygame.mixer.music.stop()
            self.is_playing = False
            
            # Call the on_close callback if provided
            if self.on_close:
                self.on_close()
            
            # Remove the widget
            self.destroy()
        except Exception as e:
            print(f"Error closing prelisten window: {e}")
