from dataclasses import dataclass
from typing import List, Optional
from models.track import Track


@dataclass
class TrackChange:
    """Represents a single change in the playlist."""
    action: str  # 'insert', 'delete', 'update'
    index: int
    track: Optional[Track] = None


@dataclass
class PlaylistDiff:
    """Result of comparing two playlists."""
    changes: List[TrackChange]
    is_identical: bool

    @classmethod
    def compute(cls, old_tracks: List[Track], new_tracks: List[Track]) -> 'PlaylistDiff':
        """
        Compare two track lists and produce minimal change set.

        Strategy:
        1. Build maps of path -> (index, track) for both lists
        2. Identify removed tracks (in old but not new)
        3. Identify added tracks (in new but not old)
        4. Identify updated tracks (same path, different attributes)

        Returns operations to transform old_tracks into new_tracks.
        """
        changes = []

        old_map = {t.path: (i, t) for i, t in enumerate(old_tracks)}
        new_map = {t.path: (i, t) for i, t in enumerate(new_tracks)}

        old_paths = set(old_map.keys())
        new_paths = set(new_map.keys())

        # Deleted tracks (in old but not in new)
        deleted_paths = old_paths - new_paths
        # Process deletions in reverse index order so indices remain valid
        for path in sorted(deleted_paths, key=lambda p: old_map[p][0], reverse=True):
            old_idx, _ = old_map[path]
            changes.append(TrackChange('delete', old_idx))

        # Added tracks (in new but not in old)
        added_paths = new_paths - old_paths
        for path in sorted(added_paths, key=lambda p: new_map[p][0]):
            new_idx, track = new_map[path]
            changes.append(TrackChange('insert', new_idx, track))

        # Check for updates among common tracks
        common_paths = old_paths & new_paths
        for path in common_paths:
            old_idx, old_track = old_map[path]
            new_idx, new_track = new_map[path]

            # Check if attributes changed
            if old_track.fingerprint() != new_track.fingerprint():
                changes.append(TrackChange('update', new_idx, new_track))

        is_identical = len(changes) == 0
        return cls(changes, is_identical)
