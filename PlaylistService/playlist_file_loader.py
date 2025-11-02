import os
from models.playlist import Playlist
from models.track import Track

def load_playlist(file_path: str) -> Playlist:
    playlist = Playlist()
    playlist.path = file_path
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_title = None
    current_duration = None

    for line in lines:

        line = line.strip()
        if not line or line.startswith('#') and not line.startswith('#EXTINF'):
            continue
        if line.startswith('\ufeff'):
            continue
        if line.startswith('#EXTINF:'):
            try:
                duration_title = line[8:]
                duration, title = duration_title.split(',', 1)
                current_duration = int(duration)
                current_title = title
            except ValueError:
                current_duration = None
                current_title = None
        else:
            track = Track(path=line, title=current_title, duration=current_duration)
            playlist.add_track(track, len(playlist.tracks))
            current_title = None
            current_duration = None

    return playlist

def save_playlist(playlist: Playlist, file_path: str = None):
    if file_path is None:
        file_path = playlist.path
    
    is_m3u_format = file_path.lower().endswith(('.m3u', '.m3u8'))

    with open(file_path, 'w', encoding="utf-8") as f:
        if is_m3u_format:
            f.write('#EXTM3U\n')
        for track in playlist.tracks:
            if is_m3u_format:
                duration = track.duration if track.duration is not None else 0
                title = track.title if track.title else os.path.basename(track.path)
                f.write(f'#EXTINF:{duration},{title}\n')
            f.write(f'{track.path}\n')