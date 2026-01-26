import re
import os
from models.track import Track
from models.playlist import Playlist


class TreeInteractionController:
    def __init__(self, controller):
        self.controller = controller
        # this has to be a reference to the tree in the tab
        self.dragging_index = None
        self.dialog_open = False
        self.clipboard = []
    
    def get_tree(self): return self.controller.get_selected_tab().tree

    def index_of_selected_row(self): 
        tree = self.get_tree()
        return tree.index(tree.selection()[0])

    def get_selected_tracks(self):
        return self.controller.get_selected_rows()[2]

    def current_row_under_mouse(self, event):
        try: y = event.y    
        except: y = event.y_root - self.get_tree().winfo_rooty()
        return self.get_tree().identify_row(y)
    def current_row_under_mouse_index(self, event):
        row_id = self.current_row_under_mouse(event)
        if row_id == "": return len(self.get_tree().get_children()) - 1
        return self.get_tree().index(row_id)

    def button_down(self, event):
        try:
            self.dragging_index = self.current_row_under_mouse_index(event)
        except Exception as e:
            pass

    def dragged(self, event):
        if self.dragging_index is None:
            return
        try:
            current_row = self.current_row_under_mouse_index(event)
            if self.current_row_under_mouse(event) == "": return
            if self.dragging_index != current_row:
                self.move_tracks([self.dragging_index], current_row)
                self.get_tree().selection_set(self.current_row_under_mouse(event))
                self.dragging_index = current_row
        except Exception as e:
            print(e)
            pass

    def button_up(self, event):
        self.dragging_index = None

    def copy_tracks(self, event=None):
        if self.dialog_open: return
        self.clipboard = self.get_selected_tracks()
    
    def cut_tracks(self, event=None):
        if self.dialog_open: return
        self.clipboard = self.get_selected_tracks()
        self.delete_tracks(tracks=self.get_selected_tracks())

        self.reload_rows_in_selected_tab_without_intro_check()

    def delete_tracks(self, event=None, tracks=None):
        if tracks == None:
            tracks = self.get_selected_tracks()
        
        playlist = self.controller.get_selected_tab_playlist()
        track_indices = [playlist.tracks.index(track) for track in tracks]
        playlist.remove_tracks(tracks)
        self.reload_rows_in_selected_tab_without_intro_check()
        if playlist.type == Playlist.PlaylistType.API:
            manager = self.controller.playlist_service.get_api_manager_for_playlist(playlist)
            if manager:
                manager.remove_tracks([i + 1 for i in track_indices])

        
    def paste_tracks(self, event=None):
        if len(self.clipboard) == 0 or self.dialog_open:
            return
        playlist = self.controller.get_selected_tab_playlist()
        selected_indexes = self.controller.get_selected_rows()[1]
        paste_index = selected_indexes[-1] + 1 if selected_indexes else len(playlist.tracks)
        new_tracks = [track.copy() for track in self.clipboard]
        playlist.add_tracks(new_tracks, paste_index)
        self.reload_rows_in_selected_tab_without_intro_check()
        self.select_row_at_index([i for i in range(paste_index, paste_index + len(new_tracks))])
        if playlist.type == Playlist.PlaylistType.API:
            manager = self.controller.playlist_service.get_api_manager_for_playlist(playlist)
            if manager:
                manager.insert_tracks(new_tracks, paste_index + 1)
    def move_tracks(self, from_index, to_index):
        playlist = self.controller.get_selected_tab_playlist()
        playlist.move_tracks(from_index, to_index)
        self.reload_rows_in_selected_tab_without_intro_check()
        if playlist.type == Playlist.PlaylistType.API:
            manager = self.controller.playlist_service.get_api_manager_for_playlist(playlist)
            if manager:
                manager.move_tracks([i + 1 for i in from_index], to_index + 1)
    
    def hover_with_files(self, event):
        self.select_row_at_index([self.current_row_under_mouse_index(event)])
    def dropped_files_in_tab(self, event):
        files = re.findall(r"\{(.+?)\}", event.data)
        files = [file.replace("/", "\\") for file in files]
        
        # Filter for supported audio file extensions
        supported_extensions = ['.mp3', '.wav', '.wma', '.m4a', '.mp4', '.aac', '.flac', '.ogg']
        valid_files = []
        
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in supported_extensions:
                valid_files.append(file)
            else:
                print(f"Skipping unsupported file format: {file}")
        
        if not valid_files:
            print("No supported audio files found in the dropped files.")
            return
            
        # see where the files were dropped
        tree = self.get_tree()
        row_index = self.current_row_under_mouse_index(event) + 1
        
        # create tracks from files
        tracks = [Track(file) for file in valid_files]
        self.controller.playlist_service.update_track_metadata(tracks)
        
        # add tracks to playlist and reload rows
        playlist = self.controller.get_selected_tab_playlist()
        playlist.add_tracks(tracks, row_index)

        self.reload_rows_in_selected_tab_without_intro_check()
        if playlist.type == Playlist.PlaylistType.API:
            manager = self.controller.playlist_service.get_api_manager_for_playlist(playlist)
            if manager:
                manager.insert_tracks(tracks, row_index + 1)
        self.select_row_at_index([i for i in range(row_index, row_index + len(files))])
    
    def reload_rows_in_selected_tab_without_intro_check(self):
        self.controller.controller_actions.reload_rows_in_selected_tab_without_intro_check()
    
    def select_row_at_index(self, indexes):
        tree = self.get_tree()
        tree.selection_set([tree.get_children()[i] for i in indexes])