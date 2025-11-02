from models.playlist import Playlist
from models.track import Track
from PlaylistService.api_playlist_manager import ApiPlaylistManager

class PlaylistEditor:
    api_manager: ApiPlaylistManager
    def __init__(self, api_manager):
        self.api_manager = api_manager

    def add_track_to_playlist(self, playlist, track, insert_index = None):
        if insert_index is None:
            insert_index = len(playlist.tracks)
        if playlist.type == Playlist.PlaylistType.API:
            self.api_manager.add_track_to_playlist(track, insert_index)
        else:
            playlist.add_track(track, insert_index)

    def add_tracks_to_playlist(self, playlist, tracks, insert_index = None):
        if insert_index is None:
            insert_index = len(playlist.tracks)
        for track in tracks:
            new_insert_index = insert_index + tracks.index(track)
            self.add_track_to_playlist(playlist, track, new_insert_index)

    def remove_track_from_playlist(self, playlist, track):
        track_index = playlist.tracks.index(track)
        if playlist.type == Playlist.PlaylistType.API:
            self.api_manager.remove_track_from_playlist(track_index + 1)
        else:
            playlist.remove_track(track)

    def remove_tracks_from_playlist(self, playlist, tracks):
        track_indices = [playlist.tracks.index(track) for track in tracks]
        if playlist.type == Playlist.PlaylistType.API:  
            self.api_manager.remove_tracks_from_playlist(track_indices)
        else:
            playlist.remove_tracks(tracks)

    def move_tracks_in_playlist(self, playlist, track_indices: list[int], new_index: int):
        playlist.move_tracks(track_indices, new_index)