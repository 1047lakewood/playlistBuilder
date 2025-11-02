from tkinter import ttk, Frame
from tkinterdnd2 import TkinterDnD, DND_FILES
from PlaylistService import playlist_service
import utils
from models.playlist import Playlist
from typing import List
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

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.callbacks["drop_files_in_tab"])
        self.dnd_bind('<<DropPosition>>', self.callbacks["hover_with_files"])
    
        self.context_menu = PlaylistTabContextMenu(self)

        # Create a container frame for the tree and search frame
        self.container = Frame(self)
        self.container.pack(fill="both", expand=True)

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
        if self.playlist.type == Playlist.PlaylistType.API:
            self.update_current_playing_track()
            # Schedule periodic updates every 2 seconds
            self.after(2000, self.periodic_update_current_playing_track)

    def is_empty(self):
        return len(self.playlist.tracks) == 0
   
    def get_selected_row_indexes(self) -> List[int]:
        indexes = []
        for row in self.tree.selection():
            if row == "":
                continue
            indexes.append(self.tree.index(row))
        return indexes

    
        
    def reload_rows(self):
        playlist = self.playlist
        
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
            
            # If this is the currently playing track, highlight it
            if path == currently_playing_path:
                tags.append("currently_playing")
                self.current_playing_track_id = item_id
                
            self.tree.item(item_id, tags=tuple(tags))
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
            # Get the current track from the API
            current_track = self.controller.playlist_service.api_manager.get_current_track()
            if not current_track:
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

            # Find the track in the tree view
            found_item_id = None
            for item_id in self.tree.get_children():
                values = self.tree.item(item_id, 'values')
                path = values[6] if len(values) > 6 else ""
                if path == current_track.path:
                    found_item_id = item_id
                    break

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
                    # Ensure the track is visible and focused if this tab is currently selected
                    # self.tree.see(found_item_id) # Disabled scrolling to playing track
                    
                    # Check if this tab is currently selected
                    # if self.controller.notebook_view.get_selected_tab() == self: # Disabled selection/focus
                        # Focus on the currently playing track
                        # self.tree.selection_set(found_item_id) # Disabled selection/focus
                        # self.tree.focus(found_item_id) # Disabled selection/focus
                    
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
            self.after(2000, self.periodic_update_current_playing_track)

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