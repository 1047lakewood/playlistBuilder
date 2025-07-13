import uuid
from enum import Enum
from typing import Optional
from models.track import Track



class Playlist:

    class PlaylistType(Enum):
        LOCAL = "local"
        API = "api"
    
    tracks: list[Track]
    path: Optional[str]
    id: uuid.UUID
    type:PlaylistType

    def __init__(self, tracks = None, path: Optional[str] = None, type: PlaylistType = PlaylistType.LOCAL):
        self.tracks: list[Track] = tracks if tracks is not None else []
        self.path = path
        self.id = uuid.uuid4()
        self.type = type

    def __str__(self):
        track_paths = []
        for track in self.tracks:
            track_paths.append(track.path)
        return "playlist with tracks:\n" + "\n".join(track_paths)

    def __repr__(self):
        return f"Playlist(tracks={self.tracks}, path={self.path}, id={self.id})"

    def add_track(self, track: Track, insert_index=-1):
        if insert_index == -1:
            insert_index = len(self.tracks)
        self.tracks.insert(insert_index, track)
    def add_tracks(self, tracks: list[Track], insert_index=-1):
        if insert_index == -1:
            insert_index = len(self.tracks)
        for track in tracks:
            self.tracks.insert(insert_index + tracks.index(track), track)

    def remove_track(self, track):
        self.tracks.remove(track)
    
    def remove_tracks(self, tracks):
        for track in tracks:
            self.tracks.remove(track)
    # dont understand this. SHOULD COPY API MOVE TRACKS!!
    def move_tracks(self, track_indices: list[int], new_index: int):
        track_indices = sorted(track_indices)
        if new_index < track_indices[0]:
            for i in range(len(track_indices)):
                pos1 = track_indices[i]
                pos2 = new_index + i
                self.tracks.insert(pos2, self.tracks.pop(pos1))
                
        elif new_index > track_indices[0]:
            for i in range(len(track_indices)):
                pos1 = track_indices[0]
                pos2 = new_index + len(track_indices) - 1
                self.tracks.insert(pos2, self.tracks.pop(pos1))
        else:
            print("new index is equal to track indices[0]")



    # test tracks
    def add_test_tracks(self, count: int):
        for i in range(count):
            self.tracks.append(Track(path=f"test_{i}.mp4", title=f"test_{i}", duration=10))