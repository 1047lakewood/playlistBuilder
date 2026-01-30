from models.track import Track
from mutagen import File, MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.asf import ASF  # For WMA files
from mutagen.mp4 import MP4  # For M4A files
import os
import logging
import io
import datetime

class TrackUtils:
    @staticmethod
    def update_track_metadata(track: Track):
        # Check if file exists before attempting to update metadata

            
        metadata = TrackUtils._get_track_metadata(track.path)
        track.artist = metadata['artist']
        track.title = metadata['title']
        track.duration = metadata['duration'] if metadata['duration'] != 0 else track.duration
        track.metadata = metadata
        track.exists = True
        return track

    @staticmethod
    def check_for_intro(intro_dir: str, track: Track):
        if not track.artist:
            track.has_intro = False
            return

        if not os.path.exists(intro_dir):
            print(f"Intro directory {intro_dir} does not exist")
            track.has_intro = False 
            return
        
        artist_lower = track.artist.lower() 
        for file_name in os.listdir(intro_dir):
            if file_name.lower().startswith(artist_lower): 
                track.has_intro = True
                return 
        
        track.has_intro = False 

    @staticmethod
    def check_if_track_exists(track: Track):
        track.exists = os.path.exists(track.path)
    @staticmethod
    def _get_track_metadata(file_path):
        if not os.path.isfile(file_path):
            return {
                'artist': "",
                'title': "",
                'duration': 0
            }

        artist = "Unknown Artist"
        title = "Unknown Title"
        duration = 0.0

        try:
            with open(file_path, 'rb') as f:
                file_ext = os.path.splitext(file_path)[1].lower()

                if file_ext == '.mp3':
                    try:
                        # Load the MP3 structure and info using MP3(fileobj=f)
                        audio_mp3 = MP3(fileobj=f)
                        duration = round(audio_mp3.info.length, 2) if audio_mp3.info and hasattr(audio_mp3.info, 'length') else 0.0

                        # Access ID3 tags directly from audio_mp3.tags
                        if audio_mp3.tags:
                            # Artist (TPE1 frame)
                            if 'TPE1' in audio_mp3.tags:
                                frame = audio_mp3.tags['TPE1']
                                if frame.text and len(frame.text) > 0 and frame.text[0].strip():
                                    artist = frame.text[0].strip()
                            
                            # Title (TIT2 frame)
                            if 'TIT2' in audio_mp3.tags:
                                frame = audio_mp3.tags['TIT2']
                                if frame.text and len(frame.text) > 0 and frame.text[0].strip():
                                    title = frame.text[0].strip()
                        
                        # Fallback if artist is still default/empty
                        if not artist or artist == "Unknown Artist":
                            artist = "Unknown Artist" # Or some other placeholder/derivation
                        
                        # Fallback for title if not found via tags or if it's still the default/empty
                        if not title or title == "Unknown Title":
                            title = os.path.splitext(os.path.basename(file_path))[0]

                    except MutagenError as e: # Catch specific mutagen errors
                        logging.debug(f"Could not read MP3 metadata for {file_path} with MP3(fileobj): {e}")
                        if not title or title == "Unknown Title": # Ensure title fallback
                            title = os.path.splitext(os.path.basename(file_path))[0]
                    except Exception as e: # General fallback for other unexpected errors
                        logging.error(f"Unexpected error reading MP3 metadata for {file_path}: {e}")
                        if not title or title == "Unknown Title": # Ensure title fallback
                            title = os.path.splitext(os.path.basename(file_path))[0]

                elif file_ext == '.wav':
                    try:
                        audio = WAVE(fileobj=f)
                        duration = round(audio.info.length, 2) if audio and audio.info else 0.0
                        
                        try:
                            f.seek(0)
                            id3 = ID3(fileobj=f)
                            if 'TPE1' in id3:
                                artist = str(id3['TPE1']).strip()
                            if 'TIT2' in id3:
                                title = str(id3['TIT2']).strip()
                        except ID3NoHeaderError:
                            if title == "Unknown Title":
                                title = os.path.splitext(os.path.basename(file_path))[0]
                        except Exception as e_id3:
                            logging.debug(f"Could not read ID3 from WAV {file_path}: {e_id3}")
                            if title == "Unknown Title":
                                title = os.path.splitext(os.path.basename(file_path))[0]
                    except Exception as e:
                        logging.debug(f"Could not read WAV metadata for {file_path}: {e}")
                        # Fallback if WAVE parser fails, still try ID3
                        try:
                            f.seek(0)
                            id3 = ID3(fileobj=f)
                            if 'TPE1' in id3:
                                artist = str(id3['TPE1']).strip()
                            if 'TIT2' in id3:
                                title = str(id3['TIT2']).strip()
                            
                            f.seek(0)
                            audio_full = File(fileobj=f) # Generic file for duration
                            duration = round(audio_full.info.length, 2) if audio_full and audio_full.info else 0.0
                        except Exception as e2:
                            logging.debug(f"Fallback ID3/File read failed for WAV {file_path}: {e2}")
                            if title == "Unknown Title":
                                title = os.path.splitext(os.path.basename(file_path))[0]
                
                elif file_ext == '.wma':
                    try:
                        audio = ASF(fileobj=f)
                        if 'Author' in audio:
                            artist = str(audio['Author'][0]).strip()
                        elif 'WM/AlbumArtist' in audio:
                            artist = str(audio['WM/AlbumArtist'][0]).strip()
                        elif 'WM/Composer' in audio:
                            artist = str(audio['WM/Composer'][0]).strip()
                            
                        if 'Title' in audio:
                            title = str(audio['Title'][0]).strip()
                        elif 'WM/Title' in audio:
                            title = str(audio['WM/Title'][0]).strip()
                            
                        duration = round(audio.info.length, 2) if audio and audio.info else 0.0
                    except Exception as e:
                        logging.debug(f"Could not read WMA metadata for {file_path}: {e}")
                        if title == "Unknown Title":
                            title = os.path.splitext(os.path.basename(file_path))[0]

                elif file_ext in ['.m4a', '.mp4', '.aac']:
                    try:
                        audio = MP4(fileobj=f)
                        if '\xa9ART' in audio: # Artist
                            artist = str(audio['\xa9ART'][0]).strip()
                        elif 'aART' in audio: # Album Artist
                            artist = str(audio['aART'][0]).strip()
                        elif '----:com.apple.iTunes:Artist' in audio:
                            artist = str(audio['----:com.apple.iTunes:Artist'][0]).decode('utf-8', 'ignore').strip()
                        
                        if '\xa9nam' in audio: # Name/Title
                            title = str(audio['\xa9nam'][0]).strip()
                        elif '----:com.apple.iTunes:Name' in audio:
                            title = str(audio['----:com.apple.iTunes:Name'][0]).decode('utf-8', 'ignore').strip()
                        elif '----:com.apple.iTunes:Title' in audio: # Less common but possible
                            title = str(audio['----:com.apple.iTunes:Title'][0]).decode('utf-8', 'ignore').strip()
                        
                        duration = round(audio.info.length, 2) if audio and audio.info else 0.0
                    except Exception as e:
                        logging.debug(f"Could not read M4A/MP4/AAC metadata for {file_path}: {e}")
                        if title == "Unknown Title":
                            title = os.path.splitext(os.path.basename(file_path))[0]
                
                else: # Fallback for other/unknown formats
                    try:
                        audio = File(fileobj=f, easy=True)
                        if audio is not None:
                            artist = audio.get('artist', ['Unknown Artist'])[0].strip()
                            title = audio.get('title', ['Unknown Title'])[0].strip()
                            
                            f.seek(0)
                            audio_full = File(fileobj=f) # For duration
                            duration = round(audio_full.info.length, 2) if audio_full and audio_full.info else 0.0
                        else: # If File(easy=True) returns None
                            if title == "Unknown Title":
                                title = os.path.splitext(os.path.basename(file_path))[0]
                    except Exception as e:
                        logging.debug(f"Could not read generic metadata for {file_path}: {e}")
                        if title == "Unknown Title":
                            title = os.path.splitext(os.path.basename(file_path))[0]
        
        except IOError as e:
            logging.error(f"Could not open or read file {file_path}: {e}")
            # Keep default values, or values from filename if title is still unknown
            if title == "Unknown Title":
                 title = os.path.splitext(os.path.basename(file_path))[0]
        except Exception as e:
            logging.error(f"Unexpected error processing {file_path}: {e}")
            if title == "Unknown Title":
                 title = os.path.splitext(os.path.basename(file_path))[0]

        return {
            'artist': artist,
            'title': title,
            'duration': duration
        }
    @staticmethod
    def change_track_metadata(track: Track, artist: str, title: str):
        # Check if file exists before attempting to change metadata
        if not os.path.isfile(track.path):
            import tkinter.messagebox as messagebox
            messagebox.showerror("File Error", f"File doesn't exist: {track.path}")
            return
            
        file_ext = os.path.splitext(track.path)[1].lower()
        
        try:
            if file_ext == '.mp3':
                # MP3 files - with enhanced error handling for newly converted files
                try:
                    # First try the standard EasyID3 approach
                    try:
                        audio = EasyID3(track.path)
                    except Exception as e:
                        logging.info(f"Initial EasyID3 failed: {str(e)}. Trying to add tags...")
                        # If the file doesn't have ID3 tags, try to add them
                        try:
                            # Try with mutagen.File first
                            audio = File(track.path)
                            if audio is None:
                                raise ValueError(f"Unsupported or corrupt file: {track.path}")
                                
                            if hasattr(audio, 'add_tags') and callable(audio.add_tags):
                                try:
                                    audio.add_tags()
                                except Exception as e2:
                                    logging.debug(f"Could not add tags with File: {str(e2)}")
                        except Exception as e3:
                            logging.debug(f"File approach failed: {str(e3)}. Trying with MP3...")
                            
                        # Try with MP3 directly
                        try:
                            mp3_file = MP3(track.path)
                            if mp3_file.tags is None:
                                mp3_file.add_tags()
                                mp3_file.save()
                            # Now try EasyID3 again
                            audio = EasyID3(track.path)
                        except Exception as e4:
                            logging.debug(f"MP3 approach failed: {str(e4)}. Last resort...")
                            
                            # Last resort: Create a new ID3 tag from scratch
                            try:
                                from mutagen.id3 import ID3, ID3NoHeaderError
                                try:
                                    id3 = ID3(track.path)
                                except ID3NoHeaderError:
                                    # Create a new tag
                                    id3 = ID3()
                                    id3.save(track.path)
                                # Now try EasyID3 once more
                                audio = EasyID3(track.path)
                            except Exception as e5:
                                logging.error(f"All ID3 approaches failed: {str(e5)}")
                                raise ValueError(f"Could not create or access ID3 tags: {track.path}")
                    
                    # Set the artist and title tags
                    audio['artist'] = [artist]
                    audio['title'] = [title]
                    audio.save()
                    logging.info(f"Successfully updated MP3 metadata for: {track.path}")
                    
                except Exception as e:
                    logging.error(f"Failed to update MP3 metadata: {str(e)}")
                    # Try direct ID3 tag manipulation as a last resort
                    try:
                        from mutagen.id3 import ID3, TPE1, TIT2
                        try:
                            id3 = ID3(track.path)
                        except:
                            id3 = ID3()
                        
                        id3.add(TPE1(encoding=3, text=artist))
                        id3.add(TIT2(encoding=3, text=title))
                        id3.save(track.path)
                        logging.info(f"Successfully updated MP3 metadata using direct ID3: {track.path}")
                    except Exception as e2:
                        logging.error(f"Direct ID3 update failed: {str(e2)}")
                        raise
            
            elif file_ext == '.wav':
                # WAV files - limited metadata support for writing
                logging.debug("WAV files have limited metadata support for writing")
                # Try to write ID3 tags to WAV file
                try:
                    # Try to get existing ID3 tags or create new ones
                    try:
                        id3 = ID3(track.path)
                    except ID3NoHeaderError:
                        # No ID3 header, create one
                        id3 = ID3()
                    
                    # Set the artist and title tags
                    from mutagen.id3 import TPE1, TIT2
                    id3.add(TPE1(encoding=3, text=artist))
                    id3.add(TIT2(encoding=3, text=title))
                    
                    # Save the ID3 tags to the WAV file
                    id3.save(track.path)
                    logging.info(f"Successfully wrote ID3 tags to WAV file: {track.path}")
                except Exception as e:
                    logging.debug(f"Failed to write metadata to WAV file {track.path}: {str(e)}")
            
            elif file_ext == '.wma':
                # WMA files
                audio = ASF(track.path)
                audio['Author'] = [artist]
                audio['Title'] = [title]
                audio.save()
            elif file_ext == '.mp4':
                raise ValueError("video files are not supported for metadata changes")
            
            elif file_ext in ['.m4a', '.aac']:
                # M4A/MP4/AAC files
                audio = MP4(track.path)
                audio['\xa9ART'] = [artist]
                audio['\xa9nam'] = [title]
                audio.save()
            
            else:
                # Generic approach for other formats
                try:
                    audio = File(track.path, easy=True)
                    if audio is None:
                        raise ValueError(f"Unsupported or corrupt file: {track.path}")
                    
                    if hasattr(audio, 'add_tags') and not audio.tags:
                        audio.add_tags()
                    
                    audio['artist'] = [artist]
                    audio['title'] = [title]
                    audio.save()
                except Exception as e:
                    logging.error(f"Error changing metadata for {track.path}: {str(e)}")
                    raise ValueError(f"Could not change metadata: {str(e)}")
        
        except Exception as e:
            logging.error(f"Failed to change metadata for {track.path}: {str(e)}")
            raise
        
        # Reflect changes in the Track object
        track.artist = artist
        track.title = title
        track.metadata = {
            'artist': artist,
            'title': title,
            'duration': track.metadata.get('duration', 0) if track.metadata else 0
        }

    @staticmethod
    def update_current_track_play_time(playlist, current_track):
        # Get current day of week (0=Monday, 6=Sunday in Python's weekday())
        # Convert to our mapping where 0=Sunday
        now = datetime.datetime.now()
        python_weekday = now.weekday()  # 0=Monday, 6=Sunday
        day_multiplier = (python_weekday + 1) % 7  # Convert to 0=Sunday, 1=Monday, etc.

        # Calculate current time of day in seconds since midnight
        current_seconds_in_day = now.hour * 3600 + now.minute * 60 + now.second

        seconds_in_day = 86400

        if current_track.play_time is not None:
            # If track's time-of-day is greater than current time-of-day,
            # the track must have started yesterday (e.g., started at 11:55 PM,
            # now it's 12:05 AM)
            if current_track.play_time > current_seconds_in_day:
                day_multiplier = (day_multiplier - 1) % 7  # Go back one day (wraps Sun->Sat)

            elapsed_seconds_in_week = day_multiplier * seconds_in_day
            current_track.play_time = elapsed_seconds_in_week + current_track.play_time
        else:
            return current_track
        return current_track
