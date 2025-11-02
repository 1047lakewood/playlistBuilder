import tkinter as tk
from tkinter import ttk, messagebox
import pygame
import os
import threading
import time
import logging
from font_config import DEFAULT_FONT, BOLD_FONT, DEFAULT_FONT_TUPLE
from audio_converter import AudioConverter
from models.playlist import Playlist

class PrelistenView(tk.Frame):
    def __init__(self, parent, track, on_close_callback):
        super().__init__(parent, bg="#f0f0f0")
        self.view_parent = parent # Store the ContainerView instance
        self.track = track
        self.track_path = track.path
        self.on_close_callback = on_close_callback
        self.playing = False
        self.current_position = 0
        self.track_length = track.duration
        
        # Initialize pygame mixer with high quality settings and larger buffer to prevent crackling
        if not pygame.mixer.get_init():
            # 44.1kHz sample rate, 16-bit signed audio, stereo, buffer size 4096 (larger buffer reduces crackling)
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        else:
            # If already initialized, quit and reinitialize with our settings
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        
        self.create_widgets()
        self.load_audio()
        
        # Bind Esc key to close the window
        self.bind_all("<Escape>", lambda event: self.close())
        
    def create_widgets(self):
        # Colors
        prelisten_bg = "#f0f0f0"
        control_bg = "#e0e0e0"
        
        # Top control bar with title and close button
        self.control_frame = tk.Frame(self, bg=control_bg)
        self.control_frame.pack(fill="x", padx=5, pady=5)
        
        # Close button (moved to left side)
        self.close_button = ttk.Button(self.control_frame, text="✕", width=3, command=self.close)
        self.close_button.pack(side="left", padx=5)
        
        # Track title label
        self.title_label = tk.Label(self.control_frame, text="Prelistening: " + os.path.basename(self.track_path), 
                                    bg=control_bg, anchor="w", font=DEFAULT_FONT)
        self.title_label.pack(side="left", padx=5)
        
        # Playback controls
        self.playback_frame = tk.Frame(self, bg=prelisten_bg)
        self.playback_frame.pack(fill="x", padx=10, pady=5)
        
        # Play/Pause button
        self.play_button = ttk.Button(self.playback_frame, text="▶", width=3, command=self.toggle_play)
        self.play_button.pack(side="left", padx=5)
        
        # Time display
        self.time_label = tk.Label(self.playback_frame, text="0:00 / 0:00", bg=prelisten_bg, font=DEFAULT_FONT)
        self.time_label.pack(side="left", padx=10)

        
        # Progress bar
        self.progress_frame = tk.Frame(self, bg=prelisten_bg)
        self.progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_bar = ttk.Scale(self.progress_frame, from_=0, to=100, orient="horizontal", 
                                      command=self.seek_position)
        self.progress_bar.pack(fill="x", expand=True)
        
        # Status message
        self.status_label = tk.Label(self, text="Loading audio...", bg=prelisten_bg, font=DEFAULT_FONT)
        self.status_label.pack(pady=5)
        
    def load_audio(self):
        """Load the audio file and prepare for playback"""
        try:
            # Check if the file format is supported by pygame
            if not AudioConverter.is_format_supported_by_pygame(self.track_path):
                self.status_label.config(text="Unsupported format. Offering conversion...")
                print(f"Unsupported format for prelisten: {self.track_path}")
                
                # Offer to convert the file
                converted_path = AudioConverter.offer_conversion_dialog(self.master, self.track_path, self.track)
                
                if converted_path:
                    # Update the track path if conversion was successful
                    # AudioConverter.offer_conversion_dialog already updated self.track.path
                    self.track_path = converted_path # Sync PrelistenView's local variable
                    print(f"Using converted file: {self.track_path} for track object: {self.track.path}")

                    # --- Add logic to update main playlist and API if necessary ---
                    controller = self.view_parent.controller # self.view_parent is ContainerView
                    current_playlist = controller.get_selected_tab_playlist()

                    # Ensure the track object is the one from the playlist for index finding
                    # This is important if self.track was a copy, though it seems to be the original.
                    # For safety, let's try to find the exact instance in the playlist.
                    track_in_playlist = None
                    original_track_index = -1
                    for i, t_obj in enumerate(current_playlist.tracks):
                        if t_obj is self.track: # Check object identity
                            track_in_playlist = t_obj
                            original_track_index = i
                            break
                    
                    if track_in_playlist and original_track_index != -1:
                        # 1. Update metadata for the new path (self.track's path was updated by offer_conversion_dialog)
                        controller.playlist_service.update_track_metadata([self.track])
                        
                        # 2. Check for intros (important after path/metadata change)
                        # Ensure check_for_intros_and_if_exists can handle a single track in a list
                        controller.controller_actions.check_for_intros_and_if_exists(playlist=current_playlist, tracks=[self.track])
                        
                        # 3. Update Remote Playlist if necessary
                        if current_playlist.type == Playlist.PlaylistType.API:
                            # remove_and_reinsert_track expects the track object and its original index
                            controller.controller_actions.remove_and_reinsert_track(self.track, original_track_index)
                            
                        # 4. Reload the rows in the tree view of the active tab
                        controller.controller_actions.reload_rows_in_selected_tab_without_intro_check()
                        
                        # 5. Mark profile as dirty
                        controller.mark_profile_dirty()
                        
                        print(f"Track '{self.track.title}' updated in main playlist after pre-listen conversion.")
                    else:
                        print(f"Warning: Track '{self.track.title}' (object ID: {id(self.track)}) not found by identity in current playlist after conversion, or index issue. Skipping main playlist updates.")
                        # Fallback: if identity check fails, try to find by old path if stored, but this is less reliable.
                        # This part is complex because the original path of self.track might not be easily available here
                        # if offer_conversion_dialog directly modified it without returning the old one.
                        # For now, relying on object identity is the primary approach.

                else:
                    # User cancelled conversion
                    print("Conversion cancelled or failed")
                    self.status_label.config(text="Conversion cancelled. Trying to play original file...")
            
            # Set volume to 100% for best quality
            pygame.mixer.music.set_volume(1.0)
            
            # Load the audio file
            pygame.mixer.music.load(self.track_path)
            
            self.track_length = self.track.duration
            
            # Update UI
            self.status_label.config(text="Ready to play")
            self.time_label.config(text=f"0:00 / {self.format_time(self.track_length)}")
            self.progress_bar.config(to=self.track_length)
            
            # Start the update thread
            self.update_thread = threading.Thread(target=self.update_position)
            self.update_thread.daemon = True
            self.update_thread.start()
            
            # Log success
            print(f"Successfully loaded audio: {self.track_path}")

            # Auto play
            self.toggle_play()
            
        except Exception as e:
            self.status_label.config(text=f"Error loading audio: {str(e)}")
            print(f"Error loading audio: {str(e)}")
            
            # If the error might be due to an unsupported format, offer conversion
            if "mixer" in str(e).lower() or "format" in str(e).lower() or "load" in str(e).lower():
                try:
                    self.status_label.config(text="Error playing file. Trying conversion...")
                    converted_path = AudioConverter.offer_conversion_dialog(self.master, self.track_path, self.track)
                    
                    if converted_path:
                        # Update the track path if conversion was successful
                        self.track_path = converted_path
                        print(f"Using converted file after error: {self.track_path}")
                        
                        # Try loading again
                        self.load_audio()
                except Exception as conv_error:
                    print(f"Error during conversion attempt: {str(conv_error)}")
                    self.status_label.config(text=f"Conversion failed: {str(conv_error)}")
    
    def toggle_play(self):
        """Toggle between play and pause"""
        if not self.playing:
            try:
                # Ensure the mixer is properly initialized before playing
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                
                # Set volume to full for best quality
                pygame.mixer.music.set_volume(1.0)
                
                # Start playback from current position or beginning
                if self.current_position > 0:
                    pygame.mixer.music.play(start=self.current_position)
                else:
                    pygame.mixer.music.play()
                    
                self.playing = True
                self.play_button.config(text="⏸")
                self.status_label.config(text="Playing")
                print(f"Started playback at position {self.format_time(self.current_position)}")
            except Exception as e:
                self.status_label.config(text=f"Error playing: {str(e)}")
                print(f"Error playing: {str(e)}")
        else:
            try:
                pygame.mixer.music.pause()
                self.playing = False
                self.play_button.config(text="▶")
                self.status_label.config(text="Paused")
                print(f"Paused playback at position {self.format_time(self.current_position)}")
            except Exception as e:
                self.status_label.config(text=f"Error pausing: {str(e)}")
                print(f"Error pausing: {str(e)}")
    
    def seek_position(self, value):
        """Seek to a specific position in the track"""
        try:
            position = float(value)
            self.current_position = position
            
            # If currently playing, restart at new position
            if self.playing:
                pygame.mixer.music.stop()
                pygame.mixer.music.play(start=position)
            
            self.time_label.config(text=f"{self.format_time(position)} / {self.format_time(self.track_length)}")
        except Exception as e:
            self.status_label.config(text=f"Error seeking: {str(e)}")

    
    def update_position(self):
        #FIX
        return
        """Update the current position and progress bar"""
        last_update_time = time.time()
        while True:
            try:
                if self.playing and pygame.mixer.music.get_busy():
                    # Calculate elapsed time since last update for smoother position tracking
                    current_time = time.time()
                    elapsed = current_time - last_update_time
                    last_update_time = current_time
                    
                    # Update position based on actual elapsed time (smoother than fixed increments)
                    self.current_position += elapsed
                    
                    if self.current_position > self.track_length:
                        self.current_position = 0
                        self.playing = False
                        self.play_button.config(text="▶")
                    
                    # Update UI
                    self.progress_bar.set(self.current_position)
                    self.time_label.config(text=f"{self.format_time(self.current_position)} / {self.format_time(self.track_length)}")
            except Exception as e:
                print(f"Error updating position: {str(e)}")
            
            # Use a longer sleep time to reduce CPU usage and prevent audio crackling
            time.sleep(0.2)
    
    def format_time(self, seconds):
        """Format seconds to mm:ss"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    def close(self):
        """Stop playback and close the view"""
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.playing = False
            
            # Call the callback to notify parent
            if self.on_close_callback:
                self.on_close_callback()
        except Exception as e:
            print(f"Error closing prelisten view: {str(e)}")
    
    def refresh_theme_colors(self):
        """Refresh colors - using hardcoded defaults."""
        prelisten_bg = "#f0f0f0"
        control_bg = "#e0e0e0"
        
        # Update widget backgrounds
        self.config(bg=prelisten_bg)
        self.control_frame.config(bg=control_bg)
        self.title_label.config(bg=control_bg)
        self.playback_frame.config(bg=prelisten_bg)
        self.time_label.config(bg=prelisten_bg)
        self.progress_frame.config(bg=prelisten_bg)
        self.status_label.config(bg=prelisten_bg)
