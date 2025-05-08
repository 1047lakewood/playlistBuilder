import time
import pygame
from playlist_manager_view import PlaylistManagerView
from playlist_manager_model import PlaylistManagerModel
from playlist_tab import PlaylistTab
from utils import DEFAULT_COLUMNS
import logging
import os
from tkinter import filedialog, messagebox
logger = logging.getLogger(__name__)

# --- Controller ---
class PlaylistManagerController:
    def __init__(self, master_tk_root):
        self.model = PlaylistManagerModel()
        self.view = PlaylistManagerView(master_tk_root, self)
        
        self.playback_update_job = None
        self._scrubbing = False # Flag for progress bar scrubbing

        # For tab drag and drop
        self._dragged_tab_index = None
        self._dragged_tab_id = None

        self._post_ui_init_setup()

    def _post_ui_init_setup(self):
        # Apply initial volume from settings
        self.view.volume_var.set(self.model.current_settings.get('volume', 0.8))
        if pygame.mixer.get_init(): # If pygame is already init by now
             pygame.mixer.music.set_volume(self.view.volume_var.get())


        # Restore open tabs or load last profile
        if self.model.current_settings.get("last_profile"):
            self.load_profile(self.model.current_settings["last_profile"], startup=True)
        else:
            self.restore_open_tabs_from_model()
        
        # Ensure at least one tab exists, even after profile load or restore
        if not self.view.notebook.tabs():
            self.add_new_tab_command(title="Untitled Playlist") # Use command to ensure proper handling

        self._auto_init_audio()
        self.view.update_dynamic_profile_menu(self.model.current_settings.get("profiles", {}))

        # Select the first tab if any exist
        if self.view.notebook.tabs():
            self.view.notebook.select(self.view.notebook.tabs()[0])
            self.on_tab_change() # Manually trigger tab change logic for the first tab

    def add_new_tab_command(self, title="Untitled Playlist", filepath=None):
        """Command to add a new tab, typically from menu or shortcut."""
        # Apply current global column settings to the new tab
        new_tab = PlaylistTab(
            self.view.notebook, 
            self,  # Pass controller to PlaylistTab
            filepath=filepath,
            initial_columns=self.model.current_settings['columns']
        )
        display_title = title
        if filepath:
            display_title = os.path.splitext(os.path.basename(filepath))[0]
            if new_tab.tab_display_name != display_title: # if PlaylistTab set a different one based on existing file
                new_tab.tab_display_name = display_title


        self.view.add_tab_to_notebook(new_tab, display_title) # View handles adding to notebook
        new_tab.update_tab_title() # Set initial '*' if needed after being added
        self.view.set_status(f"Created new playlist: {display_title}")
        
        # Apply persistent column widths
        widths = self.model.get_column_widths()
        for col, width in widths.items():
            try:
                new_tab.tree.column(col, width=width)
            except Exception: # Column might not be in this tab's current display_columns
                pass
        return new_tab


    def open_playlists(self):
        filepaths = filedialog.askopenfilenames(
            parent=self.view,
            title="Open Playlist(s)",
            filetypes=[("M3U Playlists", "*.m3u *.m3u8"), ("All Files", "*.*")]
        )
        if not filepaths:
            return

        loaded_count = 0
        for path in filepaths:
            try:
                is_open = False
                for tab_widget in self.view.get_all_tab_widgets():
                    if tab_widget.filepath == path:
                        self.view.notebook.select(tab_widget)
                        self.view.set_status(f"Playlist '{os.path.basename(path)}' is already open.")
                        is_open = True
                        break
                if is_open:
                    continue

                current_tab = self.view.get_current_tab_widget()
                # If current tab is empty and unsaved, load into it
                if current_tab and not current_tab._track_data and not current_tab.filepath and not current_tab.is_dirty:
                    success = current_tab.load_playlist_from_file(path) # This updates filepath and name
                    if success:
                        current_tab.filepath = path # Ensure it's set
                        current_tab.tab_display_name = os.path.splitext(os.path.basename(path))[0]
                        current_tab.update_tab_title()
                        loaded_count += 1
                    else: # load_playlist_from_file should show its own error
                        current_tab.is_dirty = False # Reset dirty state on fail
                        current_tab.update_tab_title()
                    continue
                
                # Otherwise, add new tab and load
                tab_title = os.path.splitext(os.path.basename(path))[0]
                new_tab = self.add_new_tab_command(title=tab_title, filepath=path) # filepath passed here
                # new_tab.load_playlist_from_file is called in PlaylistTab constructor if filepath is given
                if new_tab and new_tab.filepath == path : # Check if loading was implicitly successful by filepath being set
                     if new_tab._track_data: # Check if tracks were loaded
                        loaded_count += 1
                     else: # Filepath set, but no tracks - might be empty or error during its load
                        # Check if the PlaylistTab itself logged an error or showed a message
                        logger.warning(f"Playlist {path} loaded into new tab but might be empty or had internal load issues.")
                        # If new_tab.load_playlist_from_file returned False but didn't raise, it's tricky.
                        # For now, assume constructor load handles errors/messages.
                else:
                    # This case might mean new_tab creation failed or path wasn't set right
                    messagebox.showerror("Load Error", f"Failed to create tab or load playlist:\n{path}", parent=self.view)


            except Exception as e:
                logger.error(f"Error opening playlist {os.path.basename(path)}: {e}", exc_info=True)
                messagebox.showerror("Error Opening Playlist", f"Could not open {os.path.basename(path)}:\n{e}", parent=self.view)
        
        if loaded_count > 0:
            self.view.set_status(f"Opened {loaded_count} playlist(s).")
        elif filepaths: # Attempted to open but none succeeded fully
            self.view.set_status(f"Finished attempting to open {len(filepaths)} playlist(s). Some may have failed.")


    def save_current_playlist(self, save_as=False):
        current_tab = self.view.get_current_tab_widget()
        if not current_tab:
            messagebox.showwarning("No Playlist", "No playlist tab is currently active.", parent=self.view)
            return
        current_tab.save_playlist(force_save_as=save_as)

    def _on_ctrl_s_global(self, event=None): # Bound in View to master
        self.save_current_playlist()
        return "break" # Prevent further processing of the event

    def close_current_tab(self):
        current_tab = self.view.get_current_tab_widget()
        if not current_tab:
            return False # Indicate no tab to close or action taken

        if current_tab.is_dirty:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                f"Playlist '{current_tab.get_display_name()}' has unsaved changes.\nDo you want to save before closing?",
                parent=self.view
            )
            if response is None: # Cancel
                return False 
            elif response is True: # Yes (Save)
                saved_successfully = current_tab.save_playlist()
                if not saved_successfully:
                    return False # Saving was cancelled or failed

        # If response was False (No) or save was successful, proceed to close
        tab_id_for_notebook = self.view.notebook.select() # Get the Tk path of the tab
        self.view.remove_tab_from_notebook(tab_id_for_notebook)
        self.view.set_status(f"Closed tab: {current_tab.get_display_name()}")

        if not self.view.notebook.tabs(): # If last tab was closed
            self.reset_prelisten_ui_if_needed(force_reset=True) # Force reset UI
            self.view.set_status("Ready. No playlists open.")
        # on_tab_change will be called automatically by notebook if tabs remain
        return True # Indicate successful close

    def quit_app(self):
        tabs_to_save_names = []
        dirty_tab_widgets = []

        for tab_widget in self.view.get_all_tab_widgets():
            if tab_widget.is_dirty:
                tabs_to_save_names.append(tab_widget.get_display_name())
                dirty_tab_widgets.append(tab_widget)
        
        if tabs_to_save_names:
            save_all_prompt = messagebox.askyesnocancel(
                "Unsaved Playlists",
                "There are unsaved playlists:\n- " + "\n- ".join(tabs_to_save_names) +
                "\n\nDo you want to save all changes before exiting?",
                parent=self.view
            )
            if save_all_prompt is None: # User chose Cancel
                return 
            if save_all_prompt is True: # User chose Yes (save all)
                for tab_to_save in dirty_tab_widgets:
                    self.view.notebook.select(tab_to_save) # Make it current for saving logic
                    if not tab_to_save.save_playlist():
                        # Save was cancelled or failed for this tab
                        if not messagebox.askyesno(
                            "Save Failed", 
                            f"Could not save '{tab_to_save.get_display_name()}'.\nExit anyway?",
                            parent=self.view):
                            return # User chose not to exit
        
        # All saves handled (or skipped), proceed with quit
        if self.model.pygame_initialized:
            self.stop_playback()
            try:
                pygame.mixer.quit()
                logger.info("Pygame mixer quit successfully.")
            except Exception as e:
                logger.error(f"Error during pygame.mixer.quit(): {e}")
            self.model.pygame_initialized = False


        self._prepare_and_save_settings()
        self.view.master.destroy()

    def _prepare_and_save_settings(self):
        # Update open_tabs in model from current view state
        open_tab_paths = []
        if self.view.notebook:
            for tab_id in self.view.notebook.tabs():
                try:
                    widget = self.view.nametowidget(tab_id)
                    if isinstance(widget, PlaylistTab):
                        open_tab_paths.append(widget.filepath if widget.filepath else None)
                except tk.TclError: # Tab might be in process of being destroyed
                    continue
        self.model.current_settings['open_tabs'] = open_tab_paths
        
        # Column widths and volume are already updated in the model by their respective handlers
        # self.model.current_settings['column_widths'] = self.model.get_column_widths()
        # self.model.current_settings['volume'] = self.view.volume_var.get()

        self.model.save_all_settings()

    def copy_selected(self):
        current_tab = self.view.get_current_tab_widget()
        if current_tab:
            selected_data = current_tab.get_selected_track_data()
            if selected_data:
                self.model.clipboard = selected_data
                self.view.set_status(f"Copied {len(self.model.clipboard)} track(s) to clipboard.")
            else:
                self.view.set_status("Select tracks to copy first.")

    def cut_selected(self):
        current_tab = self.view.get_current_tab_widget()
        if not current_tab: return
        
        selected_tracks_data = current_tab.get_selected_track_data()
        if not selected_tracks_data:
            self.view.set_status("Select tracks to cut first.")
            return

        self.model.clipboard = [track.copy() for track in selected_tracks_data] # Store copies
        current_tab.remove_selected_tracks() # This will set dirty flag and refresh
        self.view.set_status(f"Cut {len(self.model.clipboard)} track(s).")


    def paste_tracks(self):
        current_tab = self.view.get_current_tab_widget()
        if not current_tab:
            messagebox.showwarning("Paste Error", "No active playlist tab to paste into.", parent=self.view)
            return
        if not self.model.clipboard:
            messagebox.showwarning("Paste Error", "Clipboard is empty.", parent=self.view)
            return

        # Get selected item's index to paste after, or end of list
        insert_at_index = None
        selected_iids = current_tab.tree.selection()
        if selected_iids:
            last_selected_iid = selected_iids[-1] # Get the last selected item
            insert_at_index = current_tab.tree.index(last_selected_iid) + 1
        
        current_tab.add_tracks([track.copy() for track in self.model.clipboard], at_index=insert_at_index) # Pass copies
        self.view.set_status(f"Pasted {len(self.model.clipboard)} track(s) into {current_tab.get_display_name()}.")

    def remove_selected_from_current(self):
        current_tab = self.view.get_current_tab_widget()
        if current_tab:
            current_tab.remove_selected_tracks() # Tab handles its own removal logic + status update

    def refresh_current_tab_view(self):
        current_tab = self.view.get_current_tab_widget()
        if current_tab:
            current_tab.refresh_display()
            self.view.set_status(f"Refreshed view for {current_tab.get_display_name()}")

    def customize_columns(self):
        dialog = ColumnChooserDialog(
            self.view, 
            AVAILABLE_COLUMNS, 
            self.model.current_settings['columns']
        )
        if dialog.result is not None: # Check for actual result (not cancel)
            self.model.current_settings['columns'] = dialog.result
            self.view.update_column_settings_in_all_tabs(dialog.result)
            self.model.save_all_settings() # Persist column choice
            self.view.set_status("Column view updated.")
            # Apply new widths from model, as some columns might now be shown/hidden
            self.view.update_column_widths_in_all_tabs(self.model.get_column_widths())


    def on_column_widths_changed(self, new_widths):
        """Callback from PlaylistTab when its column widths are manually resized by user."""
        self.model.set_column_widths(new_widths)
        self.model.save_all_settings() # Persist immediately
        # Propagate to other tabs to keep them consistent
        self.view.update_column_widths_in_all_tabs(new_widths)

    def on_tab_change(self, event=None):
        # Stop playback when switching tabs if something is playing
        if self.model.currently_playing_path:
             self.stop_playback()

        current_tab = self.view.get_current_tab_widget()
        if current_tab:
            self.view.set_status(f"Active Playlist: {current_tab.get_display_name()}")
            # Update prelisten label if a track is selected in the new tab
            selected_iid = current_tab.get_selected_item_id()
            if selected_iid:
                track_data = current_tab.get_track_data_by_iid(selected_iid)
                if track_data:
                    self.update_prelisten_info_from_tab(track_data) # This updates view
                else: # Should not happen
                    self.reset_prelisten_ui_if_needed(force_reset=True)
            else: # No track selected in the new tab
                 self.reset_prelisten_ui_if_needed(force_reset=True)
        else: # No tab selected (e.g., all tabs closed)
             self.reset_prelisten_ui_if_needed(force_reset=True)
             self.view.set_status("No playlist selected.")
             
    def update_prelisten_info_from_tab(self, track_data):
        """Called by PlaylistTab when selection changes."""
        # Update model's idea of current track duration for potential playback
        if track_data:
            self.model.current_track_duration = track_data.get('duration', 0)
        
        # Update the prelisten UI display, but only if the selected track isn't already playing
        # If it IS playing, the playback progress update will handle the display.
        is_currently_playing_this_track = self.model.currently_playing_path == track_data.get('path')
        self.view.update_prelisten_display(track_data, is_playing_this_track=is_currently_playing_this_track)

    def reset_prelisten_ui_if_needed(self, force_reset=False):
        """
        Resets the prelisten UI elements if no track is playing,
        or if force_reset is True.
        """
        if force_reset or not self.model.currently_playing_path:
            self.view.update_prelisten_display(None) # Clears labels, progress
            self.view.update_play_pause_button(False, False) # Set to "Play"
            # self.view.hide_prelisten_player_frame() # Decide if player should auto-hide
            self.model.current_track_duration = 0


    def _auto_init_audio(self):
        # Based on original logic, but interacts with model and view
        self.model.pygame_initialized = False
        max_attempts = 3 # Reduced for faster startup if problematic
        delay_ms = 300

        def attempt_init(attempt_num):
            if attempt_num > max_attempts:
                logger.error("Audio could not be initialized after retries. Pre-listening disabled.")
                self.view.set_status("Audio Error: Mixer not initialized. Pre-listening disabled.")
                self.model.pygame_initialized = False
                return
            
            try: # Try to ensure clean state
                if pygame.mixer.get_init(): pygame.mixer.quit()
            except Exception: pass

            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self.model.pygame_initialized = True
                pygame.mixer.music.set_volume(self.view.volume_var.get()) # Set initial volume
                self.view.set_status("Audio initialized. Pre-listening enabled.")
                logger.info(f"Pygame mixer initialized (attempt {attempt_num}).")
            except Exception as e:
                self.model.pygame_initialized = False
                logger.warning(f"Audio init attempt {attempt_num} failed: {e}")
                self.view.set_status(f"Audio not available (attempt {attempt_num}). Retrying...")
                # Use view's master for 'after'
                self.view.master.after(delay_ms, lambda: attempt_init(attempt_num + 1))

        attempt_init(1)

    def play_selected_from_current_tab(self):
        current_tab = self.view.get_current_tab_widget()
        if not current_tab: return

        iid = current_tab.get_selected_item_id()
        if not iid:
            messagebox.showinfo("Play Track", "Select a track in the list to play.", parent=self.view)
            return

        track_data = current_tab.get_track_data_by_iid(iid)
        self.start_playback(track_data) # start_playback handles checks

    def toggle_play_pause(self):
        if not self.model.pygame_initialized:
            messagebox.showwarning("Audio Error", "Audio system not initialized. Cannot play.", parent=self.view)
            return

        if self.model.currently_playing_path: # If something is loaded/playing/paused
            if self.model.is_paused:
                try:
                    pygame.mixer.music.unpause()
                    self.model.is_paused = False
                    self.view.set_status(f"Resumed: {os.path.basename(self.model.currently_playing_path)}")
                    # Recalculate start time based on paused position
                    self.model.playback_start_time = time.time() - self.model.paused_position 
                    self._start_playback_progress_updater()
                except Exception as e:
                    messagebox.showerror("Playback Error", f"Could not resume playback: {e}", parent=self.view)
                    self.stop_playback() # Reset state on error
            else: # Is playing, so pause it
                try:
                    pygame.mixer.music.pause()
                    self.model.is_paused = True
                    # Store current elapsed time
                    self.model.paused_position = time.time() - self.model.playback_start_time
                    self.view.set_status(f"Paused: {os.path.basename(self.model.currently_playing_path)}")
                    self._stop_playback_progress_updater()
                except Exception as e:
                    messagebox.showerror("Playback Error", f"Could not pause playback: {e}", parent=self.view)
                    self.stop_playback() # Reset state on error
        else: # Nothing is playing, try to play selected track
            self.play_selected_from_current_tab()
        
        # Update button text regardless of action
        self.view.update_play_pause_button(bool(self.model.currently_playing_path), self.model.is_paused)


    def start_playback(self, track_data):
        # Check if pygame is properly imported and initialized
        if not hasattr(pygame, 'mixer') or not self.model.pygame_initialized:
            self._auto_init_audio()  # Try to initialize audio again
            if not self.model.pygame_initialized:
                logger.error("start_playback called but Pygame mixer not initialized.")
                self.view.set_status("Audio Error: Mixer not initialized.")
                messagebox.showwarning("Audio Error", "Audio system not ready. Cannot play.", parent=self.view)
                return

        if not track_data or not track_data.get('path'):
            missing_reason = "Track data invalid or missing path"
            messagebox.showwarning("Play Error", f"Cannot play track: {missing_reason}.", parent=self.view)
            self.view.set_status(f"Error: Cannot play. {missing_reason}.")
            return
            
        path = track_data['path']
        
        # Verify file exists before attempting to play
        if not os.path.exists(path):
            track_data['exists'] = False  # Update metadata
            missing_reason = f"File does not exist: {path}"
            messagebox.showwarning("Play Error", f"Cannot play track: File not found.", parent=self.view)
            self.view.set_status(f"Error: Cannot play. File not found.")
            return
        else:
            track_data['exists'] = True  # Update metadata
            
        try:
            # Log playback attempt
            logger.info(f"Attempting to play: {path}")
            self.view.set_status(f"Loading: {os.path.basename(path)}")
            
            # Stop any current playback before loading new track
            if pygame.mixer.music.get_busy() or self.model.currently_playing_path:
                pygame.mixer.music.stop()
                if self.model.currently_playing_path:  # Unload if a path was loaded
                    try: 
                        pygame.mixer.music.unload()
                    except Exception as unload_err: 
                        logger.warning(f"Error unloading previous track: {unload_err}")

            # Try to load and play the file
            try:
                pygame.mixer.music.load(path)
            except Exception as load_err:
                logger.error(f"Error loading audio file: {load_err}")
                raise pygame.error(f"Failed to load audio file: {load_err}")
                
            pygame.mixer.music.play()
            pygame.mixer.music.set_volume(self.view.volume_var.get())

            self.model.currently_playing_path = path
            self.model.is_paused = False
            self.model.paused_position = 0
            self.model.current_track_duration = track_data.get('duration', 0)  # Get duration from metadata
            self.model.playback_start_time = time.time()

            self.view.show_prelisten_player_frame()
            self.view.update_prelisten_display(track_data, is_playing_this_track=True)
            self.view.update_play_pause_button(True, False)
            self.view.set_status(f"Playing: {os.path.basename(path)}")
            
            self._start_playback_progress_updater()

        except pygame.error as e:
            logger.error(f"Pygame error starting playback for {path}: {e}", exc_info=True)
            self.view.set_status(f"Audio Error: {e}")
            messagebox.showerror("Playback Error", f"Could not play '{os.path.basename(path)}':\n{e}", parent=self.view)
        except Exception as e:
            logger.error(f"Unexpected error playing {path}: {e}", exc_info=True)
            self.view.set_status(f"Error playing file: {e}")
            messagebox.showerror("Playback Error", f"Unexpected error playing '{os.path.basename(path)}':\n{e}", parent=self.view)
            self.model.currently_playing_path = None # Reset

            self.model.currently_playing_path = None

    def stop_playback(self):
        self._stop_playback_progress_updater()
        
        if self.model.pygame_initialized and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
                if self.model.currently_playing_path: # Only unload if something was loaded
                    pygame.mixer.music.unload()
            except pygame.error as e:
                logger.warning(f"Pygame error during stop/unload: {e}")
            except Exception as e: # Catch any other unexpected errors during unload
                logger.error(f"Unexpected error during pygame music unload: {e}")


        was_playing = self.model.currently_playing_path is not None
        self.model.currently_playing_path = None
        self.model.is_paused = False
        self.model.paused_position = 0
        
        self.view.update_play_pause_button(False, False)
        if was_playing: # Only update status and UI if something was actually stopped
            self.view.set_status("Playback stopped.")
            # Reset progress display to 00:00 / Total Duration
            self.view.update_playback_progress_display(0, self.model.current_track_duration) 
            # Consider if player should hide: self.view.hide_prelisten_player_frame()
        # self.model.current_track_duration = 0 # Keep last track's duration for display until new selection


    def _start_playback_progress_updater(self):
        self._stop_playback_progress_updater() # Ensure no duplicates
        self._update_playback_progress_tick()

    def _stop_playback_progress_updater(self):
        if self.playback_update_job:
            self.view.master.after_cancel(self.playback_update_job)
            self.playback_update_job = None

    def _update_playback_progress_tick(self):
        if self.model.currently_playing_path and not self.model.is_paused and \
           self.model.pygame_initialized and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            
            elapsed_time = time.time() - self.model.playback_start_time
            
            # If duration is known, cap elapsed time and update progress bar
            if self.model.current_track_duration > 0:
                elapsed_time = min(elapsed_time, self.model.current_track_duration)
            
            if not self._scrubbing: # Don't update from tick if user is scrubbing
                self.view.update_playback_progress_display(elapsed_time, self.model.current_track_duration)

            self.playback_update_job = self.view.master.after(250, self._update_playback_progress_tick)
        
        elif self.model.currently_playing_path and not self.model.is_paused:
            # Music stopped on its own (reached end or error not caught by play())
            logger.info(f"Playback of {self.model.currently_playing_path} ended or was interrupted.")
            self.stop_playback() # Clean up state

    def hide_prelisten_player(self): # Command for hide button
        self.stop_playback() # Stop music if playing
        self.view.hide_prelisten_player_frame()
        self.view.set_status("Pre-listen player hidden.")

    def on_scrub_progress(self, value_str): # Called during scale drag
        if not self.model.pygame_initialized or not self.model.currently_playing_path : return

        self._scrubbing = True # Signal that user is scrubbing
        if self.playback_update_job: # Temporarily stop auto-updates
            self.view.master.after_cancel(self.playback_update_job)
            self.playback_update_job = None

        percent = float(value_str) / 100.0
        if self.model.current_track_duration > 0:
            display_time = percent * self.model.current_track_duration
            self.view.progress_label.config(text=f"{format_duration(display_time)} / {format_duration(self.model.current_track_duration)}")
        self.view.progress_scale.focus_set() # Make it easier to drag

    def on_scrub_release(self, event=None): # Called when scale drag ends
        if not self.model.pygame_initialized or not self.model.currently_playing_path or not self._scrubbing:
            self._scrubbing = False
            if self.model.currently_playing_path and not self.model.is_paused: # Restart updater if it was paused
                self._start_playback_progress_updater()
            return

        self._scrubbing = False
        percent = self.view.progress_var.get() / 100.0
        seek_time_seconds = 0
        
        if self.model.current_track_duration > 0:
            seek_time_seconds = percent * self.model.current_track_duration
        
        try:
            # For pygame.mixer.music, play(start=...) is for starting position, not seeking in flight.
            # We need to stop, (optionally reload if issues), then play from new pos.
            # However, some versions/platforms might support set_pos or rewind+play.
            # The most reliable way is often to stop and play(start=...).
            current_volume = self.view.volume_var.get() # Preserve volume

            pygame.mixer.music.stop() # Stop current playback
            # pygame.mixer.music.load(self.model.currently_playing_path) # Re-load might be needed on some systems
            pygame.mixer.music.play(start=seek_time_seconds)
            pygame.mixer.music.set_volume(current_volume) # Reapply volume

            self.model.playback_start_time = time.time() - seek_time_seconds
            self.model.is_paused = False # Ensure not paused after scrub
            self.view.update_play_pause_button(True, False) # Update button to "Pause"
            self._start_playback_progress_updater() # Restart progress updates

        except Exception as e:
            logger.error(f"Error during scrubbing/seeking: {e}", exc_info=True)
            messagebox.showerror("Seek Error", f"Could not seek in track: {e}", parent=self.view)
            self.stop_playback() # Reset on error

    def on_volume_change(self, value_str):
        if not self.model.pygame_initialized or not pygame.mixer.get_init(): return
        try:
            volume = float(value_str)
            pygame.mixer.music.set_volume(volume)
            self.model.update_volume_setting(volume) # Update in model for persistence
        except Exception as e:
            logger.error(f"Error setting volume: {e}")

    # --- Profile Management ---
    def save_profile(self):
        profiles = list(self.model.current_settings.get("profiles", {}).keys())
        last_profile = self.model.current_settings.get("last_profile")
        
        options = []
        if last_profile:
            options.append(f"Overwrite current profile: {last_profile}")
        options.append("Save to new profile")

        # Custom dialog for choosing overwrite or new
        dialog = tk.Toplevel(self.view)
        dialog.title("Save Profile")
        dialog.transient(self.view) # Make it transient to the main app window
        dialog.grab_set()
        # Center dialog (basic centering)
        self.view.master.eval(f'tk::PlaceWindow {str(dialog)} center')

        tk.Label(dialog, text="Choose save option:").pack(padx=10, pady=10)
        var = tk.StringVar(value=options[0] if options else "Save to new profile") # Default selection
        for opt in options:
            tk.Radiobutton(dialog, text=opt, variable=var, value=opt).pack(anchor="w", padx=15)
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        result = {'option': None} # Use a dict to pass result out of callbacks
        def on_ok():
            result['option'] = var.get()
            dialog.destroy()
        def on_cancel():
            dialog.destroy() # result['option'] remains None

        tk.Button(btn_frame, text="OK", command=on_ok, width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=8).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window() # Wait for dialog to close
        choice = result['option']

        if choice is None: # Cancelled
            self.view.set_status("Profile save cancelled.")
            return

        profile_name_to_save = None
        if choice.startswith("Overwrite current profile") and last_profile:
            profile_name_to_save = last_profile
        else: # "Save to new profile" or no last_profile
            profile_name_to_save = simpledialog.askstring(
                "Save New Profile", 
                "Enter a name for this new profile:", 
                parent=self.view
            )
            if not profile_name_to_save:
                self.view.set_status("Profile save cancelled: No name provided.")
                return
            if profile_name_to_save in profiles:
                if not messagebox.askyesno("Overwrite Existing?", f"Profile '{profile_name_to_save}' already exists. Overwrite it?", parent=self.view):
                    self.view.set_status("Profile save cancelled: Did not overwrite.")
                    return

        # Gather data for the profile
        tabs_info = []
        for tab_widget in self.view.get_all_tab_widgets():
            if tab_widget.filepath: # Only save tabs that point to a file
                tabs_info.append({
                    "filepath": tab_widget.filepath,
                    "display_name": tab_widget.get_display_name() # Save current display name
                })
        
        profile_data = {
            "tabs_info": tabs_info,
            "columns": list(self.model.current_settings['columns']), # Save a copy
            "column_widths": self.model.get_column_widths().copy(),
            "volume": self.view.volume_var.get()
        }

        self.model.save_profile_data(profile_name_to_save, profile_data) # Model handles saving to its settings and persisting
        self.view.update_dynamic_profile_menu(self.model.current_settings.get("profiles", {}))
        self.view.set_status(f"Profile '{profile_name_to_save}' saved.")
        logger.info(f"Profile '{profile_name_to_save}' saved with {len(tabs_info)} tabs.")


    def load_profile(self, profile_name, startup=False):
        logger.info(f"Controller: Attempting to load profile: {profile_name} (startup={startup})")
        
        profiles_dict = self.model.current_settings.get("profiles", {})
        if profile_name not in profiles_dict:
            logger.error(f"Profile '{profile_name}' not found in settings.")
            if not startup: # Only show error if not on initial startup
                messagebox.showerror("Load Error", f"Profile '{profile_name}' not found.", parent=self.view)
            if startup: # If profile missing at startup, clear last_profile and proceed
                self.model.current_settings["last_profile"] = None
                self.model.save_all_settings()
                self.restore_open_tabs_from_model() # Fallback to open_tabs or default
            return

        profile_data = profiles_dict[profile_name]
        
        # Apply settings from profile
        self.model.current_settings['columns'] = list(profile_data.get('columns', DEFAULT_COLUMNS))
        self.model.set_column_widths(profile_data.get('column_widths', {}))
        new_volume = profile_data.get('volume', self.model.current_settings.get('volume', 0.8))
        self.model.current_settings['volume'] = new_volume
        self.view.volume_var.set(new_volume)
        if self.model.pygame_initialized and pygame.mixer.get_init():
            pygame.mixer.music.set_volume(new_volume)

        # Close all existing tabs (prompting for save if necessary)
        existing_tab_widgets = self.view.get_all_tab_widgets() # Get a static list
        for tab_widget in existing_tab_widgets:
            self.view.notebook.select(tab_widget) # Select to make it current
            if not self.close_current_tab(): # This handles save prompts
                messagebox.showwarning("Profile Load Cancelled", "Could not close existing tabs. Profile load aborted.", parent=self.view)
                # Revert column/width changes if load is aborted? For now, no.
                return 

        # Load tabs from profile
        tabs_info = profile_data.get('tabs_info', [])
        if not tabs_info:
            logger.warning(f"Profile '{profile_name}' has no tabs. Adding one Untitled tab.")
            self.add_new_tab_command(title="Untitled Playlist (from profile)")
        else:
            for i, tab_info in enumerate(tabs_info):
                filepath = tab_info.get('filepath')
                display_name = tab_info.get('display_name', "Untitled (from profile)")
                
                if filepath:
                    if os.path.exists(filepath):
                        logger.debug(f"Profile load: Adding tab for existing file: {filepath}")
                        new_tab = self.add_new_tab_command(title=display_name, filepath=filepath)
                        # add_new_tab_command handles loading content via PlaylistTab constructor
                        if new_tab:
                            new_tab.tab_display_name = display_name # Ensure profile's display name is used
                            new_tab.update_tab_title()
                            if not new_tab._track_data and os.path.exists(filepath): # File exists but no tracks loaded
                                logger.warning(f"File {filepath} from profile loaded 0 tracks. Check file content.")
                                # No messagebox here, PlaylistTab load should handle specific errors.
                    else:
                        logger.warning(f"File path from profile does not exist, skipping: {filepath}")
                        if not startup: # Avoid too many popups on startup
                            messagebox.showwarning("Load Warning", f"Playlist file not found:\n{filepath}\nThis tab was not loaded.", parent=self.view)
                else: # No filepath in profile tab_info (should ideally not happen for saved tabs)
                    logger.info("Profile load: Adding an Untitled tab as specified in profile.")
                    self.add_new_tab_command(title=display_name)
        
        # After loading all tabs from profile, ensure at least one tab exists
        if not self.view.notebook.tabs():
            logger.warning("No tabs were loaded from profile. Adding a default Untitled tab.")
            self.add_new_tab_command(title="Untitled Playlist")

        self.model.current_settings["last_profile"] = profile_name
        self.model.save_all_settings() # Save change to last_profile and potentially columns/widths
        self.view.update_dynamic_profile_menu(self.model.current_settings.get("profiles", {}))
        self.view.update_column_settings_in_all_tabs(self.model.current_settings['columns'])
        self.view.update_column_widths_in_all_tabs(self.model.get_column_widths())
        self.view.set_status(f"Profile '{profile_name}' loaded.")
        logger.info(f"Profile '{profile_name}' loading complete.")

        if self.view.notebook.tabs(): # If tabs exist, select first and trigger tab change
             self.view.notebook.select(self.view.notebook.tabs()[0])
             self.on_tab_change()


    def delete_profile_via_dialog(self):
        profiles = list(self.model.current_settings.get("profiles", {}).keys())
        if not profiles:
             messagebox.showinfo("Delete Profile", "There are no profiles to delete.", parent=self.view)
             return

        dialog = tk.Toplevel(self.view)
        dialog.title("Delete Profile")
        dialog.transient(self.view)
        dialog.grab_set()
        self.view.master.eval(f'tk::PlaceWindow {str(dialog)} center')

        tk.Label(dialog, text="Select a profile to delete:").pack(padx=10, pady=10)
        
        listbox_var = tk.StringVar(value=profiles) # For listbox content
        listbox = tk.Listbox(dialog, listvariable=listbox_var, height=min(10, len(profiles)), exportselection=False)
        listbox.pack(padx=10, pady=5, fill=tk.X, expand=True)
        if profiles: listbox.selection_set(0) # Pre-select first item

        result = {'profile': None}
        def on_ok():
            sel_indices = listbox.curselection()
            if sel_indices:
                result['profile'] = profiles[sel_indices[0]]
            dialog.destroy()
        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Delete", command=on_ok, width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=8).pack(side=tk.LEFT, padx=5)
        dialog.wait_window()

        profile_to_delete = result['profile']
        if profile_to_delete:
            if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the profile '{profile_to_delete}'?", parent=self.view):
                self.model.delete_profile_data(profile_to_delete)
                self.view.update_dynamic_profile_menu(self.model.current_settings.get("profiles", {}))
                self.view.set_status(f"Profile '{profile_to_delete}' deleted.")
        elif profile_to_delete is not None: # Means OK was clicked but nothing selected (should not happen if pre-selected)
             messagebox.showwarning("Delete Error", "No profile selected for deletion.", parent=self.view)


    def restore_open_tabs_from_model(self):
        """Restores tabs based on 'open_tabs' list in model.current_settings."""
        open_tab_filepaths = self.model.current_settings.get('open_tabs', [])
        
        # Close any existing tabs first (e.g. if called not at startup)
        # This part should ideally not prompt if it's a clean restore, but for safety:
        existing_tab_widgets = self.view.get_all_tab_widgets()
        for tab_widget in existing_tab_widgets:
            # A non-interactive close might be better here if this is purely for restore
            self.view.remove_tab_from_notebook(tab_widget) 

        if not open_tab_filepaths:
            logger.info("No tabs to restore from settings.")
            # self.add_new_tab_command("Untitled Playlist") # Ensure one tab if none restored (handled later)
            return

        logger.info(f"Restoring {len(open_tab_filepaths)} tabs from settings.")
        for filepath in open_tab_filepaths:
            if filepath and os.path.exists(filepath):
                # add_new_tab_command handles loading content if filepath is valid
                self.add_new_tab_command(filepath=filepath) 
            elif filepath and not os.path.exists(filepath):
                logger.warning(f"Filepath from open_tabs setting does not exist, creating empty tab: {filepath}")
                # Create an untitled tab but with a name hinting at the missing file
                missing_name = f"Missing: {os.path.basename(filepath)}"
                new_tab = self.add_new_tab_command(title=missing_name)
                if new_tab: new_tab.is_dirty = True # Mark as dirty since its intended content is gone
            else: # filepath is None (was an unsaved tab)
                self.add_new_tab_command(title="Untitled Playlist")

    # --- Tab Manipulation Callbacks (for notebook bindings) ---
    def on_tab_right_click_context(self, event):
        try:
            tab_index = self.view.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError: # Clicked outside a tab label
            return

        tab_widget_id_tkpath = self.view.notebook.tabs()[tab_index]
        tab_widget_instance = self.view.nametowidget(tab_widget_id_tkpath)

        if not isinstance(tab_widget_instance, PlaylistTab): return # Should not happen

        menu = tk.Menu(self.view, tearoff=0)
        menu.add_command(label="Rename Tab", command=lambda: self.rename_notebook_tab_dialog(tab_index, tab_widget_instance))
        menu.add_command(label="Close Tab", command=lambda: self._close_specific_tab(tab_widget_instance))
        menu.add_separator()
        menu.add_command(label="Close Other Tabs", command=lambda: self._close_other_tabs(tab_widget_instance))
        menu.add_command(label="Close Tabs to the Right", command=lambda: self._close_tabs_to_the_right(tab_index))
        
        menu.tk_popup(event.x_root, event.y_root)

    def rename_notebook_tab_dialog(self, tab_index, tab_widget_instance):
        current_title = tab_widget_instance.get_display_name()
        new_title = simpledialog.askstring("Rename Tab", "Enter new tab name:",
                                           initialvalue=current_title, parent=self.view)
        if new_title and new_title.strip() and new_title.strip() != current_title:
            clean_title = new_title.strip()
            self.view.notebook.tab(tab_index, text=clean_title + ("*" if tab_widget_instance.is_dirty else ""))
            tab_widget_instance.tab_display_name = clean_title
            # tab_widget_instance.update_tab_title() # Not needed if we set text with asterisk directly

    def _close_specific_tab(self, tab_to_close: PlaylistTab):
        self.view.notebook.select(tab_to_close) # Make it current
        self.close_current_tab() # This handles save prompts

    def _close_other_tabs(self, keep_tab: PlaylistTab):
        all_tabs = list(self.view.notebook.tabs()) # Get list of tk_paths
        for tab_tkpath in all_tabs:
            tab_widget = self.view.nametowidget(tab_tkpath)
            if tab_widget != keep_tab and isinstance(tab_widget, PlaylistTab):
                self.view.notebook.select(tab_widget)
                if not self.close_current_tab():
                    # User cancelled closing one of the "other" tabs
                    messagebox.showinfo("Operation Cancelled", "Closing other tabs was cancelled.", parent=self.view)
                    break # Stop trying to close more tabs
        self.view.notebook.select(keep_tab) # Reselect the original tab

    def _close_tabs_to_the_right(self, keep_tab_index):
        all_tabs_tkpaths = list(self.view.notebook.tabs())
        tabs_to_close_tkpaths = all_tabs_tkpaths[keep_tab_index + 1:]
        
        for tab_tkpath in tabs_to_close_tkpaths:
            tab_widget = self.view.nametowidget(tab_tkpath)
            if isinstance(tab_widget, PlaylistTab):
                self.view.notebook.select(tab_widget)
                if not self.close_current_tab():
                    messagebox.showinfo("Operation Cancelled", "Closing tabs to the right was cancelled.", parent=self.view)
                    break
        # Reselect the tab that was to the left of the closed ones (or the first one if keep_tab_index was 0 and all to right closed)
        if self.view.notebook.tabs(): # Check if any tabs remain
            target_select_index = min(keep_tab_index, len(self.view.notebook.tabs()) -1)
            self.view.notebook.select(self.view.notebook.tabs()[target_select_index])


    def on_tab_press_for_drag(self, event):
        try:
            # Check if the click is on a tab label
            if self.view.notebook.identify(event.x, event.y) == 'label':
                self._dragged_tab_index = self.view.notebook.index(f"@{event.x},{event.y}")
                self._dragged_tab_id = self.view.notebook.tabs()[self._dragged_tab_index] # tk_path of tab
            else:
                self._dragged_tab_index = None
                self._dragged_tab_id = None
        except tk.TclError:
            self._dragged_tab_index = None
            self._dragged_tab_id = None

    def on_tab_drag(self, event):
        if self._dragged_tab_index is None or self._dragged_tab_id is None:
            return
        try:
            # Where is the mouse pointer now in terms of tab index?
            target_index = self.view.notebook.index(f"@{event.x},{event.y}")
            
            if target_index != self._dragged_tab_index:
                # Move the dragged tab to the new position
                self.view.notebook.insert(target_index, self._dragged_tab_id)
                self._dragged_tab_index = target_index # Update current index of dragged tab
        except tk.TclError: # Mouse might be dragged off the tab area
            pass 

    def on_tab_release_for_drag(self, event):
        if self._dragged_tab_index is not None:
            # Update open_tabs in settings to reflect new order
            self._prepare_and_save_settings() # This will get current tab order
        self._dragged_tab_index = None
        self._dragged_tab_id = None


    def toggle_filter_bar_for_current_tab(self):
        tab = self.view.get_current_tab_widget()
        if tab:
            tab.show_filter_bar() # PlaylistTab needs to implement this

    def open_settings_dialog(self):
        # This would open a more comprehensive settings dialog if one were implemented
        # For now, let's assume a simple dialog or direct to column customizer as example
        # messagebox.showinfo("Settings", "Settings dialog not fully implemented.\nOpening Column Customizer as a placeholder.", parent=self.view)
        # self.customize_columns()
        from settings_dialog import SettingsDialog # Assuming settings_dialog.py exists

        def save_settings_callback(new_settings_from_dialog):
            # Carefully merge new_settings_from_dialog into self.model.current_settings
            # For example, if settings_dialog can change 'columns':
            if 'columns' in new_settings_from_dialog:
                self.model.current_settings['columns'] = new_settings_from_dialog['columns']
                self.view.update_column_settings_in_all_tabs(new_settings_from_dialog['columns'])
            
            if 'settings_file_path' in new_settings_from_dialog:
                new_path = new_settings_from_dialog['settings_file_path']
                if new_path != self.model.get_actual_settings_file_path():
                    # Handle settings file path change. This might involve moving the file.
                    # For now, just update the path in settings.
                    self.model.current_settings['settings_file_path'] = new_path
                    logger.info(f"Settings file path changed to: {new_path}")


            # Potentially other settings...
            self.model.save_all_settings() # Save all changes
            self.view.set_status("Settings updated.")

        # Pass a copy of current settings to the dialog
        # The dialog should return only the settings it's responsible for changing
        try:
            dialog = SettingsDialog(self.view.master, self.model.current_settings.copy(), save_settings_callback, self)
            # The SettingsDialog constructor in its original form might not need the controller ('self')
            # Adjust based on SettingsDialog's actual signature. If it needs the controller:
            # dialog = SettingsDialog(self.view.master, self.model.current_settings.copy(), save_settings_callback, self)
        except NameError:
             messagebox.showinfo("Settings", "SettingsDialog class not found. This feature is unavailable.", parent=self.view)
        except Exception as e:
            logger.error(f"Error opening settings dialog: {e}", exc_info=True)
            messagebox.showerror("Error", f"Could not open settings dialog: {e}", parent=self.view)

