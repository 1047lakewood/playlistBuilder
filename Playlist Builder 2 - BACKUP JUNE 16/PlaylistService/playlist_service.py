
from PlaylistService import playlist_store
from models import playlist
from models.playlist import Playlist
from PlaylistService.playlist_store import PlaylistStore
from PlaylistService.playlist_editor import PlaylistEditor
from PlaylistService.api_playlist_manager import ApiPlaylistManager
from PlaylistService.track_utils import TrackUtils
from models.track import Track
from typing import List
class PlaylistServiceManager:
    def __init__(self):
        self.playlist_prefered_order = []

        self.api_manager = ApiPlaylistManager()
        self.editor = PlaylistEditor(self.api_manager)
        self.store = PlaylistStore(self.api_manager)
        self.playlists = self.store.open_playlists
        self.intro_dir = "G:\\Shiurim\\IntrosCleanedUp\\"
    



    # playlist loading and saving
    def load_playlist_from_path(self, path) -> Playlist:
        return self.store.load_playlist_from_path(path)

    def save_playlist(self, playlist, file_path = None):
        self.store.save_playlist(playlist, file_path)

    def close_playlist(self, playlist):
        self.store.close_playlist(playlist)


    # Remote Playlist loading

    def load_api_playlist(self):
        api_playlist = self.store.load_api_playlist()
        self.create_day_start_times_playlist(api_playlist)
        return api_playlist
    def reload_api_playlist(self):
        playlist = self.api_manager.reload_playlist()
        self.create_day_start_times_playlist(playlist)
        return playlist
    def close_api_playlist(self):
        self.store.close_playlist(self.store.api_playlist)

    def update_playlist_metadata(self, playlist: Playlist):
        for track in playlist.tracks:
            TrackUtils.update_track_metadata(track)
    def update_track_metadata(self, tracks:List[Track]):
        for track in tracks:
            TrackUtils.update_track_metadata(track)
    
    def update_play_times(self, updated_track: Track, playlist: Playlist):
        if updated_track.play_time == None:
            print(f"in PlaylistServiceManager.update_play_times: play_time is None for {updated_track.title} by {updated_track.artist}")
        if updated_track.play_time < 0 or updated_track.play_time > 604800 :
            print(f"in PlaylistServiceManager.update_play_times: play_time {updated_track.play_time} is not a valid time for {updated_track.title} by {updated_track.artist}")
        track_index = playlist.tracks.index(updated_track)
        # calculate backwards
        for i in range(track_index - 1, -1, -1):
            current_known_track = playlist.tracks[i+1]
            previous_track = playlist.tracks[i]
            previous_duration = 0 if previous_track.duration is None else previous_track.duration
            previous_track.play_time = current_known_track.play_time - previous_duration
            if previous_track.play_time < 0:
                previous_track.play_time += 604800
                
        # calculate forwards
        for i in range(track_index + 1, len(playlist.tracks)):
            current_known_track = playlist.tracks[i-1]
            next_track = playlist.tracks[i]
            duration = 0 if current_known_track.duration is None else current_known_track.duration
            next_track.play_time = current_known_track.play_time + duration
            if next_track.play_time > 604800:
                next_track.play_time -= 604800
        

    def check_for_intros_and_exists(self, playlist: Playlist = None, tracks: List[Track] = None, be_verbose: bool = False):
        if playlist == None and tracks == None:
            print("in PlaylistServiceManager.check_for_intros_and_exists: No playlist or tracks provided")
            return
        if playlist != None:
            for track in playlist.tracks:
                TrackUtils.check_for_intro(self.intro_dir, track)
                TrackUtils.check_if_track_exists(track)
                if be_verbose:
                    print("track has intro: ", track.has_intro)
        if tracks != None:
            for track in tracks:
                TrackUtils.check_for_intro(self.intro_dir, track)
                TrackUtils.check_if_track_exists(track)


    def get_current_api_playing_track_pos(self):
        current_track_pos = self.api_manager.get_current_track_pos()
        if current_track_pos is None:
            return None
        return current_track_pos

    def create_day_start_times_playlist(self, playlist: Playlist) -> Playlist:
        current_track_pos = self.get_current_api_playing_track_pos()
        if current_track_pos is None:
            print("in PlaylistServiceManager.create_day_start_times_playlist: current_track_pos is None")
            return playlist
        track = TrackUtils.update_current_track_play_time(playlist, playlist.tracks[current_track_pos])

        self.update_play_times(track, playlist)

        return playlist