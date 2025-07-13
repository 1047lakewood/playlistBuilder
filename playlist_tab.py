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
    
    def perform_search(self, search_text):
        """Search for text in the tree view"""
        self.clear_search_results()
        
        if not search_text:
            return
            
        search_text = search_text.lower()
        self.search_results = []
        
        # Search through all rows
        for item_id in self.tree.get_children():
            match_found = False
            values = self.tree.item(item_id, 'values')
            
            # Convert all values to strings and check if any contain the search text
            for value in values:
                if str(value).lower().find(search_text) != -1:
                    match_found = True
                    break
                    
            if match_found:
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
            return
            
        try:
            # Get the current track from the API
            current_track = self.controller.playlist_service.api_manager.get_current_track()
            if not current_track:
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
        except Exception as e:
            print(f"Error updating current playing track: {str(e)}")
            
    def periodic_update_current_playing_track(self):
        """Periodically update the currently playing track"""
        if self.playlist.type == Playlist.PlaylistType.API:
            self.update_current_playing_track()
            # Schedule the next update
            self.after(2000, self.periodic_update_current_playing_track)
