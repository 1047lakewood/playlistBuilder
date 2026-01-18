from tkinter import filedialog, simpledialog, messagebox
from unittest import result
from models import playlist
from models.playlist import Playlist
from models.track import Track
from typing import List
import os
import threading
from PlaylistService.track_utils import TrackUtils
from playlist_notebook_view import PlaylistTabView
import asyncio
from test import Test
import re
from metadata_edit_dialog import MetadataEditDialog
from calculate_start_times_dialog import CalculateStartTimesDialog
from audio_converter import AudioConverter
import shutil
import app_config
import logging


class ControllerActions():

    def __init__(self, controller):
        self.controller = controller
        self.actions = {
            "open": self.open_playlist,
            "save": self.save_current_playlist,
            "save_as": self.save_current_playlist_as,
            "test": self.test,
            "test2": self.test2,
            "save_profile": self.controller.profile_loader.save_profile,
            "load_profile": self.controller.profile_loader.load_profile,
            "manage_profiles": self.controller.profile_loader.manage_profiles,
            "reload_api_playlist": self.reload_api_playlist_action,
            "disconnect_all_remotes": self.disconnect_all_remotes
        }
        self.clipboard = []
        self.dialog_open = False
    def test(self, event=None):
        test = Test(self.controller)
        test.test()
    def test2(self, event=None):
        test = Test(self.controller)
        test.test2()
    def get_selected_tab(self):
        return self.controller.notebook_view.get_selected_tab()
    def get_selected_tab_playlist(self):
        return self.get_selected_tab().playlist

    def open_playlist(self, event=None):
        filetypes = [
        ("Playlist files", "*.m3u;*.m3u8"),
        ("All files", "*.*")
        ]
    
        file_path = filedialog.askopenfilename(
            title="Select a Playlist File",
            filetypes=filetypes,
            initialdir=app_config.get(["paths","playlists_dir"], "")
        )
        if file_path:
            self.controller.playlist_service.load_playlist_from_path(file_path)
            self.reload_open_playlists()

    def save_current_playlist_as(self, event=None):
        playlist = self.get_selected_tab_playlist()
        if playlist.path is not None:
            file_name = os.path.basename(playlist.path)
        else:
            file_name = ""
        file_path = filedialog.asksaveasfilename(
            title="Save Playlist As",
            initialfile=file_name,
            defaultextension=".m3u8",
            filetypes=[
                ("Playlist files", ".m3u;*.m3u8"),
                ("All files", "*.*")
            ],
            initialdir=os.path.dirname(playlist.path) if playlist.path else app_config.get(["paths","playlists_dir"], "")
        )
        if file_path:
            playlist.path = file_path
            self.controller.playlist_service.save_playlist(playlist)
    def save_current_playlist(self, event=None):
        playlist = self.get_selected_tab_playlist()
        print("playlsit.path", playlist.path)        
        if playlist.path is None:
            self.save_current_playlist_as()
            return
        self.controller.playlist_service.save_playlist(playlist)

    def close_playlist(self, playlist: Playlist):
        self.controller.playlist_service.close_playlist(playlist)
        

    # is this correct?
    def get_open_playlists(self):
        return self.controller.playlist_service.playlists
    
    def get_tab_state(self):
        return self.controller.notebook_view.get_tab_state()

    def reload_rows_in_selected_tab_without_intro_check(self):
        tab = self.get_selected_tab()
        playlist = tab.playlist
        tab.reload_rows()

    def reload_open_playlists(self):
        open_playlists: List[Playlist] = self.get_open_playlists()
        playlists_displayed_in_tabs = [playlist for playlist in self.controller.notebook_view.get_tab_playlists()]

        # Build a set of source_ids already displayed for API playlists
        displayed_source_ids = set()
        for tab in self.controller.notebook_view.get_tabs():
            if tab.playlist.type == Playlist.PlaylistType.API and tab.playlist.source_id:
                displayed_source_ids.add(tab.playlist.source_id)

        for playlist in open_playlists:
            if playlist not in playlists_displayed_in_tabs:
                # Skip API playlists that already have a tab (check by source_id)
                if playlist.type == Playlist.PlaylistType.API:
                    if playlist.source_id in displayed_source_ids:
                        continue
                    # API playlists should be opened via toggle_remote_source, not here
                    continue

                title = os.path.splitext(os.path.basename(playlist.path))[0]
                tab = self.controller.notebook_view.add_tab(playlist, title)
                continue
        for tab in self.controller.notebook_view.get_tabs():
            # Skip API playlists - they already have metadata from server
            # and intros were already checked in toggle_remote_source()
            if tab.playlist.type == Playlist.PlaylistType.API:
                continue
            self.load_playlist_metadata_for_tab(tab)


    
    def load_playlist_metadata_for_tab(self, tab: PlaylistTabView):
        # Create a thread to run the metadata loading asynchronously
        thread = threading.Thread(target=self._async_load_playlist_metadata, args=(tab, None))
        thread.daemon = True  # Thread will exit when main program exits
        thread.start()
 
    def _async_load_playlist_metadata(self, playlist_tab: PlaylistTabView = None, playlist: Playlist = None):
        if playlist_tab == None and playlist == None:
            print("No tab or playlist provided")
            return
        try:
            if playlist == None:
                playlist = playlist_tab.playlist
            self.controller.playlist_service.update_playlist_metadata(playlist)
            self.controller.playlist_service.check_for_intros_and_exists(playlist)
            if playlist_tab:
                playlist_tab.after(0, lambda pt=playlist_tab: pt.reload_rows(preserve_scroll=True) if pt.winfo_exists() else None)
        except Exception as e:
            print(e)
    
 

    def get_selected_row_indexes(self):
        tab = self.controller.notebook_view.get_selected_tab()
        return tab.get_selected_row_indexes()
    def get_selected_tracks(self):
        selected_indexes = self.get_selected_row_indexes()
        playlist = self.get_selected_tab_playlist()
        return [playlist.tracks[i] for i in selected_indexes]
    
    
    
    
    def select_row_at_index(self, index: list[int]):
        tab = self.get_selected_tab()
        if index == None:
            index = -1
        rows_to_select = [tab.tree.get_children()[i] for i in index]
        tab.tree.selection_set(rows_to_select) 
        tab.tree.focus(rows_to_select[-1])
        tab.tree.see(rows_to_select[-1])

    def check_for_intros_and_if_exists(self, playlist = None, tracks = None):
        self.controller.playlist_service.check_for_intros_and_exists(playlist, tracks)

    def open_edit_metadata_dialog(self):
        selected_tracks = self.get_selected_tracks()
        if not selected_tracks:
            messagebox.showinfo("Edit Metadata", "No track selected.", parent=self.controller.root)
            return
        track = selected_tracks[0]
        if track.path.lower().endswith('.mp4'):
            messagebox.showinfo(
                "Edit Metadata",
                "Cannot edit metadata for video files (.mp4).\nOpen in Audacity to convert to audio.",
                parent=self.controller.root
            )
            return
        
        if len(selected_tracks) > 1:
            messagebox.showerror("Error", "Please select only one track")
            return
        edit_metadata_dialog = MetadataEditDialog(self.controller.root, selected_tracks[0], on_done = self.edit_metadata)


    def edit_metadata(self, track: Track, result):
        TrackUtils.change_track_metadata(track, artist=result[1], title=result[0])
        current_playlist = self.get_selected_tab_playlist()
        # Check for intros after metadata update
        self.check_for_intros_and_if_exists(playlist=current_playlist, tracks=[track])
        self.reload_rows_in_selected_tab_without_intro_check()
        # If it's an Remote Playlist, need to update there too
        if current_playlist.type == Playlist.PlaylistType.API:
            track_index = current_playlist.tracks.index(track)
            self.remove_and_reinsert_track(track, track_index)

    def remove_and_reinsert_track(self, track: Track, track_index_0_based: int):
        """
        Removes a track from the Remote Playlist and re-inserts it with updated metadata.
        Updates the local playlist representations from the API manager's state.
        """
        current_tab = self.get_selected_tab()
        current_playlist = current_tab.playlist
        api_manager = self.controller.playlist_service.api_manager
        track_index_1_based = track_index_0_based + 1

        logging.info(f"API Sync: Attempting to remove track '{track.title}' at 1-based index {track_index_1_based} from remote playlist.")
        
        # Safeguard: Verify track is still at the expected local index, or find it again.
        # This helps if the local list might have changed slightly before this async operation runs.
        actual_local_index_0_based = -1
        try:
            actual_local_index_0_based = current_playlist.tracks.index(track)
            if actual_local_index_0_based != track_index_0_based:
                logging.warning(f"API Sync: Track '{track.title}' was at 0-based index {track_index_0_based}, but now found at {actual_local_index_0_based}. Using new index.")
                track_index_1_based = actual_local_index_0_based + 1
            else:
                 # Original index is fine
                 pass 
        except ValueError:
            logging.error(f"API Sync: Track '{track.title}' not found in local playlist '{current_playlist.name_for_display()}' before API removal. Aborting sync for this track.")
            messagebox.showerror("API Sync Error", f"Could not find track '{track.title}' in the local playlist to sync removal. Please reload the Remote Playlist.")
            return

        if api_manager.remove_track(track_index_1_based):
            logging.info(f"API Sync: Successfully removed track '{track.title}' from remote playlist.")
            
            logging.info(f"API Sync: Attempting to re-insert track '{track.title}' (Artist: {track.artist}) at 1-based index {track_index_1_based} in remote playlist.")
            if api_manager.insert_track(track, track_index_1_based):
                logging.info(f"API Sync: Successfully re-inserted track '{track.title}' into remote playlist.")
            else:
                logging.error(f"API Sync: Failed to re-insert track '{track.title}' into remote playlist.")
                messagebox.showerror("API Sync Error", f"Failed to re-insert track '{track.title}' on the server. The playlist might be inconsistent. Please reload the Remote Playlist.")
        else:
            logging.error(f"API Sync: Failed to remove track '{track.title}' from remote playlist at 1-based index {track_index_1_based}.")
            messagebox.showerror("API Sync Error", f"Failed to remove track '{track.title}' from the server. The playlist might be inconsistent. Please reload the Remote Playlist.")

        # After API operations, the api_manager.playlist is reloaded internally by its methods.
        # Synchronize local playlist instances with the fresh state from api_manager.playlist.
        if api_manager.playlist:
            logging.info(f"API Sync: Updating local playlist views from api_manager.playlist which has {len(api_manager.playlist.tracks)} tracks.")
            # Update the current tab's playlist object directly with tracks from the reloaded Remote Playlist
            current_tab.playlist.tracks = list(api_manager.playlist.tracks) # Use a new list copy
            current_tab.playlist.path = api_manager.playlist.path 
            current_tab.playlist.type = api_manager.playlist.type

            # If the playlist being modified is the main Remote Playlist in the store, update it too.
            if self.controller.playlist_service.store.api_playlist and \
               self.controller.playlist_service.store.api_playlist is current_playlist:
                 self.controller.playlist_service.store.api_playlist.tracks = list(api_manager.playlist.tracks)
                 self.controller.playlist_service.store.api_playlist.path = api_manager.playlist.path
                 self.controller.playlist_service.store.api_playlist.type = api_manager.playlist.type
                 logging.info("API Sync: Central store's Remote Playlist instance updated.")
            
            # Reload rows in the UI to reflect the (potentially) changed playlist from the server
            self.reload_rows_in_selected_tab_without_intro_check()
            logging.info("API Sync: UI reloaded for the current tab.")
        else:
            logging.error("API Sync: api_manager.playlist is None after operations. Cannot update local state. Critical issue, suggest reload.")
            messagebox.showwarning("API Sync Critical Error", "The Remote Playlist data is unavailable after editing metadata. Please reload the Remote Playlist to ensure consistency.")

    def rename_track_file_path_dialog(self, event=None):
        selected_tracks = self.get_selected_tracks()
        if not selected_tracks:
            messagebox.showinfo("Rename File Path", "No track selected.", parent=self.controller.root)
            return
        if len(selected_tracks) > 1:
            messagebox.showerror("Error", "Please select only one track to rename.", parent=self.controller.root)
            return
        
        track = selected_tracks[0]
        current_playlist = self.get_selected_tab_playlist()
        track_index = current_playlist.tracks.index(track)

        new_path_input = simpledialog.askstring("Rename File Path", "Enter new file path:",
                                              parent=self.controller.root,
                                              initialvalue=track.path)
        
        if new_path_input and new_path_input != track.path:
            normalized_new_path = os.path.normpath(new_path_input)
            original_path = track.path 

            old_path_is_file = os.path.isfile(original_path)
            
            # Ensure the target directory exists before attempting rename/move
            # This applies if normalized_new_path is intended as a file path.
            prospective_target_dir = os.path.dirname(normalized_new_path)
            if prospective_target_dir and not os.path.exists(prospective_target_dir):
                try:
                    os.makedirs(prospective_target_dir, exist_ok=True)
                    logging.info(f"Created directory: {prospective_target_dir}")
                except OSError as e:
                    messagebox.showerror("Directory Creation Error",
                                         f"Could not create directory '{prospective_target_dir}':\n{e}",
                                         parent=self.controller.root)
                    return # Cannot proceed if target directory can't be made

            new_path_target_exists = os.path.exists(normalized_new_path)
            operation_successful = False
            path_to_update_track_with = normalized_new_path # Default path for track attribute

            if not new_path_target_exists:
                # Target path is clear
                if old_path_is_file:
                    # Old file exists, new path is clear: rename file
                    try:
                        os.rename(original_path, normalized_new_path)
                        logging.info(f"File renamed from '{original_path}' to '{normalized_new_path}'")
                        # path_to_update_track_with is already normalized_new_path
                        operation_successful = True
                    except OSError as e:
                        messagebox.showerror("File Rename Error", 
                                             f"Could not rename file from '{original_path}' to '{normalized_new_path}':\n{e}",
                                             parent=self.controller.root)
                else:
                    # Old file doesn't exist, new path is clear: just update path attribute
                    # path_to_update_track_with is already normalized_new_path
                    operation_successful = True
            else: 
                # Target path (normalized_new_path) is occupied
                if old_path_is_file:
                    # Old file exists, new path is occupied: move/overwrite file
                    try:
                        if os.path.isdir(normalized_new_path):
                            # Target is a directory, move file into it
                            shutil.move(original_path, normalized_new_path)
                            path_to_update_track_with = os.path.join(normalized_new_path, os.path.basename(original_path))
                            logging.info(f"File '{original_path}' moved into directory '{normalized_new_path}'. New path: '{path_to_update_track_with}'")
                        else:
                            # Target is a file (or other), attempt to overwrite
                            shutil.move(original_path, normalized_new_path) 
                            # path_to_update_track_with is already normalized_new_path
                            logging.info(f"File '{original_path}' moved to '{normalized_new_path}', overwriting/replacing existing target.")
                        operation_successful = True
                    except Exception as e:
                        messagebox.showerror("File Move/Rename Error", 
                                             f"Could not move/rename file from '{original_path}' to '{normalized_new_path}':\n{e}",
                                             parent=self.controller.root)
                else:
                    # Old file doesn't exist, new path is occupied: just update path attribute
                    # (allows pointing a 'red' track to an existing file)
                    # path_to_update_track_with is already normalized_new_path
                    operation_successful = True
        
            if operation_successful:
                track.path = path_to_update_track_with
                self.controller.playlist_service.update_track_metadata([track])
                self.check_for_intros_and_if_exists(playlist=current_playlist, tracks=[track])
                self.reload_rows_in_selected_tab_without_intro_check()
                if current_playlist.type == Playlist.PlaylistType.API:
                    self.remove_and_reinsert_track(track, track_index)
                self.controller.mark_profile_dirty()
            

    def rename_track_by_browsing_dialog(self, event=None):
        selected_tracks = self.get_selected_tracks()
        if not selected_tracks:
            messagebox.showinfo("Rename by Browsing", "No track selected.", parent=self.controller.root)
            return
        if len(selected_tracks) > 1:
            messagebox.showerror("Error", "Please select only one track to rename.", parent=self.controller.root)
            return

        track = selected_tracks[0]
        current_playlist = self.get_selected_tab_playlist()
        track_index = current_playlist.tracks.index(track)
        initial_dir = os.path.dirname(track.path)

        filetypes = [
            ("Audio files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a"),
            ("All files", "*.*")
        ]

        new_path = filedialog.askopenfilename(
            initialfile=os.path.basename(track.path),
            title="Select New Audio File",
            initialdir=initial_dir,
            filetypes=filetypes,
            parent=self.controller.root
        )

        if new_path and new_path != track.path:
            new_path = os.path.normpath(new_path) # Normalize path
            track.path = new_path
            self.controller.playlist_service.update_track_metadata([track])
            self.check_for_intros_and_if_exists(playlist=current_playlist, tracks=[track])
            self.reload_rows_in_selected_tab_without_intro_check()
            if current_playlist.type == Playlist.PlaylistType.API:
                self.remove_and_reinsert_track(track, track_index)

    def remove_and_reinsert_track(self, track: Track, track_index: int):
        playlist = self.get_selected_tab_playlist()
        if playlist.type == Playlist.PlaylistType.API:
            self.controller.playlist_service.api_manager.remove_tracks([track_index + 1])
            self.controller.playlist_service.api_manager.insert_tracks([track], track_index + 1)

    def convert_tracks_to_mp3(self, event=None):
        """Convert selected tracks to MP3 format"""
        selected_tracks = self.get_selected_tracks()
        if not selected_tracks:
            messagebox.showinfo("Convert to MP3", "No tracks selected.", parent=self.controller.root)
            return
            
        # Confirm conversion with user
        if len(selected_tracks) == 1:
            message = f"Convert '{os.path.basename(selected_tracks[0].path)}' to MP3?"
        else:
            message = f"Convert {len(selected_tracks)} tracks to MP3?"
            
        if not messagebox.askyesno("Convert to MP3", message, parent=self.controller.root):
            return
            
        # Process each track
        converted_count = 0
        failed_count = 0
        skipped_count = 0
        current_playlist = self.get_selected_tab_playlist()
        
        for track in selected_tracks:
            # Skip if already MP3
            file_ext = os.path.splitext(track.path)[1].lower()
            if file_ext == '.mp3':
                skipped_count += 1
                continue
                
            # Get track index for updating Remote Playlist if needed
            track_index = current_playlist.tracks.index(track)

            # Convert the file
            try:
                converted_path = AudioConverter.convert_to_mp3(track.path, delete_original=True)
                if converted_path and os.path.exists(converted_path):
                    # Update track path
                    track.path = converted_path
                    # Update metadata
                    self.controller.playlist_service.update_track_metadata([track])
                    # Check for intros
                    self.check_for_intros_and_if_exists(tracks=[track])
                    # Update Remote Playlist if needed
                    if current_playlist.type == Playlist.PlaylistType.API:
                        self.remove_and_reinsert_track(track, track_index)
                    converted_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Error converting track to MP3: {str(e)}")
                failed_count += 1
        
        # Reload the playlist view
        self.reload_rows_in_selected_tab_without_intro_check()
        
        # Show results
        result_message = f"Conversion complete:\n"
        if converted_count > 0:
            result_message += f"- {converted_count} track(s) converted successfully\n"
        if skipped_count > 0:
            result_message += f"- {skipped_count} track(s) already in MP3 format\n"
        if failed_count > 0:
            result_message += f"- {failed_count} track(s) failed to convert\n"
            
        messagebox.showinfo("Convert to MP3", result_message, parent=self.controller.root)

    def reload_api_playlist_action(self, event=None):
        """Reload the currently selected Remote Playlist while preserving scroll position."""
        # Get the currently selected tab
        try:
            selected_tab = self.controller.notebook_view.get_selected_tab()
            if not selected_tab or selected_tab.playlist.type != Playlist.PlaylistType.API:
                # Find any API tab
                api_tabs = [t for t in self.controller.notebook_view.get_tabs() 
                           if t.playlist.type == Playlist.PlaylistType.API]
                if not api_tabs:
                    messagebox.showinfo("Reload", "No remote playlist is currently open.")
                    return
                selected_tab = api_tabs[0]
        except Exception:
            messagebox.showinfo("Reload", "No remote playlist is currently open.")
            return

        source_id = selected_tab.playlist.source_id
        if not source_id:
            messagebox.showerror("Reload Error", "Cannot determine source for this playlist.")
            return

        # Preserve current vertical scroll position
        try:
            yview = selected_tab.tree.yview()
            yview_first = yview[0] if yview else 0.0
        except Exception:
            yview_first = 0.0

        # Reload the Remote Playlist from the service
        api_playlist = self.controller.playlist_service.reload_api_playlist(source_id)
        if api_playlist is None:
            messagebox.showerror("Reload Error", f"Failed to reload playlist from {source_id}.")
            return

        # Ensure intros / metadata are up-to-date
        self.controller.playlist_service.check_for_intros_and_exists(api_playlist)

        # Update the existing tab's playlist instance
        selected_tab.playlist.tracks = list(api_playlist.tracks)
        selected_tab.playlist.path = api_playlist.path
        selected_tab.playlist.type = api_playlist.type

        # Reload the rows in the UI
        selected_tab.reload_rows()

        # Restore the vertical scroll position
        try:
            selected_tab.tree.update_idletasks()
            selected_tab.tree.yview_moveto(yview_first)
        except Exception:
            pass

        # Ensure the tab is selected
        self.controller.notebook_view.notebook.select(str(selected_tab))
    
    def disconnect_all_remotes(self, event=None):
        """Disconnect all remote playlists."""
        # Avoid writing settings.json once per remote; we'll save once at the end.
        setattr(self.controller, "_suppress_profile_autosave", True)
        api_tabs = [t for t in self.controller.notebook_view.get_tabs() 
                   if t.playlist.type == Playlist.PlaylistType.API]
        
        for tab in api_tabs:
            source_id = tab.playlist.source_id
            if source_id:
                self.toggle_remote_source(source_id, False)

        setattr(self.controller, "_suppress_profile_autosave", False)
        self._autosave_current_profile()

    def _autosave_current_profile(self) -> None:
        """Persist current open tabs into the active profile, without prompting.

        This is used to make remote playlist checkbox state survive app restarts.
        """
        try:
            if getattr(self.controller, "_is_loading_profile", False):
                return
            if getattr(self.controller, "_suppress_profile_autosave", False):
                return
            profile_name = self.controller.persistence.get_current_profile_name()
            if not profile_name:
                return
            self.controller.profile_loader.save_profile(profile_name)
        except Exception as e:
            # Never let persistence failures break UI actions.
            print(f"Warning: Failed to auto-save profile: {e}")
    
    def toggle_remote_source(self, source_id: str, show: bool):
        """Show or hide a specific remote playlist source.
        
        Args:
            source_id: The ID of the remote source (e.g., "104.7", "88.7")
            show: True to connect and show, False to disconnect and hide
        """
        try:
            # Get source info
            sources = self.controller.playlist_service.get_available_sources()
            source_name = source_id
            for sid, name in sources:
                if sid == source_id:
                    source_name = name
                    break
            
            # Find if tab for this source is already open
            existing_tab = None
            for tab_view in self.controller.notebook_view.get_tabs():
                if (tab_view.playlist.type == Playlist.PlaylistType.API and 
                    tab_view.playlist.source_id == source_id):
                    existing_tab = tab_view
                    break
            
            if show:
                # Connect and show
                if existing_tab is None:
                    # Load the playlist from this source
                    api_playlist = self.controller.playlist_service.load_api_playlist(source_id)
                    if api_playlist is None:
                        # Show error but don't crash
                        status, message = self.controller.playlist_service.get_source_status(source_id)
                        messagebox.showerror(
                            "Connection Failed", 
                            f"Could not connect to {source_name}.\n\n{message}"
                        )
                        # Update menu checkbox to reflect failure
                        self.controller.menu_bar.set_source_connected(source_id, False)
                        return
                    
                    self.controller.playlist_service.check_for_intros_and_exists(api_playlist)
                    
                    # Add the tab
                    tab = self.controller.notebook_view.add_tab(api_playlist, source_name)
                    if tab:
                        tab_id = str(tab)
                        # Insert at position based on source order
                        self.controller.notebook_view.notebook.insert(0, tab_id)
                        self.controller.notebook_view.notebook.select(tab_id)

                        # Start auto-reload if enabled in config
                        auto_reload_config = app_config.get(["network", "auto_reload"], {})
                        if auto_reload_config.get("enabled", True):
                            interval = auto_reload_config.get("interval_seconds", 30)
                            tab.start_auto_reload(interval)

                    print(f"Remote Playlist '{source_name}' loaded and displayed")
                else:
                    # Tab exists, just select it
                    tab_id = str(existing_tab)
                    self.controller.notebook_view.notebook.select(tab_id)
                
                # Show the currently playing bar if any remote is connected
                self.controller.container_view.show_currently_playing_bar()
                
                # Update menu
                self.controller.menu_bar.set_source_connected(source_id, True)
                self._autosave_current_profile()
            else:
                # Disconnect and hide
                if existing_tab is not None:
                    self.controller.notebook_view.remove_tab(existing_tab)
                    print(f"Remote Playlist '{source_name}' disconnected")
                
                # Update menu
                self.controller.menu_bar.set_source_connected(source_id, False)
                
                # Remove this station from the currently playing bar
                self.controller.container_view.remove_station(source_id)
                
                # Clear the currently playing context for this source
                self.controller._currently_playing_contexts.pop(source_id, None)

                self._autosave_current_profile()
                    
        except Exception as e:
            print(f"Error toggling remote source {source_id}: {e}")
            import traceback
            traceback.print_exc()

    def open_calculate_start_times_dialog(self):
        if self.dialog_open:
            return
        if self.get_selected_tab_playlist().type == Playlist.PlaylistType.API:
            messagebox.showerror("Error", "Cannot update start times for Remote Playlist")
            return
        if len(self.get_selected_tracks()) == 1:
            dialog = CalculateStartTimesDialog(self.controller.root)
            result = dialog.result
            track = self.get_selected_tracks()[0]
            track.play_time = result
            self.controller.playlist_service.update_play_times(track, self.get_selected_tab_playlist())
            self.reload_rows_in_selected_tab_without_intro_check()
        else:
            messagebox.showerror("Error", "Please select only one track")
        self.dialog_open = False

    def replace_from_macro_output_action(self, event=None):
        selected_tracks = self.get_selected_tracks()
        if not selected_tracks:
            messagebox.showinfo("Replace from Macro Output", "No track selected.", parent=self.controller.root)
            return
        if len(selected_tracks) > 1:
            messagebox.showerror("Error", "Please select only one track to replace.", parent=self.controller.root)
            return

        track = selected_tracks[0]
        current_playlist = self.get_selected_tab_playlist()
        track_index = current_playlist.tracks.index(track)

        track_dir = os.path.dirname(track.path)
        track_filename_no_ext, current_track_ext = os.path.splitext(os.path.basename(track.path))
        macro_output_dir = os.path.join(track_dir, "macro-output")

        if not os.path.exists(macro_output_dir) or not os.path.isdir(macro_output_dir):
            messagebox.showerror("Error", f"'macro-output' folder not found in {track_dir}", parent=self.controller.root)
            return

        found_file_in_macro = None
        for item_in_macro_dir in os.listdir(macro_output_dir):
            item_in_macro_path = os.path.join(macro_output_dir, item_in_macro_dir)
            if os.path.isfile(item_in_macro_path):
                macro_file_basename_no_ext, _ = os.path.splitext(item_in_macro_dir)
                if macro_file_basename_no_ext == track_filename_no_ext:
                    found_file_in_macro = item_in_macro_dir
                    break
        
        if not found_file_in_macro:
            messagebox.showinfo("Replace from Macro Output", 
                                f"No file matching '{track_filename_no_ext}.*' found in '{macro_output_dir}'.", 
                                parent=self.controller.root)
            return

        source_file_path = os.path.join(macro_output_dir, found_file_in_macro)
        # The destination path will be the original track's directory, but with the new filename (which might have a new extension)
        destination_path = os.path.join(track_dir, found_file_in_macro)
        original_track_path_before_move = track.path # Store original path

        try:
            # Move the new file into place. shutil.move will overwrite if destination_path is identical to an existing file.
            shutil.move(source_file_path, destination_path)

            # If the new file's path (destination_path) is different from the original track's path
            # (e.g., different extension), and the original file still exists, remove the original file.
            if destination_path != original_track_path_before_move and os.path.exists(original_track_path_before_move):
                os.remove(original_track_path_before_move)
            # If the macro-output folder is empty after moving the file, delete the folder
            if not os.listdir(macro_output_dir):
                os.rmdir(macro_output_dir)
            
            messagebox.showinfo("Success", f"Track '{os.path.basename(original_track_path_before_move)}' replaced with '{found_file_in_macro}'.", parent=self.controller.root)

            path_changed = False
            if destination_path != original_track_path_before_move:
                track.path = destination_path
                path_changed = True
            
            # Re-check metadata and existence for the track
            self.check_for_intros_and_if_exists(playlist=current_playlist, tracks=[track])
            self.reload_rows_in_selected_tab_without_intro_check()

            # If it's an Remote Playlist and path changed, need to update there too
            if current_playlist.type == Playlist.PlaylistType.API and path_changed:
                # This might need adjustment if the track identity relies on path heavily in API sync
                # For now, assume re-inserting with new path is okay
                self.remove_and_reinsert_track(track, track_index) # remove_and_reinsert_track might need to be more robust or a different method used

        except Exception as e:
            messagebox.showerror("Error", f"Failed to replace file: {e}", parent=self.controller.root)
