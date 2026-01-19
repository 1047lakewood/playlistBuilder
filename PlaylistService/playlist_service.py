
from PlaylistService import playlist_store
from models import playlist
from models.playlist import Playlist
from PlaylistService.playlist_store import PlaylistStore
from PlaylistService.playlist_editor import PlaylistEditor
from PlaylistService.api_playlist_manager import ApiPlaylistManager, RemotePlaylistRegistry, ConnectionStatus
from PlaylistService.track_utils import TrackUtils
import app_config
from models.track import Track
from typing import List, Optional


class PlaylistServiceManager:
    def __init__(self):
        self.playlist_prefered_order = []

        # Use the new store that handles multiple API playlists
        self.store = PlaylistStore()
        
        # For backwards compatibility, provide access to a default manager
        # This will be the first available manager
        self._default_source_id: Optional[str] = None
        available = self.store.remote_registry.get_available_sources()
        if available:
            self._default_source_id = available[0][0]
        
        self.playlists = self.store.open_playlists
        self.intro_dir = app_config.get(["paths", "intros_dir"], "")
    
    @property
    def api_manager(self) -> Optional[ApiPlaylistManager]:
        """Legacy property - returns the default/first API manager."""
        if self._default_source_id:
            return self.store.remote_registry.get_manager(self._default_source_id)
        return None
    
    def get_api_manager(self, source_id: str) -> Optional[ApiPlaylistManager]:
        """Get the API manager for a specific source."""
        return self.store.remote_registry.get_manager(source_id)
    
    def get_api_manager_for_playlist(self, playlist: Playlist) -> Optional[ApiPlaylistManager]:
        """Get the API manager for a playlist."""
        return self.store.get_manager_for_playlist(playlist)
    
    def get_available_sources(self) -> List[tuple]:
        """Get list of available remote sources as (source_id, name) tuples."""
        return self.store.remote_registry.get_available_sources()

    # Playlist loading and saving
    def create_new_playlist(self) -> Playlist:
        """Create a new empty playlist."""
        return self.store.create_new_playlist()

    def load_playlist_from_path(self, path) -> Playlist:
        return self.store.load_playlist_from_path(path)

    def save_playlist(self, playlist, file_path=None):
        self.store.save_playlist(playlist, file_path)

    def close_playlist(self, playlist):
        self.store.close_playlist(playlist)

    # Remote Playlist loading
    def load_api_playlist(self, source_id: str = None) -> Optional[Playlist]:
        """Load an API playlist from a specific source."""
        api_playlist = self.store.load_api_playlist(source_id)
        if api_playlist:
            self.create_day_start_times_playlist(api_playlist)
        return api_playlist
    
    def reload_api_playlist(self, source_id: str = None) -> Optional[Playlist]:
        """Reload an API playlist."""
        if source_id is None:
            source_id = self._default_source_id
        if source_id is None:
            return None
        
        playlist = self.store.reload_api_playlist(source_id)
        if playlist:
            self.create_day_start_times_playlist(playlist)
        return playlist
    
    def close_api_playlist(self, source_id: str = None):
        """Close an API playlist."""
        if source_id is None:
            source_id = self._default_source_id
        if source_id:
            playlist = self.store.get_api_playlist(source_id)
            if playlist:
                self.store.close_playlist(playlist)
    
    def is_source_connected(self, source_id: str) -> bool:
        """Check if a source is connected."""
        return self.store.is_source_connected(source_id)
    
    def get_source_status(self, source_id: str) -> tuple[str, str]:
        """Get the status of a source."""
        return self.store.get_source_status(source_id)

    def update_playlist_metadata(self, playlist: Playlist):
        for track in playlist.tracks:
            TrackUtils.update_track_metadata(track)
    
    def update_track_metadata(self, tracks: List[Track]):
        for track in tracks:
            TrackUtils.update_track_metadata(track)
    
    def update_play_times(self, updated_track: Track, playlist: Playlist):
        if updated_track.play_time is None:
            print(f"in PlaylistServiceManager.update_play_times: play_time is None for {updated_track.title} by {updated_track.artist}")
        if updated_track.play_time < 0 or updated_track.play_time > 604800:
            print(f"in PlaylistServiceManager.update_play_times: play_time {updated_track.play_time} is not a valid time for {updated_track.title} by {updated_track.artist}")
        track_index = playlist.tracks.index(updated_track)
        
        # calculate backwards
        for i in range(track_index - 1, -1, -1):
            current_known_track = playlist.tracks[i + 1]
            previous_track = playlist.tracks[i]
            previous_duration = 0 if previous_track.duration is None else previous_track.duration
            previous_track.play_time = current_known_track.play_time - previous_duration
            if previous_track.play_time < 0:
                previous_track.play_time += 604800
                
        # calculate forwards
        for i in range(track_index + 1, len(playlist.tracks)):
            current_known_track = playlist.tracks[i - 1]
            next_track = playlist.tracks[i]
            duration = 0 if current_known_track.duration is None else current_known_track.duration
            next_track.play_time = current_known_track.play_time + duration
            if next_track.play_time > 604800:
                next_track.play_time -= 604800

    def check_for_intros_and_exists(self, playlist: Playlist = None, tracks: List[Track] = None, be_verbose: bool = False):
        if playlist is None and tracks is None:
            print("in PlaylistServiceManager.check_for_intros_and_exists: No playlist or tracks provided")
            return
        if playlist is not None:
            for track in playlist.tracks:
                TrackUtils.check_for_intro(self.intro_dir, track)
                TrackUtils.check_if_track_exists(track)
                if be_verbose:
                    print("track has intro: ", track.has_intro)
        if tracks is not None:
            for track in tracks:
                TrackUtils.check_for_intro(self.intro_dir, track)
                TrackUtils.check_if_track_exists(track)

    def get_current_api_playing_track_pos(self, source_id: str = None) -> Optional[int]:
        """Get current playing track position for a source."""
        if source_id is None:
            source_id = self._default_source_id
        if source_id is None:
            return None
        
        manager = self.store.remote_registry.get_manager(source_id)
        if manager:
            return manager.get_current_track_pos()
        return None

    def create_day_start_times_playlist(self, playlist: Playlist) -> Playlist:
        source_id = playlist.source_id or self._default_source_id
        current_track_pos = self.get_current_api_playing_track_pos(source_id)
        if current_track_pos is None:
            print("in PlaylistServiceManager.create_day_start_times_playlist: current_track_pos is None")
            return playlist
        
        if 0 <= current_track_pos < len(playlist.tracks):
            track = TrackUtils.update_current_track_play_time(playlist, playlist.tracks[current_track_pos])
            self.update_play_times(track, playlist)

        return playlist
