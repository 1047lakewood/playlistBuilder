import os
from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError
from mutagen.flac import FLACNoHeaderError
from mutagen.mp4 import MP4NoTrackError
from mutagen.oggvorbis import OggVorbisHeaderError
import traceback

def load_audio_metadata(filepath):
    """
    Loads metadata from an audio file using mutagen, with robust error handling and logging.
    Returns a dict with keys: artist, title, album, genre, tracknumber, duration, bitrate, format, path, exists.
    """
    metadata = {
        'artist': 'Unknown Artist',
        'title': os.path.splitext(os.path.basename(filepath))[0],
        'album': 'Unknown Album',
        'genre': 'Unknown Genre',
        'tracknumber': '',
        'duration': None,
        'bitrate': None,
        'format': '',
        'path': filepath,
        'exists': os.path.exists(filepath)
    }
    if not metadata['exists']:
        return metadata

    try:
        audio = None
        try:
            audio = MutagenFile(filepath, easy=True)
        except ValueError as ve:
            print(f"[METADATA][ERROR] ValueError in MutagenFile (easy=True): {filepath}\n{ve}")
            metadata['format'] = "Invalid MultiSpec"
            return metadata
        except Exception as e:
            print(f"[METADATA][ERROR] Exception in MutagenFile (easy=True): {filepath}\n{e}")
            traceback.print_exc()
            metadata['format'] = "Error reading"
            return metadata
        if audio:
            metadata['artist'] = ', '.join(audio.get('artist', ['Unknown Artist']))
            metadata['title'] = ', '.join(audio.get('title', [metadata['title']]))
            metadata['album'] = ', '.join(audio.get('album', ['Unknown Album']))
            metadata['genre'] = ', '.join(audio.get('genre', ['Unknown Genre']))
            tn = audio.get('tracknumber', [''])[0]
            if '/' in tn:
                tn = tn.split('/')[0]
            metadata['tracknumber'] = tn
            metadata['duration'] = audio.info.length if hasattr(audio, 'info') and hasattr(audio.info, 'length') else None
            metadata['format'] = type(audio).__name__
            metadata['bitrate'] = getattr(audio.info, 'bitrate', None) if hasattr(audio, 'info') else None
        else:
            # Try again without easy=True for more exotic formats
            try:
                audio = MutagenFile(filepath)
                if audio:
                    duration = None
                    if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                        duration = audio.info.length
                    metadata['duration'] = duration
                    metadata['format'] = type(audio).__name__
                    metadata['bitrate'] = getattr(audio.info, 'bitrate', None) if hasattr(audio, 'info') else None
            except (ID3NoHeaderError, FLACNoHeaderError, MP4NoTrackError, OggVorbisHeaderError) as e:
                print(f"[METADATA][WARN] Header error for {filepath}: {e}")
                metadata['format'] = "Header error"
                return metadata
            except ValueError as ve:
                print(f"[METADATA][ERROR] ValueError in MutagenFile (secondary attempt): {filepath}\n{ve}")
                metadata['format'] = "Invalid MultiSpec"
                return metadata
            except Exception as e:
                print(f"[METADATA][ERROR] Failed to load audio file (secondary attempt): {filepath}\n{e}")
                traceback.print_exc()
                metadata['format'] = "Error reading"
                return metadata
        # Final fallback: If still no duration or format, note error
        if metadata['duration'] is None:
            print(f"[METADATA][WARN] No duration found for {filepath}")
        if not metadata['format']:
            metadata['format'] = "Unknown/Unsupported ({})".format(os.path.splitext(filepath)[1])
    except Exception as e:
        print(f"[METADATA][ERROR] Could not load audio file with mutagen (unsupported format or corrupt?): {filepath}\n{e}")
        traceback.print_exc()
        metadata['format'] = "Error reading"
    return metadata

