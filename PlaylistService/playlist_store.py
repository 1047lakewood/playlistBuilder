from models.playlist import Playlist
from PlaylistService import playlist_file_loader

class PlaylistStore:
    def __init__(self, api_manager):
        self.open_playlists = []
        self.api_playlist = None
        self.api_manager = api_manager

    def load_playlist_from_path(self, path) -> Playlist:
        for playlist in self.open_playlists:
            if playlist.path == path:
                return playlist
        try:
            playlist = playlist_file_loader.load_playlist(path)
            self.open_playlists.append(playlist)
            return playlist
        except Exception as e:
            print(f"Failed to load playlist {path}: {e}")
            return None

    def save_playlist(self, playlist, file_path = None):

        if playlist is None:
            print(f"Playlist {playlist} not found")
            return False
        try:
            playlist_file_loader.save_playlist(playlist, file_path)
            return True
        except Exception as e:
            print(f"Failed to save playlist {playlist.path}: {e}")
            return False


    def close_playlist(self, playlist):
        if playlist.type == Playlist.PlaylistType.API:
            self.open_playlists.remove(self.api_playlist)
            self.api_playlist = None
            return True
        if playlist is None:
            print(f"Playlist {playlist} not found")
            return False
        self.open_playlists.remove(playlist)
        return True


    # Remote Playlist loading and manipulation
    def load_api_playlist(self):
        self.api_manager.reload_playlist()

        api_playlist = self.api_manager.playlist
        api_playlist.type = Playlist.PlaylistType.API

        self.api_playlist = api_playlist
        for playlist in self.open_playlists:
            if playlist.type == Playlist.PlaylistType.API:
                self.open_playlists.remove(playlist)
                break
        self.open_playlists.append(api_playlist)
        return api_playlist