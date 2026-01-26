from tkinter import ttk, Frame, Label
from tkinterdnd2 import TkinterDnD, DND_FILES
from PlaylistService import playlist_service
from PlaylistService.api_playlist_manager import ConnectionStatus
from PlaylistService.playlist_diff import PlaylistDiff
import utils
from models.playlist import Playlist
from models.track import Track
from typing import List, Optional
import os
from playlist_tab_subviews import PlaylistTabTreeView, PlaylistTabContextMenu, SearchFrame



class PlaylistTabView(ttk.Frame):

    def __init__(self, parent, controller, playlist: Playlist, title:str, callbacks: dict):
        super().__init__(parent)
        parent.add(self, text=title)
        self.controller = controller
        self.playlist = playlist
        self.title = title
        self.callbacks = callbacks
        self.current_playing_track_id = None
        
        # Connection status tracking for API playlists
        self._connection_status = ConnectionStatus.DISCONNECTED
        self._is_api_playlist = playlist.type == Playlist.PlaylistType.API
        self._api_manager = None
        self._currently_playing_job = None

        # Auto-reload interaction guarding
        self._user_is_interacting = False
        self._pending_playlist_update: Optional[Playlist] = None
        self._interaction_timeout_job = None
        self._auto_reload_enabled = False

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.callbacks["drop_files_in_tab"])
        self.dnd_bind('<<DropPosition>>', self.callbacks["hover_with_files"])
    
        self.context_menu = PlaylistTabContextMenu(self)

        # Create a container frame for the tree and search frame
        self.container = Frame(self)
        self.container.pack(fill="both", expand=True)
        
        # Connection status bar (for API playlists) - initially hidden
        self._status_bar_frame: Optional[Frame] = None
        self._status_label: Optional[Label] = None
        self._reconnect_btn: Optional[ttk.Button] = None
        
        if self._is_api_playlist:
            self._create_status_bar()

        self.tree = PlaylistTabTreeView(self.container, callbacks)
        self.tree.bind("<Button-3>", lambda event: self.context_menu.show(event))
        self.tree.pack(side="top", fill="both", expand=True)

        # Search frame (initially hidden)
        self.search_frame = None
        self.search_results = []
        self.current_match_index = -1

        self.dragging_index = None
        # get playlist data
        self.reload_rows()
        
        # If this is an Remote Playlist, start checking for the currently playing track
        if self._is_api_playlist:
            self._register_status_callback()
            self.update_current_playing_track()
            # Schedule periodic updates every 2 seconds
            self._currently_playing_job = self.after(2000, self.periodic_update_current_playing_track)

    def _cleanup_remote_resources(self):
        """Stop background timers/subscriptions that can outlive the tab being visible."""
        # Cancel periodic currently-playing polling
        if self._currently_playing_job is not None:
            try:
                self.after_cancel(self._currently_playing_job)
            except Exception:
                pass
            self._currently_playing_job = None

        # Cancel any pending disconnect UI timer
        if hasattr(self, "_disconnect_timer") and self._disconnect_timer:
            try:
                self.after_cancel(self._disconnect_timer)
            except Exception:
                pass
            self._disconnect_timer = None

        # Cancel any pending interaction timeout
        if self._interaction_timeout_job is not None:
            try:
                self.after_cancel(self._interaction_timeout_job)
            except Exception:
                pass
            self._interaction_timeout_job = None

        # Stop auto-reload and unsubscribe from reload callbacks
        try:
            if self._api_manager:
                self._api_manager.stop_auto_reload()
                self._api_manager.remove_reload_callback(self._on_playlist_reloaded)
                self._api_manager.remove_status_callback(self._on_connection_status_change)
        except Exception:
            pass
        self._api_manager = None
        self._auto_reload_enabled = False
        self._pending_playlist_update = None

    def destroy(self):
        # Ensure we don't keep updating "Now Playing" after the tab is closed/disconnected.
        try:
            self._cleanup_remote_resources()
        finally:
            super().destroy()
    
    def _create_status_bar(self):
        """Create the connection status bar for API playlists."""
        self._status_bar_frame = Frame(self.container, bg="#fff3cd", height=32)
        
        self._status_label = Label(
            self._status_bar_frame,
            text="⟳ Connecting...",
            bg="#fff3cd",
            fg="#856404",
            font=("Segoe UI", 9),
            anchor="w",
            padx=10
        )
        self._status_label.pack(side="left", fill="x", expand=True)
        
        self._reconnect_btn = ttk.Button(
            self._status_bar_frame,
            text="Reconnect",
            command=self._attempt_reconnect,
            width=10
        )
        # Don't pack reconnect button initially - only shown on disconnect
        
        # Initially hidden - will show if disconnected
        # self._status_bar_frame.pack(side="top", fill="x", pady=(0, 2))
    
    def _register_status_callback(self):
        """Register for connection status updates."""
        if not self._is_api_playlist or not self.playlist.source_id:
            return
        self.ensure_manager_subscription()

    def ensure_manager_subscription(self):
        """Ensure we're subscribed to the current ApiPlaylistManager instance.

        This self-heals cases where the registry recreated managers (or the tab
        was created before a manager existed).
        """
        if not self._is_api_playlist or not self.playlist.source_id:
            return

        manager = self.controller.playlist_service.get_api_manager(self.playlist.source_id)
        if not manager:
            return

        if self._api_manager is not manager:
            # Unsubscribe from old manager (if any)
            try:
                if self._api_manager:
                    self._api_manager.remove_status_callback(self._on_connection_status_change)
            except Exception:
                pass

            self._api_manager = manager
            try:
                manager.add_status_callback(self._on_connection_status_change)
            except Exception:
                pass

        # Sync UI immediately to manager's current state
        try:
            status = manager.status
            message = manager.status_message
            if manager.is_connected or manager.playlist is not None:
                status = ConnectionStatus.CONNECTED
            self._update_status_display(status, message)
        except Exception:
            pass
    
    def _on_connection_status_change(self, manager, status: ConnectionStatus, message: str):
        """Handle connection status changes."""
        # Schedule UI update on main thread
        self.after(0, lambda: self._update_status_display(status, message))
    
    def _update_status_display(self, status: ConnectionStatus, message: str = ""):
        """Update the status bar display based on connection status."""
        old_status = self._connection_status
        self._connection_status = status

        if not self._status_bar_frame:
            return

        if status == ConnectionStatus.CONNECTED:
            # Cancel any pending disconnect timer
            if hasattr(self, '_disconnect_timer') and self._disconnect_timer:
                self.after_cancel(self._disconnect_timer)
                self._disconnect_timer = None
            
            # Hide status bar when connected
            if self._status_bar_frame.winfo_ismapped():
                self._status_bar_frame.pack_forget()
                self._reconnect_btn.pack_forget()
            # Update tab title to show connected
            self._update_tab_title(connected=True)

        elif status == ConnectionStatus.CONNECTING:
            # Don't show status bar for connecting state - too intrusive during normal polling
            # Keep the current tab title state
            pass

        elif status == ConnectionStatus.DISCONNECTED:
            # Only show disconnected status after a brief delay to avoid flashing
            if not hasattr(self, '_disconnect_timer'):
                self._disconnect_timer = None

            # Cancel any existing timer
            if self._disconnect_timer:
                self.after_cancel(self._disconnect_timer)

            # Schedule to show disconnected status after 3 seconds of persistent disconnection
            self._disconnect_timer = self.after(3000, lambda: self._show_disconnected_status())

        elif status in (ConnectionStatus.ERROR, ConnectionStatus.TIMEOUT):
            # Cancel any disconnect timer
            if hasattr(self, '_disconnect_timer') and self._disconnect_timer:
                self.after_cancel(self._disconnect_timer)
                self._disconnect_timer = None

            # Show error status immediately
            self._status_bar_frame.configure(bg="#f8d7da")
            error_icon = "⚠" if status == ConnectionStatus.ERROR else "⏱"
            self._status_label.configure(
                text=f"{error_icon} {message or 'Connection failed'}",
                bg="#f8d7da",
                fg="#721c24"
            )
            self._reconnect_btn.pack(side="right", padx=5, pady=2)
            if not self._status_bar_frame.winfo_ismapped():
                self._status_bar_frame.pack(side="top", fill="x", pady=(0, 2), before=self.tree)
            self._update_tab_title(connected=False)

    def _show_disconnected_status(self):
        """Show the disconnected status bar after delay."""
        if self._connection_status == ConnectionStatus.DISCONNECTED:
            self._status_bar_frame.configure(bg="#e2e3e5")
            self._status_label.configure(
                text="○ Disconnected",
                bg="#e2e3e5",
                fg="#383d41"
            )
            self._reconnect_btn.pack(side="right", padx=5, pady=2)
            if not self._status_bar_frame.winfo_ismapped():
                self._status_bar_frame.pack(side="top", fill="x", pady=(0, 2), before=self.tree)
            self._update_tab_title(connected=False)
    
    def _update_tab_title(self, connected: bool):
        """Update the tab title to indicate connection status."""
        notebook = self.master
        if not notebook:
            return
        
        base_title = self.title.replace(" ●", "").replace(" ○", "").strip()
        if connected:
            new_title = f"{base_title} ●"
        else:
            new_title = f"{base_title} ○"
        
        try:
            notebook.tab(self, text=new_title)
        except Exception:
            pass
    
    def _attempt_reconnect(self):
        """Attempt to reconnect to the remote source."""
        if not self._is_api_playlist or not self.playlist.source_id:
            return
        
        self._update_status_display(ConnectionStatus.CONNECTING, "Reconnecting...")
        
        # Run reconnection in background thread
        import threading
        def reconnect():
            try:
                playlist = self.controller.playlist_service.reload_api_playlist(self.playlist.source_id)
                if playlist:
                    self.playlist.tracks = list(playlist.tracks)
                    self.after(0, self.reload_rows)
            except Exception as e:
                print(f"Reconnection failed: {e}")
        
        thread = threading.Thread(target=reconnect, daemon=True)
        thread.start()
    
    @property
    def is_connected(self) -> bool:
        """Check if this tab's playlist source is connected."""
        if not self._is_api_playlist:
            return True  # Local playlists are always "connected"
        return self._connection_status == ConnectionStatus.CONNECTED

    # --- Auto-reload and interaction guarding ---

    def start_auto_reload(self, interval_seconds: int = 30):
        """Start auto-reload for this tab's remote playlist."""
        if not self._is_api_playlist or not self.playlist.source_id:
            return

        manager = self.controller.playlist_service.get_api_manager(self.playlist.source_id)
        if not manager:
            return

        # Register for reload notifications
        manager.add_reload_callback(self._on_playlist_reloaded)
        manager.start_auto_reload(interval_seconds)
        self._auto_reload_enabled = True

    def _on_playlist_reloaded(self, new_playlist: Playlist):
        """Called from background thread when playlist is reloaded.

        Schedules UI update on main thread.
        """
        # Schedule UI update on main thread
        self.after(0, lambda: self._handle_playlist_update(new_playlist))

    def _handle_playlist_update(self, new_playlist: Playlist):
        """Handle playlist update on main thread.

        If user is interacting, queue the update for later.
        """
        if self._user_is_interacting:
            # Queue the update for when user stops interacting
            self._pending_playlist_update = new_playlist
            return

        self._apply_playlist_update(new_playlist)

    def _apply_playlist_update(self, new_playlist: Playlist):
        """Apply a playlist update with full UI refresh and state preservation.

        Uses reload_rows() instead of diff-based updates to ensure:
        - Times stay in sync (all tracks get recalculated start times)
        - Artist intro dots are preserved (check_for_intros_and_exists is called)
        """
        # Save current state
        selection = self.tree.selection()
        selected_paths = []
        for item_id in selection:
            try:
                values = self.tree.item(item_id, 'values')
                if len(values) > 6:
                    selected_paths.append(values[6])
            except Exception:
                pass

        yview = self.tree.yview()
        scroll_position = yview[0] if yview else 0.0

        # Save currently playing track path
        currently_playing_path = None
        if self.current_playing_track_id:
            try:
                values = self.tree.item(self.current_playing_track_id, 'values')
                currently_playing_path = values[6] if len(values) > 6 else None
            except Exception:
                pass

        # Calculate play times for the new playlist (same as initial load)
        # This ensures times are calculated correctly instead of using raw server STARTTIME
        self.controller.playlist_service.create_day_start_times_playlist(new_playlist)

        # Check for intros and file existence (fixes artist dots disappearing after auto-reload)
        self.controller.playlist_service.check_for_intros_and_exists(new_playlist)

        # Update the playlist tracks
        self.playlist.tracks = list(new_playlist.tracks)

        # Full UI refresh (reliable sync for times and intro dots)
        # Using reload_rows() instead of diff-based update ensures UI always matches model
        self.reload_rows()

        # Restore scroll position
        self.tree.update_idletasks()
        self.tree.yview_moveto(scroll_position)

        # Restore selection by path
        self._restore_selection_by_paths(selected_paths)

        # Restore currently playing highlight
        if currently_playing_path:
            self._restore_currently_playing(currently_playing_path)

    def _restore_selection_by_paths(self, paths: List[str]):
        """Restore selection based on track paths."""
        if not paths:
            return

        items_to_select = []
        for item_id in self.tree.get_children():
            try:
                values = self.tree.item(item_id, 'values')
                if len(values) > 6 and values[6] in paths:
                    items_to_select.append(item_id)
            except Exception:
                pass

        if items_to_select:
            self.tree.selection_set(items_to_select)

    def _restore_currently_playing(self, track_path: str):
        """Restore the currently playing highlight after diff update."""
        for item_id in self.tree.get_children():
            try:
                values = self.tree.item(item_id, 'values')
                if len(values) > 6 and values[6] == track_path:
                    current_tags = list(self.tree.item(item_id, 'tags'))
                    if 'currently_playing' not in current_tags:
                        current_tags.append('currently_playing')
                    self.tree.item(item_id, tags=tuple(current_tags))
                    self.current_playing_track_id = item_id
                    return
            except Exception:
                pass

    def mark_user_interacting(self):
        """Mark that user is actively interacting with the view.

        Call this from mouse event handlers to defer auto-reload updates.
        """
        self._user_is_interacting = True

        # Cancel any existing timeout
        if self._interaction_timeout_job:
            try:
                self.after_cancel(self._interaction_timeout_job)
            except Exception:
                pass

        # Set timeout to clear interaction flag after 500ms of no activity
        self._interaction_timeout_job = self.after(500, self._clear_interaction_flag)

    def _clear_interaction_flag(self):
        """Clear the interaction flag and apply any pending updates."""
        self._user_is_interacting = False
        self._interaction_timeout_job = None

        # Apply any pending update
        if self._pending_playlist_update:
            pending = self._pending_playlist_update
            self._pending_playlist_update = None
            self._apply_playlist_update(pending)

    def is_empty(self):
        return len(self.playlist.tracks) == 0
   
    def get_selected_row_indexes(self) -> List[int]:
        indexes = []
        for row in self.tree.selection():
            if row == "":
                continue
            indexes.append(self.tree.index(row))
        return indexes

    
        
    def reload_rows(self, preserve_scroll: bool = False):
        playlist = self.playlist

        # Save scroll position and selection if requested
        scroll_position = 0.0
        selected_indexes = []
        if preserve_scroll:
            try:
                yview = self.tree.yview()
                scroll_position = yview[0] if yview else 0.0
                selected_indexes = self.get_selected_row_indexes()
            except Exception:
                pass
        
        # Store the path of the currently playing track before clearing the tree
        currently_playing_path = None
        if self.current_playing_track_id:
            values = self.tree.item(self.current_playing_track_id, 'values')
            currently_playing_path = values[6] if len(values) > 6 else None
        
        self.tree.delete(*self.tree.get_children())
        self.current_playing_track_id = None  # Reset the current playing track ID
        
        tracks = playlist.tracks
        if tracks and tracks[0].play_time is not None and playlist.type != Playlist.PlaylistType.API:
            self.controller.playlist_service.update_play_times(tracks[0], playlist)
        is_api_raw = self.check_for_no_large_play_time(playlist)
        if is_api_raw:
            pass
        found_currently_playing = False
        for i, track in enumerate(tracks):
            rowNumber = i + 1

            if playlist.type == Playlist.PlaylistType.API:
                if is_api_raw:
                    start_time = utils.format_play_time(track.play_time, type="api_raw")
                else:
                    start_time = utils.format_play_time(track.play_time)
            else:
                start_time = utils.format_play_time(track.play_time)
            
            has_intro = "•" if track.has_intro else ""
            artist = track.artist
            title = track.title
            duration = utils.format_duration(track.duration) if track.duration is not None else ""
            path = track.path
            # Check if file exists
            file_exists = True if track.exists else False

            # Insert row with appropriate tag if file doesn't exist
            item_id = self.tree.insert("", "end", values=(rowNumber, start_time, has_intro, artist, title, duration, path))
            
            # Apply appropriate tags
            tags = []
            # Apply alternating row colors
            if i % 2 == 0:
                tags.append("even_row")
            else:
                tags.append("odd_row")
                
            if not file_exists:
                tags.append("missing_file")
            
            # If this is the currently playing track, highlight it (only first match for duplicates)
            if path == currently_playing_path and not found_currently_playing:
                tags.append("currently_playing")
                self.current_playing_track_id = item_id
                found_currently_playing = True
                
            self.tree.item(item_id, tags=tuple(tags))

        # Restore scroll position and selection if requested
        if preserve_scroll:
            self.tree.update_idletasks()
            if scroll_position > 0.0:
                self.tree.yview_moveto(scroll_position)
            if selected_indexes:
                children = self.tree.get_children()
                items_to_select = [children[i] for i in selected_indexes if i < len(children)]
                if items_to_select:
                    self.tree.selection_set(items_to_select)

    def apply_diff(self, diff: PlaylistDiff, new_tracks: List[Track]):
        """Apply a diff to the TreeView without full rebuild.

        Must be called on main thread.
        """
        if diff.is_identical:
            return

        # Process changes - note: deletions are in reverse index order from diff.compute()
        for change in diff.changes:
            if change.action == 'delete':
                self._delete_row_at_index(change.index)
            elif change.action == 'insert':
                self._insert_row_at_index(change.index, change.track)
            elif change.action == 'update':
                self._update_row_at_index(change.index, change.track)

        # Renumber all rows and fix alternating colors after changes
        self._renumber_rows()

        # Update the playlist tracks reference
        self.playlist.tracks = list(new_tracks)

    def _delete_row_at_index(self, index: int):
        """Delete a single row from TreeView."""
        children = self.tree.get_children()
        if 0 <= index < len(children):
            item_id = children[index]
            # Check if this was the currently playing track
            if item_id == self.current_playing_track_id:
                self.current_playing_track_id = None
            self.tree.delete(item_id)

    def _insert_row_at_index(self, index: int, track: Track):
        """Insert a single row into TreeView at specified index."""
        children = self.tree.get_children()

        # Determine insert position
        if index >= len(children):
            position = "end"
        else:
            position = index

        # Format track data
        row_values = self._format_track_for_row(index + 1, track)

        # Insert
        item_id = self.tree.insert("", position, values=row_values)
        self._apply_row_tags(item_id, index, track)

    def _update_row_at_index(self, index: int, track: Track):
        """Update an existing row's values without deleting it."""
        children = self.tree.get_children()
        if 0 <= index < len(children):
            item_id = children[index]
            row_values = self._format_track_for_row(index + 1, track)
            self.tree.item(item_id, values=row_values)
            self._apply_row_tags(item_id, index, track)

    def _format_track_for_row(self, row_number: int, track: Track) -> tuple:
        """Format a track into TreeView row values."""
        is_api_raw = self.check_for_no_large_play_time(self.playlist)

        if self.playlist.type == Playlist.PlaylistType.API:
            if is_api_raw:
                start_time = utils.format_play_time(track.play_time, type="api_raw")
            else:
                start_time = utils.format_play_time(track.play_time)
        else:
            start_time = utils.format_play_time(track.play_time)

        has_intro = "•" if track.has_intro else ""
        duration = utils.format_duration(track.duration) if track.duration is not None else ""

        return (row_number, start_time, has_intro, track.artist, track.title, duration, track.path)

    def _apply_row_tags(self, item_id: str, index: int, track: Track):
        """Apply appropriate tags to a row."""
        tags = []

        # Alternating row colors
        if index % 2 == 0:
            tags.append("even_row")
        else:
            tags.append("odd_row")

        # Missing file
        if not track.exists:
            tags.append("missing_file")

        # Preserve currently playing highlight if this track matches
        if self.current_playing_track_id:
            try:
                current_values = self.tree.item(self.current_playing_track_id, 'values')
                if len(current_values) > 6 and current_values[6] == track.path:
                    tags.append("currently_playing")
                    self.current_playing_track_id = item_id
            except Exception:
                pass

        self.tree.item(item_id, tags=tuple(tags))

    def _renumber_rows(self):
        """Update row numbers and alternating colors after insertions/deletions."""
        for i, item_id in enumerate(self.tree.get_children()):
            values = list(self.tree.item(item_id, 'values'))
            values[0] = i + 1
            self.tree.item(item_id, values=tuple(values))

            # Fix alternating row colors
            current_tags = list(self.tree.item(item_id, 'tags'))
            # Remove old even/odd tags
            current_tags = [t for t in current_tags if t not in ('even_row', 'odd_row')]
            # Add correct tag
            if i % 2 == 0:
                current_tags.append('even_row')
            else:
                current_tags.append('odd_row')
            self.tree.item(item_id, tags=tuple(current_tags))

    def check_for_no_large_play_time(self, playlist: Playlist):
        for track in playlist.tracks:
            if track.play_time is None:
                continue
            if track.play_time > 86400:
                return False
        return True
    def toggle_search(self):
        """Show or hide the search frame"""
        if self.search_frame:
            self.close_search()
        else:
            self.show_search()
    
    def show_search(self):
        """Show the search frame"""
        if not self.search_frame:
            self.search_frame = SearchFrame(
                self.container, 
                self.perform_search,
                self.close_search,
                self.next_match,
                self.prev_match
            )
            self.search_frame.pack(side="bottom", fill="x", pady=(5, 0))
    
    def close_search(self):
        """Close the search frame"""
        if self.search_frame:
            self.search_frame.destroy()
            self.search_frame = None
            # Clear any highlighting
            self.clear_search_results()
    
    def perform_search(self, search_text="", search_number=""):
        """Search for text and/or number in the tree view"""
        self.clear_search_results()
        
        if not search_text and not search_number:
            return
        
        search_text = search_text.lower() if search_text else ""
        search_number = search_number.strip() if search_number else ""
        self.search_results = []
        
        # Search through all rows
        for item_id in self.tree.get_children():
            number_match = True
            text_match = True
            values = self.tree.item(item_id, 'values')
            
            # Check number search (matches against first column, index 0)
            if search_number:
                if len(values) > 0:
                    number_str = str(values[0]).strip()
                    number_match = (number_str == search_number or number_str.find(search_number) != -1)
                else:
                    number_match = False
            
            # Check text search (matches against all other columns, or all if no number search)
            if search_text:
                text_match = False
                # If number search is active, only search other columns; otherwise search all
                start_idx = 1 if search_number else 0
                for i in range(start_idx, len(values)):
                    if str(values[i]).lower().find(search_text) != -1:
                        text_match = True
                        break
            
            # Match if both conditions are met (or if only one search is active, that one matches)
            if number_match and text_match:
                self.search_results.append(item_id)
                self.tree.item(item_id, tags=("search_match",))
        
        # If we found matches, highlight the first one
        if self.search_results:
            self.current_match_index = 0
            self.highlight_current_match()
            
    def highlight_current_match(self, _recursion_depth=0):
        """Highlight the current match. If item is stale, re-search. If highlight fails, try next."""
        MAX_RECURSION_DEPTH = 10 # Safeguard against infinite loops

        if not self.search_results:
            # print("highlight_current_match: No search results. Clearing.")
            self.clear_search_results()
            return

        if _recursion_depth > MAX_RECURSION_DEPTH:
            print("highlight_current_match: Max recursion depth reached. Clearing search.")
            self.clear_search_results()
            return

        # Ensure current_match_index is valid for the current search_results list
        if not (0 <= self.current_match_index < len(self.search_results)):
            # This can happen if search_results was cleared or index became invalid
            # print(f"highlight_current_match: Invalid current_match_index {self.current_match_index} for {len(self.search_results)} results. Resetting or clearing.")
            if self.search_results: # If there are still results, try from the start
                self.current_match_index = 0 
            else: # No results left
                self.clear_search_results()
                return
        
        item_id = self.search_results[self.current_match_index]

        if not self.tree.exists(item_id):
            print(f"Search item {item_id} is stale. Attempting to re-search.")
            if self.search_frame and hasattr(self.search_frame, 'search_var'):
                current_search_term = self.search_frame.search_var.get()
                if current_search_term:
                    # perform_search will clear old results and highlight the new first match (if any)
                    self.perform_search(current_search_term) 
                else:
                    # No search term, so can't re-search. Clear current results.
                    self.clear_search_results()
            else:
                # No search frame or var, cannot re-search. Clear current results.
                self.clear_search_results()
            return # Exit after attempting re-search or clearing

        # Item exists, try to highlight it
        try:
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
            
            current_tags = list(self.tree.item(item_id, 'tags'))
            if "search_current" not in current_tags:
                current_tags.append("search_current")
            if "search_match" not in current_tags:
                current_tags.append("search_match")
            self.tree.item(item_id, tags=tuple(current_tags))
            # print(f"Successfully highlighted {item_id}")
            return # Successfully highlighted

        except Exception as e:
            print(f"Error highlighting existing item {item_id}: {e}. Removing from results and trying next.")
            # Remove problematic item and try to highlight the next logical item
            self.search_results.pop(self.current_match_index)
            # The current_match_index now points to the *next* item in the modified list, or becomes out of bounds if it was the last.
            # No need to explicitly increment current_match_index before recursive call, as pop shifts subsequent elements.
            # highlight_current_match will re-validate index at the start.
            self.highlight_current_match(_recursion_depth + 1)
            return
        
    def next_match(self):
        """Move to the next match"""
        if not self.search_results:
            return
            
        # Reset highlighting of the (now old) current match
        if 0 <= self.current_match_index < len(self.search_results):
            item_id = self.search_results[self.current_match_index]
            if self.tree.exists(item_id):
                # Attempt to set tags back to just 'search_match' if it was current
                current_tags = list(self.tree.item(item_id, 'tags'))
                if "search_current" in current_tags:
                    current_tags.remove("search_current")
                    # Ensure 'search_match' remains if it was a search result
                    if "search_match" not in current_tags:
                        current_tags.append("search_match") # Should already be there
                    self.tree.item(item_id, tags=tuple(current_tags))
                elif "search_match" in current_tags: # If it was only a match, ensure it stays that way
                    self.tree.item(item_id, tags=("search_match",))
        
        # Move to next logical match index
        self.current_match_index = (self.current_match_index + 1) % len(self.search_results)
        self.highlight_current_match() # This will handle highlighting the new valid item
        
    def prev_match(self):
        """Move to the previous match"""
        if not self.search_results:
            return
            
        # Reset highlighting of the (now old) current match
        if 0 <= self.current_match_index < len(self.search_results):
            item_id = self.search_results[self.current_match_index]
            if self.tree.exists(item_id):
                # Attempt to set tags back to just 'search_match' if it was current
                current_tags = list(self.tree.item(item_id, 'tags'))
                if "search_current" in current_tags:
                    current_tags.remove("search_current")
                    if "search_match" not in current_tags:
                        current_tags.append("search_match")
                    self.tree.item(item_id, tags=tuple(current_tags))
                elif "search_match" in current_tags:
                    self.tree.item(item_id, tags=("search_match",))

        # Move to previous logical match index
        self.current_match_index = (self.current_match_index - 1 + len(self.search_results)) % len(self.search_results) # Ensure positive index before modulo
        self.highlight_current_match() # This will handle highlighting the new valid item
        
    def clear_search_results(self):
        """Clear all search highlighting"""
        # Reset all items to their original state
        for item_id in self.tree.get_children():
            # Check if it was a missing file
            values = self.tree.item(item_id, 'values')
            path = values[6] if len(values) > 6 else ""
            track = next((t for t in self.playlist.tracks if t.path == path), None)
            
            # Preserve currently playing highlight if applicable
            if item_id == self.current_playing_track_id:
                if track and not track.exists:
                    self.tree.item(item_id, tags=("missing_file", "currently_playing"))
                else:
                    self.tree.item(item_id, tags=("currently_playing",))
            else:
                if track and not track.exists:
                    self.tree.item(item_id, tags=("missing_file",))
                else:
                    self.tree.item(item_id, tags=())
                
        self.search_results = []
        self.current_match_index = -1
        
    def update_current_playing_track(self):
        """Update the UI to highlight the currently playing track"""
        if self.playlist.type != Playlist.PlaylistType.API:
            self.controller.notify_currently_playing(None, self, False)
            return

        try:
            # Keep status subscription accurate even if managers were reloaded.
            self.ensure_manager_subscription()

            # Get the API manager for this playlist's source
            manager = self.controller.playlist_service.get_api_manager_for_playlist(self.playlist)
            if not manager:
                self.controller.notify_currently_playing(None, self, False)
                return
            
            # Get the position of the currently playing track from the API
            current_track_pos = manager.get_current_track_pos()
            if current_track_pos is None:
                if self.current_playing_track_id:
                    try:
                        current_tags = list(self.tree.item(self.current_playing_track_id, 'tags'))
                        if "currently_playing" in current_tags:
                            current_tags.remove("currently_playing")
                        self.tree.item(self.current_playing_track_id, tags=tuple(current_tags))
                    except Exception:
                        pass
                    self.current_playing_track_id = None
                self.controller.notify_currently_playing(None, self, False)
                return

            # Find the track in the tree view by position (handles duplicates correctly)
            found_item_id = None
            current_track = None
            children = self.tree.get_children()
            if 0 <= current_track_pos < len(children):
                found_item_id = children[current_track_pos]
                if 0 <= current_track_pos < len(self.playlist.tracks):
                    current_track = self.playlist.tracks[current_track_pos]

            # If the currently playing track changed, update the highlighting
            if found_item_id != self.current_playing_track_id:
                # Remove highlight from previous track
                if self.current_playing_track_id:
                    # Get the current tags
                    current_tags = list(self.tree.item(self.current_playing_track_id, 'tags'))
                    if "currently_playing" in current_tags:
                        current_tags.remove("currently_playing")
                    self.tree.item(self.current_playing_track_id, tags=tuple(current_tags))

                # Add highlight to new track
                if found_item_id:
                    # Get the current tags
                    current_tags = list(self.tree.item(found_item_id, 'tags'))
                    if "currently_playing" not in current_tags:
                        current_tags.append("currently_playing")
                    self.tree.item(found_item_id, tags=tuple(current_tags))
                    
                # Update the current playing track ID
                self.current_playing_track_id = found_item_id

            if not found_item_id:
                self.controller.notify_currently_playing(current_track, self, False)
            else:
                self.controller.notify_currently_playing(current_track, self, True)
        except Exception as e:
            print(f"Error updating current playing track: {str(e)}")
            self.controller.notify_currently_playing(None, self, False)
            
    def periodic_update_current_playing_track(self):
        """Periodically update the currently playing track"""
        if self.playlist.type == Playlist.PlaylistType.API:
            self.update_current_playing_track()
            # Schedule the next update
            self._currently_playing_job = self.after(2000, self.periodic_update_current_playing_track)

    def scroll_to_track(self, track_path):
        """Scroll to and focus the first tree item matching the track path."""
        if not track_path:
            return

        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, 'values')
            path = values[6] if len(values) > 6 else ""
            if path == track_path:
                try:
                    self.tree.see(item_id)
                    self.tree.focus(item_id)

                    # Attempt to center the item within the viewport for better context
                    self.tree.update_idletasks()

                    total_items = len(self.tree.get_children())
                    if total_items <= 0:
                        return

                    try:
                        row_bbox = self.tree.bbox(item_id)
                    except Exception:
                        row_bbox = None

                    row_height = row_bbox[3] if row_bbox else 0
                    if row_height <= 0:
                        # Fallback if bbox failed (e.g., themed widgets sometimes return None)
                        row_height = 24

                    widget_height = max(1, self.tree.winfo_height())
                    visible_rows = max(1, widget_height // row_height)

                    item_index = self.tree.index(item_id)
                    top_index = max(0, min(total_items - visible_rows, item_index - visible_rows // 2))

                    if total_items > 0:
                        fraction = top_index / total_items
                        self.tree.yview_moveto(fraction)
                except Exception:
                    pass
                return
    
    def refresh_theme_colors(self):
        """Refresh theme colors for this tab's widgets."""
        # Refresh treeview colors
        if hasattr(self.tree, 'refresh_theme_colors'):
            self.tree.refresh_theme_colors()
        
        # Note: SearchFrame is created dynamically, so it will get
        # the new colors automatically when it's next created