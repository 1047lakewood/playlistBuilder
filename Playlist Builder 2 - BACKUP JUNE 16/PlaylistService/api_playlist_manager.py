from urllib import parse
from models.playlist import Playlist 
from models.track import Track
import requests
import xml.etree.ElementTree as ET
import threading
import time


class ApiPlaylistManager:
    api_url_base = "http://192.168.3.12:9000/?pass=bmas220"
    def __init__(self):
        self.playlist = None
        self._stop_reload_event = threading.Event()
        self._reload_thread = threading.Thread(target=self._auto_reload_loop, daemon=True)
        self._reload_thread.start()
        self.session = requests.Session()

    def _auto_reload_loop(self):
        return
        """Periodically reloads the playlist in a background thread."""
        while not self._stop_reload_event.is_set():
            print("Auto-reloading Remote Playlist...") # Added for logging/debugging
            try:
                self.reload_playlist()
            except Exception as e:
                print(f"Error during auto-reload: {e}") # Log errors
            self._stop_reload_event.wait(10) # Wait for 10 seconds or until stop event is set

    def stop_auto_reload(self):
        """Stops the automatic playlist reloading."""
        self._stop_reload_event.set()
        if self._reload_thread.is_alive():
            self._reload_thread.join()

    def reload_playlist(self) -> Playlist:
        response = self.session.get(self.api_url_base + "&action=getplaylist2")
        if response.status_code == 200:
            self.playlist = self.parse_playlist(response)
            return self.playlist
        else:
            return None
    def get_current_track_pos(self):
        response = self.session.get(self.api_url_base + "&action=playbackinfo")
        if response.status_code == 200:
            return self.parse_current_track_pos(response)
        else:
            return None
    def get_current_track(self):
        response = self.session.get(self.api_url_base + "&action=playbackinfo")
        if response.status_code == 200:
            current_track_pos = self.parse_current_track_pos(response)
            if current_track_pos is not None:
                return self.playlist.tracks[current_track_pos]
        return None
    def insert_tracks(self, tracks, insert_index):
        for track in tracks:
            self.insert_track(track, insert_index + tracks.index(track))
    def insert_track(self, track, insert_index):
        encoded_filename = parse.quote(track.path)
        request = self.api_url_base + f"&action=inserttrack&pos={insert_index}&filename={encoded_filename}"
        response = self.session.get(request)
        if response.status_code == 200:
            self.reload_playlist()
            return True
        else:
            return False

    def remove_tracks(self, track_indices):
        track_indices = sorted(track_indices)
        while len(track_indices) > 0:
            self.remove_track(track_indices[-1])
            track_indices.pop(-1)
    def remove_track(self, track_index):
        response = self.session.get(self.api_url_base + f"&action=delete&pos={track_index}")
        if response.status_code == 200:
            self.reload_playlist()
            return True
        else:
            return False

    def move_tracks(self, track_indices, new_index):
        track_indices = sorted(track_indices)
        if new_index < track_indices[0]:
            for i in range(len(track_indices)):
                pos1 = track_indices[i]
                pos2 = new_index + i
                response = self.session.get(self.api_url_base + f"&action=move&pos1={pos1}&pos2={pos2}")
        elif new_index > track_indices[0]:
            for i in range(len(track_indices)):
                pos1 = track_indices[0]
                pos2 = new_index + len(track_indices) - 1
                response = self.session.get(self.api_url_base + f"&action=move&pos1={pos1}&pos2={pos2}")
        else:
            return False
        if response.status_code == 200:
            self.reload_playlist()
            return True
        else:
            return False
        
                
                



    def parse_playlist(self, response) -> Playlist:
        playlist = Playlist(type=Playlist.PlaylistType.API)
        raw_xml = response.text.strip()

        # Parse the XML directly - it should handle the XML declaration automatically
        root = ET.fromstring(raw_xml)
        
        # Check if the root is 'Playlist' as indicated in your example
        if root.tag == 'Playlist':
            # Extract track info - look for TRACK elements directly under Playlist
            for track in root.findall('TRACK'):
                data = {
                    'DURATION': track.attrib.get('DURATION', ''),
                    'FILENAME': track.attrib.get('FILENAME', ''),
                    'ARTIST': track.attrib.get('ARTIST', ''),
                    'TITLE': track.attrib.get('TITLE', ''),
                    'STARTTIME': track.attrib.get('STARTTIME', '')
                }
                duration = self.time_str_to_seconds(data['DURATION'])
                track = Track(path=data['FILENAME'], artist=data['ARTIST'], title=data['TITLE'], duration=duration)
                # convert start time to seconds
                
                track.play_time = self.time_str_to_seconds(data['STARTTIME'])
                playlist.tracks.append(track)
        else:
            print(f"Unexpected root element: {root.tag}")
        playlist.type = Playlist.PlaylistType.API

        return playlist
    def parse_current_track_pos(self, response) -> int:
        raw_xml = response.text.strip()
        root = ET.fromstring(raw_xml)
        if root.tag == 'Info':
            current_track = root.find('Playback')
            if current_track is not None:
                return int(current_track.attrib.get('playlistpos', -1)) - 1
        
    def time_str_to_seconds(self, time_str):
        parts = time_str.strip().split(":")
        try:
            parts = [int(p) for p in parts]
        except ValueError:
            return None  # or raise ValueError("Invalid time string")

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
            return None  # Invalid format

        return hours * 3600 + minutes * 60 + seconds
        