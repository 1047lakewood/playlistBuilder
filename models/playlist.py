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
    type: PlaylistType
    source_id: Optional[str]  # For API playlists, identifies which remote source

    def __init__(self, tracks = None, path: Optional[str] = None, type: PlaylistType = PlaylistType.LOCAL, source_id: Optional[str] = None):
        self.tracks: list[Track] = tracks if tracks is not None else []
        self.path = path
        self.id = uuid.uuid4()
        self.type = type
        self.source_id = source_id  # e.g., "104.7" or "88.7"

    def __str__(self):
        track_paths = []
        for track in self.tracks:
            track_paths.append(track.path)
        return "playlist with tracks:\n" + "\n".join(track_paths)

    def __repr__(self):
        return f"Playlist(tracks={self.tracks}, path={self.path}, id={self.id}, source_id={self.source_id})"
    
    def name_for_display(self) -> str:
        """Return a human-readable name for the playlist."""
        if self.source_id:
            return self.source_id
        if self.path:
            import os
            return os.path.splitext(os.path.basename(self.path))[0]
        return "Untitled"

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