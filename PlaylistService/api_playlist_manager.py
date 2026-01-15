from urllib import parse
from models.playlist import Playlist 
from models.track import Track
import requests
import xml.etree.ElementTree as ET
import threading
import app_config
import time
from enum import Enum
from typing import Optional, Callable


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"


class ApiPlaylistManager:
    """Manages a connection to a single remote playlist API source."""
    
    def __init__(self, source_id: str, api_url: str, name: str = None):
        self.source_id = source_id
        self.api_url_base = api_url
        self.name = name or source_id
        self.playlist: Optional[Playlist] = None
        
        # Connection status
        self._status = ConnectionStatus.DISCONNECTED
        self._status_message = ""
        self._last_error: Optional[str] = None
        self._status_callbacks: list[Callable] = []

        # Reload callbacks - called when playlist is reloaded from server
        self._reload_callbacks: list[Callable] = []
        
        # Timeouts from config
        self._connect_timeout = app_config.get(["network", "connection_timeout"], 5)
        self._read_timeout = app_config.get(["network", "read_timeout"], 10)
        
        # Auto-reload control
        self._stop_reload_event = threading.Event()
        self._reload_thread: Optional[threading.Thread] = None
        
        # Session for connection reuse
        self.session = requests.Session()

    def update_source_config(self, api_url: str, name: str | None = None):
        """Update the source configuration in-place (used during registry reloads)."""
        self.api_url_base = api_url
        if name:
            self.name = name
        # Refresh timeouts from config in case settings changed
        self._connect_timeout = app_config.get(["network", "connection_timeout"], 5)
        self._read_timeout = app_config.get(["network", "read_timeout"], 10)
    
    @property
    def status(self) -> ConnectionStatus:
        return self._status
    
    @property
    def status_message(self) -> str:
        return self._status_message
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    @property
    def is_connected(self) -> bool:
        return self._status == ConnectionStatus.CONNECTED
    
    def add_status_callback(self, callback: Callable):
        """Register a callback to be notified when connection status changes."""
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable):
        """Unregister a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def add_reload_callback(self, callback: Callable):
        """Register a callback to be notified when playlist is reloaded from server."""
        if callback not in self._reload_callbacks:
            self._reload_callbacks.append(callback)

    def remove_reload_callback(self, callback: Callable):
        """Unregister a reload callback."""
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    def _notify_reload(self, playlist: Playlist):
        """Notify all registered callbacks that playlist was reloaded."""
        for callback in self._reload_callbacks:
            try:
                callback(playlist)
            except Exception as e:
                print(f"Error in reload callback: {e}")

    def _set_status(self, status: ConnectionStatus, message: str = ""):
        """Update connection status and notify callbacks."""
        old_status = self._status
        self._status = status
        self._status_message = message
        
        if status == ConnectionStatus.ERROR or status == ConnectionStatus.TIMEOUT:
            self._last_error = message
        
        # Notify callbacks if status changed
        if old_status != status:
            for callback in self._status_callbacks:
                try:
                    callback(self, status, message)
                except Exception as e:
                    print(f"Error in status callback: {e}")
    
    def start_auto_reload(self, interval_seconds: int = 10):
        """Start automatic playlist reloading in background."""
        if self._reload_thread and self._reload_thread.is_alive():
            return  # Already running
        
        self._stop_reload_event.clear()
        self._reload_thread = threading.Thread(
            target=self._auto_reload_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._reload_thread.start()

    def _auto_reload_loop(self, interval: int):
        """Periodically reloads the playlist in a background thread."""
        while not self._stop_reload_event.is_set():
            try:
                new_playlist = self.reload_playlist()
                if new_playlist:
                    self._notify_reload(new_playlist)
            except Exception as e:
                print(f"Error during auto-reload for {self.name}: {e}")
            self._stop_reload_event.wait(interval)

    def stop_auto_reload(self):
        """Stops the automatic playlist reloading."""
        self._stop_reload_event.set()
        if self._reload_thread and self._reload_thread.is_alive():
            self._reload_thread.join(timeout=2)
    
    def _make_request(self, endpoint: str, show_connecting: bool = True) -> Optional[requests.Response]:
        """Make a request with proper timeout handling.

        Args:
            endpoint: API endpoint to call
            show_connecting: Whether to show CONNECTING status (useful for background polling)
        """
        url = self.api_url_base + endpoint
        try:
            if show_connecting:
                self._set_status(ConnectionStatus.CONNECTING, f"Connecting to {self.name}...")
            response = self.session.get(
                url,
                timeout=(self._connect_timeout, self._read_timeout)
            )
            if response.status_code == 200:
                # Only set CONNECTED status if we were previously showing connecting
                if show_connecting or self._status != ConnectionStatus.CONNECTED:
                    self._set_status(ConnectionStatus.CONNECTED, f"Connected to {self.name}")
                return response
            else:
                self._set_status(
                    ConnectionStatus.ERROR,
                    f"Server returned status {response.status_code}"
                )
                return None
        except requests.exceptions.ConnectTimeout:
            self._set_status(
                ConnectionStatus.TIMEOUT,
                f"Connection timeout - {self.name} not responding"
            )
            return None
        except requests.exceptions.ReadTimeout:
            self._set_status(
                ConnectionStatus.TIMEOUT,
                f"Read timeout - {self.name} took too long to respond"
            )
            return None
        except requests.exceptions.ConnectionError as e:
            self._set_status(
                ConnectionStatus.ERROR,
                f"Connection failed - {self.name} unreachable"
            )
            return None
        except Exception as e:
            self._set_status(ConnectionStatus.ERROR, f"Error: {str(e)}")
            return None

    def reload_playlist(self) -> Optional[Playlist]:
        """Reload playlist from the API."""
        response = self._make_request("&action=getplaylist2")
        if response:
            self.playlist = self.parse_playlist(response)
            self.playlist.source_id = self.source_id
            return self.playlist
        return None
    
    def get_current_track_pos(self) -> Optional[int]:
        """Get the position of the currently playing track."""
        response = self._make_request("&action=playbackinfo", show_connecting=False)
        if response:
            return self.parse_current_track_pos(response)
        return None

    def get_current_track(self) -> Optional[Track]:
        """Get the currently playing track."""
        response = self._make_request("&action=playbackinfo", show_connecting=False)
        if response and self.playlist:
            current_track_pos = self.parse_current_track_pos(response)
            if current_track_pos is not None and 0 <= current_track_pos < len(self.playlist.tracks):
                return self.playlist.tracks[current_track_pos]
        return None
    
    def insert_tracks(self, tracks: list, insert_index: int) -> bool:
        """Insert multiple tracks at the specified index."""
        success = True
        for i, track in enumerate(tracks):
            if not self.insert_track(track, insert_index + i):
                success = False
        return success
    
    def insert_track(self, track: Track, insert_index: int) -> bool:
        """Insert a single track at the specified index."""
        encoded_filename = parse.quote(track.path)
        response = self._make_request(
            f"&action=inserttrack&pos={insert_index}&filename={encoded_filename}"
        )
        if response:
            self.reload_playlist()
            return True
        return False

    def remove_tracks(self, track_indices: list) -> bool:
        """Remove multiple tracks by their indices (sorted descending)."""
        track_indices = sorted(track_indices, reverse=True)
        success = True
        for index in track_indices:
            if not self.remove_track(index):
                success = False
        return success
    
    def remove_track(self, track_index: int) -> bool:
        """Remove a single track at the specified index."""
        response = self._make_request(f"&action=delete&pos={track_index}")
        if response:
            self.reload_playlist()
            return True
        return False

    def move_tracks(self, track_indices: list, new_index: int) -> bool:
        """Move tracks to a new position."""
        track_indices = sorted(track_indices)
        if not track_indices or new_index == track_indices[0]:
            return False
        
        response = None
        if new_index < track_indices[0]:
            for i, pos1 in enumerate(track_indices):
                pos2 = new_index + i
                response = self._make_request(f"&action=move&pos1={pos1}&pos2={pos2}")
        else:
            for i in range(len(track_indices)):
                pos1 = track_indices[0]
                pos2 = new_index + len(track_indices) - 1
                response = self._make_request(f"&action=move&pos1={pos1}&pos2={pos2}")
        
        if response:
            self.reload_playlist()
            return True
        return False

    def parse_playlist(self, response) -> Playlist:
        """Parse the XML response into a Playlist object."""
        playlist = Playlist(type=Playlist.PlaylistType.API)
        playlist.source_id = self.source_id
        raw_xml = response.text.strip()

        root = ET.fromstring(raw_xml)
        
        if root.tag == 'Playlist':
            for track_elem in root.findall('TRACK'):
                data = {
                    'DURATION': track_elem.attrib.get('DURATION', ''),
                    'FILENAME': track_elem.attrib.get('FILENAME', ''),
                    'ARTIST': track_elem.attrib.get('ARTIST', ''),
                    'TITLE': track_elem.attrib.get('TITLE', ''),
                    'STARTTIME': track_elem.attrib.get('STARTTIME', '')
                }
                duration = self.time_str_to_seconds(data['DURATION'])
                track = Track(
                    path=data['FILENAME'],
                    artist=data['ARTIST'],
                    title=data['TITLE'],
                    duration=duration
                )
                track.play_time = self.time_str_to_seconds(data['STARTTIME'])
                playlist.tracks.append(track)
        else:
            print(f"Unexpected root element: {root.tag}")
        
        playlist.type = Playlist.PlaylistType.API
        return playlist
    
    def parse_current_track_pos(self, response) -> Optional[int]:
        """Parse the playback info response to get current track position."""
        raw_xml = response.text.strip()
        root = ET.fromstring(raw_xml)
        if root.tag == 'Info':
            current_track = root.find('Playback')
            if current_track is not None:
                pos = int(current_track.attrib.get('playlistpos', 0)) - 1
                return pos if pos >= 0 else None
        return None
    
    def time_str_to_seconds(self, time_str: str) -> Optional[int]:
        """Convert a time string (HH:MM:SS or MM:SS) to seconds."""
        parts = time_str.strip().split(":")
        try:
            parts = [int(p) for p in parts]
        except ValueError:
            return None

        if len(parts) == 3:
            hours, minutes, seconds = parts
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = parts
        elif len(parts) == 1:
            hours = 0
            minutes = 0
            seconds = parts[0]
        else:
            return None

        return hours * 3600 + minutes * 60 + seconds
    
    def disconnect(self):
        """Disconnect from the remote source and clean up."""
        self.stop_auto_reload()
        self._set_status(ConnectionStatus.DISCONNECTED, f"Disconnected from {self.name}")
        self.playlist = None
    
    def __repr__(self):
        return f"ApiPlaylistManager(source_id='{self.source_id}', name='{self.name}', status={self._status.value})"


class RemotePlaylistRegistry:
    """Registry that manages multiple ApiPlaylistManager instances."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._managers: dict[str, ApiPlaylistManager] = {}
        self._load_sources_from_config()
    
    def _load_sources_from_config(self):
        """Load remote source configurations."""
        sources = app_config.get(["network", "remote_sources"], {})
        for source_id, source_config in sources.items():
            if source_config.get("enabled", True):
                self.register_source(
                    source_id,
                    source_config.get("url", ""),
                    source_config.get("name", source_id)
                )
    
    def register_source(self, source_id: str, url: str, name: str = None):
        """Register a new remote source."""
        if source_id not in self._managers:
            self._managers[source_id] = ApiPlaylistManager(source_id, url, name)
    
    def get_manager(self, source_id: str) -> Optional[ApiPlaylistManager]:
        """Get the manager for a specific source."""
        return self._managers.get(source_id)
    
    def get_all_managers(self) -> dict[str, ApiPlaylistManager]:
        """Get all registered managers."""
        return self._managers.copy()
    
    def get_connected_managers(self) -> list[ApiPlaylistManager]:
        """Get all managers that are currently connected."""
        return [m for m in self._managers.values() if m.is_connected]
    
    def get_available_sources(self) -> list[tuple[str, str]]:
        """Get list of (source_id, name) for all available sources."""
        return [(m.source_id, m.name) for m in self._managers.values()]
    
    def disconnect_all(self):
        """Disconnect all managers."""
        for manager in self._managers.values():
            manager.disconnect()
    
    def reload(self):
        """Reload sources from config without breaking existing subscribers.

        Preserves existing ApiPlaylistManager instances per source_id when possible
        (updates url/name in-place) so UI callbacks remain attached.
        """
        sources = app_config.get(["network", "remote_sources"], {})

        # Compute the set of enabled sources we should have after reload.
        enabled_sources: dict[str, dict] = {}
        for source_id, source_config in sources.items():
            if source_config.get("enabled", True):
                enabled_sources[source_id] = source_config

        enabled_ids = set(enabled_sources.keys())

        # Disconnect and remove managers for disabled/removed sources.
        for source_id in list(self._managers.keys()):
            if source_id not in enabled_ids:
                try:
                    self._managers[source_id].disconnect()
                except Exception:
                    pass
                del self._managers[source_id]

        # Update existing managers in-place, and create managers for new sources.
        for source_id, source_config in enabled_sources.items():
            url = source_config.get("url", "")
            name = source_config.get("name", source_id)
            existing = self._managers.get(source_id)
            if existing:
                try:
                    existing.update_source_config(url, name=name)
                except Exception:
                    # Fall back to replacing the manager if something goes wrong
                    try:
                        existing.disconnect()
                    except Exception:
                        pass
                    self._managers[source_id] = ApiPlaylistManager(source_id, url, name)
            else:
                self._managers[source_id] = ApiPlaylistManager(source_id, url, name)