def save_audio_metadata(filepath, new_metadata):
    """
    Attempts to save metadata to an audio file using the correct Mutagen class for the file type.
    Returns (success: bool, error: str or None)
    """
    import mutagen
    import mutagen.mp3
    import mutagen.flac
    import mutagen.mp4
    import mutagen.oggvorbis
    import mutagen.asf
    import mutagen.wavpack
    import mutagen.oggopus
    import mutagen.aiff
    import mutagen.wave
    import traceback
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in ['.mp3']:
            audio = mutagen.mp3.MP3(filepath)
            audio['TIT2'] = mutagen.id3.TIT2(encoding=3, text=new_metadata.get('title', ''))
            audio['TPE1'] = mutagen.id3.TPE1(encoding=3, text=new_metadata.get('artist', ''))
            audio['TALB'] = mutagen.id3.TALB(encoding=3, text=new_metadata.get('album', ''))
            audio['TCON'] = mutagen.id3.TCON(encoding=3, text=new_metadata.get('genre', ''))
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['TRCK'] = mutagen.id3.TRCK(encoding=3, text=str(tn))
            audio.save()
        elif ext in ['.flac']:
            audio = mutagen.flac.FLAC(filepath)
            audio['title'] = [new_metadata.get('title', '')]
            audio['artist'] = [new_metadata.get('artist', '')]
            audio['album'] = [new_metadata.get('album', '')]
            audio['genre'] = [new_metadata.get('genre', '')]
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['tracknumber'] = [str(tn)]
            audio.save()
        elif ext in ['.m4a', '.mp4']:
            audio = mutagen.mp4.MP4(filepath)
            audio['\xa9nam'] = [new_metadata.get('title', '')]
            audio['\xa9ART'] = [new_metadata.get('artist', '')]
            audio['\xa9alb'] = [new_metadata.get('album', '')]
            audio['\xa9gen'] = [new_metadata.get('genre', '')]
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['trkn'] = [(int(tn), 0)]
            audio.save()
        elif ext in ['.ogg', '.oga']:
            audio = mutagen.oggvorbis.OggVorbis(filepath)
            audio['title'] = [new_metadata.get('title', '')]
            audio['artist'] = [new_metadata.get('artist', '')]
            audio['album'] = [new_metadata.get('album', '')]
            audio['genre'] = [new_metadata.get('genre', '')]
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['tracknumber'] = [str(tn)]
            audio.save()
        elif ext in ['.opus']:
            audio = mutagen.oggopus.OggOpus(filepath)
            audio['title'] = [new_metadata.get('title', '')]
            audio['artist'] = [new_metadata.get('artist', '')]
            audio['album'] = [new_metadata.get('album', '')]
            audio['genre'] = [new_metadata.get('genre', '')]
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['tracknumber'] = [str(tn)]
            audio.save()
        elif ext in ['.wv']:
            audio = mutagen.wavpack.WavPack(filepath)
            audio['title'] = [new_metadata.get('title', '')]
            audio['artist'] = [new_metadata.get('artist', '')]
            audio['album'] = [new_metadata.get('album', '')]
            audio['genre'] = [new_metadata.get('genre', '')]
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['tracknumber'] = [str(tn)]
            audio.save()
        elif ext in ['.asf', '.wma']:
            audio = mutagen.asf.ASF(filepath)
            audio['Title'] = [new_metadata.get('title', '')]
            audio['Author'] = [new_metadata.get('artist', '')]
            audio['WM/AlbumTitle'] = [new_metadata.get('album', '')]
            audio['WM/Genre'] = [new_metadata.get('genre', '')]
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['WM/TrackNumber'] = [str(tn)]
            audio.save()
        elif ext in ['.aiff', '.aif']:
            audio = mutagen.aiff.AIFF(filepath)
            audio['TIT2'] = mutagen.id3.TIT2(encoding=3, text=new_metadata.get('title', ''))
            audio['TPE1'] = mutagen.id3.TPE1(encoding=3, text=new_metadata.get('artist', ''))
            audio['TALB'] = mutagen.id3.TALB(encoding=3, text=new_metadata.get('album', ''))
            audio['TCON'] = mutagen.id3.TCON(encoding=3, text=new_metadata.get('genre', ''))
            tn = new_metadata.get('tracknumber', '')
            if tn:
                audio['TRCK'] = mutagen.id3.TRCK(encoding=3, text=str(tn))
            audio.save()
        elif ext in ['.wav']:
            # WAV: Only supports RIFF INFO tags, very limited
            try:
                audio = mutagen.wave.WAVE(filepath)
                audio['INAM'] = new_metadata.get('title', '')
                audio['IART'] = new_metadata.get('artist', '')
                audio['IPRD'] = new_metadata.get('album', '')
                audio['IGNR'] = new_metadata.get('genre', '')
                tn = new_metadata.get('tracknumber', '')
                if tn:
                    audio['ITRK'] = str(tn)
                audio.save()
            except Exception as e:
                print(f"[METADATA][WARN] WAV tag writing failed for {filepath}: {e}")
                return False, f"WAV tag writing failed: {e}"
        else:
            return False, f"Unsupported audio format for metadata editing: {ext}"
        return True, None
    except Exception as e:
        print(f"[METADATA][ERROR] Failed to save metadata for {filepath}: {e}")
        traceback.print_exc()
        return False, str(e)
