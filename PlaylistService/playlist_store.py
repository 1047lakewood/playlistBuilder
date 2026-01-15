from models.playlist import Playlist
from PlaylistService import playlist_file_loader
from PlaylistService.api_playlist_manager import ApiPlaylistManager, RemotePlaylistRegistry
from typing import Optional


class PlaylistStore:
    def __init__(self):
        self.open_playlists: list[Playlist] = []
        
        # Multiple API playlists - keyed by source_id
        self._api_playlists: dict[str, Playlist] = {}
        
        # The registry manages all ApiPlaylistManager instances
        self.remote_registry = RemotePlaylistRegistry()

    @property
    def api_playlist(self) -> Optional[Playlist]:
        """Legacy property - returns first connected API playlist or None."""
        for playlist in self._api_playlists.values():
            return playlist
        return None
    
    def get_api_playlist(self, source_id: str) -> Optional[Playlist]:
        """Get an API playlist by its source ID."""
        return self._api_playlists.get(source_id)
    
    def get_all_api_playlists(self) -> dict[str, Playlist]:
        """Get all loaded API playlists."""
        return self._api_playlists.copy()
    
    def get_manager_for_playlist(self, playlist: Playlist) -> Optional[ApiPlaylistManager]:
        """Get the ApiPlaylistManager for a given playlist."""
        if playlist.type != Playlist.PlaylistType.API or not playlist.source_id:
            return None
        return self.remote_registry.get_manager(playlist.source_id)

    def load_playlist_from_path(self, path: str) -> Optional[Playlist]:
        """Load a local playlist from file."""
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

    def save_playlist(self, playlist: Playlist, file_path: str = None) -> bool:
        """Save a playlist to file."""
        if playlist is None:
            print("Playlist is None, cannot save")
            return False
        try:
            playlist_file_loader.save_playlist(playlist, file_path)
            return True
        except Exception as e:
            print(f"Failed to save playlist {playlist.path}: {e}")
            return False

    def close_playlist(self, playlist: Playlist) -> bool:
        """Close a playlist and remove it from open playlists."""
        if playlist is None:
            return False
        
        if playlist.type == Playlist.PlaylistType.API:
            source_id = playlist.source_id
            if source_id and source_id in self._api_playlists:
                del self._api_playlists[source_id]
                # Disconnect the manager
                manager = self.remote_registry.get_manager(source_id)
                if manager:
                    manager.disconnect()
            # Also remove from open_playlists if present
            if playlist in self.open_playlists:
                self.open_playlists.remove(playlist)
            return True
        
        if playlist in self.open_playlists:
            self.open_playlists.remove(playlist)
            return True
        return False

    # Remote Playlist loading and manipulation
    def load_api_playlist(self, source_id: str = None) -> Optional[Playlist]:
        """Load an API playlist from a specific source.
        
        Args:
            source_id: The ID of the remote source (e.g., "104.7", "88.7").
                      If None, uses the first available source.
        
        Returns:
            The loaded Playlist or None if loading failed.
        """
        # Determine which source to use
        if source_id is None:
            available = self.remote_registry.get_available_sources()
            if not available:
                print("No remote sources configured")
                return None
            source_id = available[0][0]
        
        manager = self.remote_registry.get_manager(source_id)
        if not manager:
            print(f"No manager found for source: {source_id}")
            return None
        
        # Try to load the playlist
        api_playlist = manager.reload_playlist()
        if api_playlist is None:
            print(f"Failed to load playlist from {source_id}: {manager.last_error}")
            return None
        
        api_playlist.type = Playlist.PlaylistType.API
        api_playlist.source_id = source_id
        
        # Store it
        self._api_playlists[source_id] = api_playlist
        
        # Also add to open_playlists if not already there
        # First, remove any existing playlist from this source
        existing = [p for p in self.open_playlists if p.source_id == source_id]
        for p in existing:
            self.open_playlists.remove(p)
        
        self.open_playlists.append(api_playlist)
        
        return api_playlist
    
    def reload_api_playlist(self, source_id: str) -> Optional[Playlist]:
        """Reload an existing API playlist from its source."""
        manager = self.remote_registry.get_manager(source_id)
        if not manager:
            print(f"No manager found for source: {source_id}")
            return None
        
        playlist = manager.reload_playlist()
        if playlist:
            playlist.source_id = source_id
            self._api_playlists[source_id] = playlist
            
            # Update in open_playlists
            for i, p in enumerate(self.open_playlists):
                if p.source_id == source_id:
                    self.open_playlists[i] = playlist
                    break
        
        return playlist
    
    def is_source_connected(self, source_id: str) -> bool:
        """Check if a specific source is connected."""
        manager = self.remote_registry.get_manager(source_id)
        return manager.is_connected if manager else False
    
    def get_source_status(self, source_id: str) -> tuple[str, str]:
        """Get the connection status for a source.
        
        Returns:
            Tuple of (status_name, status_message)
        """
        manager = self.remote_registry.get_manager(source_id)
        if manager:
            return (manager.status.value, manager.status_message)
        return ("unknown", "Source not found")
