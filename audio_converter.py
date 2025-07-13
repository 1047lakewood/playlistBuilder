import os
import tempfile
import shutil
import tkinter as tk
from tkinter import messagebox
from pydub import AudioSegment
import logging
import time
import subprocess
import sys
import re
from mutagen.id3 import ID3, APIC, TPE1, TIT2, TALB, TCON, TDRC, TRCK, TYER, TPOS, TCOM, TPUB, TENC
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen import File
from mutagen.id3 import ID3NoHeaderError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class AudioConverter:
    """Utility class for converting audio files to MP3 format"""
    
    @staticmethod
    def is_format_supported_by_pygame(file_path):
        """Check if the file format is natively supported by pygame"""
        # Pygame natively supports MP3, WAV, and OGG
        # But there can be issues with certain WAV files and other formats
        supported_extensions = ['.mp3', '.wav', '.ogg']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        return file_ext in supported_extensions
    
    @staticmethod
    def convert_to_mp3(file_path, delete_original=False):
        """
        Convert an audio file to MP3 format and transfer metadata
        
        Args:
            file_path: Path to the audio file to convert
            delete_original: Whether to delete the original file after conversion
            
        Returns:
            str: Path to the converted MP3 file, or None if conversion failed
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logging.error(f"File does not exist: {file_path}")
                return None
                
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # If already MP3, just return the path
            if file_ext == '.mp3':
                return file_path
                
            # Determine output path (same directory, same name, but .mp3 extension)
            output_path = os.path.splitext(file_path)[0] + '.mp3'
            
            # Extract metadata from original file with enhanced extraction methods
            original_metadata = {}
            try:
                # First try using mutagen.File for general metadata extraction
                audio_file = File(file_path)
                if audio_file is not None:
                    # Try to get common metadata tags
                    if hasattr(audio_file, 'tags') and audio_file.tags:
                        for key in audio_file.tags.keys():
                            original_metadata[key] = str(audio_file.tags[key])
                    
                    # For files with different tag structures
                    if hasattr(audio_file, 'info'):
                        if hasattr(audio_file.info, 'length'):
                            original_metadata['length'] = audio_file.info.length
                        
                        # Try to extract common tags with different methods
                        for tag_method in ['artist', 'title', 'album', 'genre', 'date', 'composer', 'year', 'tracknumber']:
                            if hasattr(audio_file, tag_method):
                                original_metadata[tag_method] = getattr(audio_file, tag_method)
                            elif hasattr(audio_file, 'get') and callable(audio_file.get):
                                try:
                                    value = audio_file.get(tag_method)
                                    if value:
                                        original_metadata[tag_method] = value
                                except:
                                    pass
                
                # Try format-specific extraction methods for more complete metadata
                if file_ext == '.mp3':
                    try:
                        mp3_file = MP3(file_path)
                        if mp3_file.tags:
                            # Extract ID3 tags
                            for key in mp3_file.tags.keys():
                                tag_value = str(mp3_file.tags[key])
                                original_metadata[key] = tag_value
                                # Map common ID3 frames to standard names
                                if key.startswith('TPE1'):  # Artist
                                    original_metadata['artist'] = tag_value
                                elif key.startswith('TIT2'):  # Title
                                    original_metadata['title'] = tag_value
                                elif key.startswith('TALB'):  # Album
                                    original_metadata['album'] = tag_value
                                elif key.startswith('TCON'):  # Genre
                                    original_metadata['genre'] = tag_value
                                elif key.startswith('TDRC'):  # Recording date
                                    original_metadata['date'] = tag_value
                    except Exception as e:
                        logging.warning(f"MP3-specific metadata extraction failed: {str(e)}")
                
                elif file_ext == '.flac':
                    try:
                        from mutagen.flac import FLAC
                        flac_file = FLAC(file_path)
                        for key, value in flac_file.items():
                            if value:  # Only add non-empty values
                                original_metadata[key] = value[0] if isinstance(value, list) and value else value
                    except Exception as e:
                        logging.warning(f"FLAC-specific metadata extraction failed: {str(e)}")
                
                elif file_ext in ['.m4a', '.mp4', '.aac']:
                    try:
                        mp4_file = MP4(file_path)
                        # Map MP4 tags to standard names
                        tag_mapping = {
                            '\xa9ART': 'artist',
                            '\xa9nam': 'title',
                            '\xa9alb': 'album',
                            '\xa9gen': 'genre',
                            '\xa9day': 'date',
                            'aART': 'album_artist',
                            'trkn': 'tracknumber'
                        }
                        for mp4_tag, std_tag in tag_mapping.items():
                            if mp4_tag in mp4_file:
                                value = mp4_file[mp4_tag]
                                if value:
                                    original_metadata[std_tag] = value[0] if isinstance(value, list) and value else value
                    except Exception as e:
                        logging.warning(f"MP4-specific metadata extraction failed: {str(e)}")
                
                elif file_ext == '.wma':
                    try:
                        wma_file = ASF(file_path)
                        # Map WMA tags to standard names
                        tag_mapping = {
                            'Author': 'artist',
                            'Title': 'title',
                            'WM/AlbumTitle': 'album',
                            'WM/Genre': 'genre',
                            'WM/Year': 'date',
                            'WM/AlbumArtist': 'album_artist',
                            'WM/TrackNumber': 'tracknumber'
                        }
                        for wma_tag, std_tag in tag_mapping.items():
                            if wma_tag in wma_file:
                                value = wma_file[wma_tag]
                                if value:
                                    original_metadata[std_tag] = str(value[0]) if isinstance(value, list) and value else str(value)
                    except Exception as e:
                        logging.warning(f"WMA-specific metadata extraction failed: {str(e)}")
                
                # Try to extract filename-based metadata as fallback
                if 'title' not in original_metadata or not original_metadata['title']:
                    filename = os.path.basename(file_path)
                    title = os.path.splitext(filename)[0]
                    # Clean up the filename (remove numbers, underscores, etc.)
                    title = re.sub(r'^\d+\s*[-_.]\s*', '', title)  # Remove leading numbers and separators
                    title = re.sub(r'[-_.]', ' ', title)  # Replace separators with spaces
                    original_metadata['title'] = title
                    
                # Try to extract artist from directory structure as last resort
                if 'artist' not in original_metadata or not original_metadata['artist']:
                    dir_path = os.path.dirname(file_path)
                    dir_name = os.path.basename(dir_path)
                    if dir_name and dir_name != '':
                        original_metadata['artist'] = dir_name
                
                logging.info(f"Extracted metadata from original file: {original_metadata}")
            except Exception as e:
                logging.warning(f"Error extracting metadata from original file: {str(e)}")
            
            # First try using pydub
            pydub_success = False
            try:
                # Load the audio file based on its format
                if file_ext == '.wav':
                    audio = AudioSegment.from_wav(file_path)
                elif file_ext == '.m4a' or file_ext == '.mp4' or file_ext == '.aac':
                    audio = AudioSegment.from_file(file_path, format="m4a")
                elif file_ext == '.wma':
                    audio = AudioSegment.from_file(file_path, format="wma")
                elif file_ext == '.flac':
                    audio = AudioSegment.from_file(file_path, format="flac")
                elif file_ext == '.ogg':
                    audio = AudioSegment.from_file(file_path, format="ogg")
                else:
                    # Try generic loading for other formats
                    audio = AudioSegment.from_file(file_path)
                    
                # Export as MP3
                audio.export(output_path, format="mp3", bitrate="320k")
                pydub_success = True
                logging.info(f"Successfully converted using pydub: {file_path} -> {output_path}")
            except Exception as e:
                logging.warning(f"Pydub conversion failed: {str(e)}. Trying FFmpeg directly...")
            
            # If pydub fails, try direct FFmpeg conversion
            if not pydub_success:
                try:
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Prepare FFmpeg command
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-y',  # Overwrite output file if it exists
                        '-i', file_path,  # Input file
                        '-vn',  # No video
                        '-ar', '44100',  # Audio sample rate
                        '-ac', '2',  # Stereo
                        '-b:a', '320k',  # Bitrate
                        '-f', 'mp3',  # Output format
                        output_path  # Output file
                    ]
                    
                    # Run FFmpeg with additional error handling
                    logging.info(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
                    process = subprocess.Popen(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    # Capture output
                    stdout, stderr = process.communicate()
                    
                    # Check if conversion was successful
                    if process.returncode != 0:
                        logging.error(f"FFmpeg error: {stderr}")
                        
                        # Try one more time with different options for corrupted files
                        logging.info("Trying FFmpeg with error recovery options...")
                        ffmpeg_recovery_cmd = [
                            'ffmpeg',
                            '-y',
                            '-err_detect', 'ignore_err',  # Ignore errors
                            '-i', file_path,
                            '-vn',
                            '-ar', '44100',
                            '-ac', '2',
                            '-b:a', '320k',
                            '-f', 'mp3',
                            output_path
                        ]
                        
                        process = subprocess.Popen(
                            ffmpeg_recovery_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True
                        )
                        
                        stdout, stderr = process.communicate()
                        
                        if process.returncode != 0:
                            logging.error(f"FFmpeg recovery attempt failed: {stderr}")
                            return None
                    
                    logging.info(f"Successfully converted using direct FFmpeg: {file_path} -> {output_path}")
                except Exception as e:
                    logging.error(f"FFmpeg direct conversion failed: {str(e)}")
                    return None
            
            # Check if output file exists and has content
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logging.error(f"Conversion failed: Output file is missing or empty: {output_path}")
                return None
            
            # Apply metadata to the new MP3 file with comprehensive tag mapping
            try:
                if original_metadata:
                    # First try using EasyID3 for basic tags (simpler interface)
                    try:
                        mp3_tags = EasyID3(output_path)
                    except Exception as e:
                        logging.warning(f"Error opening MP3 tags, creating new: {str(e)}")
                        # Create ID3 tag if it doesn't exist
                        try:
                            mp3_tags = EasyID3()
                            mp3_tags.save(output_path)
                        except Exception as e2:
                            logging.warning(f"Error creating new ID3 tags: {str(e2)}")
                            mp3_tags = None
                    
                    if mp3_tags:
                        # Extended tag mapping to capture more metadata
                        tag_mapping = {
                            'artist': 'artist',
                            'title': 'title',
                            'album': 'album',
                            'genre': 'genre',
                            'date': 'date',
                            'year': 'date',
                            'tracknumber': 'tracknumber',
                            'discnumber': 'discnumber',
                            'composer': 'composer',
                            'album_artist': 'albumartist',
                            'bpm': 'bpm',
                            'compilation': 'compilation',
                            'copyright': 'copyright',
                            'encodedby': 'encodedby',
                            'lyricist': 'lyricist',
                            'organization': 'organization',
                            'performer': 'performer',
                            'conductor': 'conductor',
                            'arranger': 'arranger',
                            'author': 'author',
                            'isrc': 'isrc'
                        }
                        
                        # Apply mapped tags
                        for orig_tag, id3_tag in tag_mapping.items():
                            if orig_tag in original_metadata and original_metadata[orig_tag]:
                                try:
                                    mp3_tags[id3_tag] = str(original_metadata[orig_tag])
                                except Exception as e:
                                    logging.warning(f"Error setting {id3_tag} tag: {str(e)}")
                        
                        # Save tags
                        try:
                            mp3_tags.save()
                            logging.info(f"Applied basic metadata to converted MP3 file: {output_path}")
                        except Exception as e:
                            logging.warning(f"Error saving EasyID3 tags: {str(e)}")
                    
                    # For more complex tags or album art, use the full ID3 interface
                    try:
                        # Open with full ID3 interface
                        id3 = ID3(output_path)
                        
                        # Add standard tags that might not be supported by EasyID3
                        if 'artist' in original_metadata and original_metadata['artist']:
                            id3.add(TPE1(encoding=3, text=str(original_metadata['artist'])))
                        if 'title' in original_metadata and original_metadata['title']:
                            id3.add(TIT2(encoding=3, text=str(original_metadata['title'])))
                        if 'album' in original_metadata and original_metadata['album']:
                            id3.add(TALB(encoding=3, text=str(original_metadata['album'])))
                        if 'genre' in original_metadata and original_metadata['genre']:
                            id3.add(TCON(encoding=3, text=str(original_metadata['genre'])))
                        if 'date' in original_metadata and original_metadata['date']:
                            id3.add(TDRC(encoding=3, text=str(original_metadata['date'])))
                        if 'year' in original_metadata and original_metadata['year']:
                            id3.add(TYER(encoding=3, text=str(original_metadata['year'])))
                        if 'tracknumber' in original_metadata and original_metadata['tracknumber']:
                            id3.add(TRCK(encoding=3, text=str(original_metadata['tracknumber'])))
                        if 'composer' in original_metadata and original_metadata['composer']:
                            id3.add(TCOM(encoding=3, text=str(original_metadata['composer'])))
                        
                        # Try to extract and transfer album art if present in original file
                        try:
                            original_file = File(file_path)
                            if hasattr(original_file, 'pictures') and original_file.pictures:
                                # For FLAC and similar formats with picture attribute
                                for picture in original_file.pictures:
                                    id3.add(APIC(
                                        encoding=3,
                                        mime=picture.mime,
                                        type=3,  # Cover image
                                        desc='Cover',
                                        data=picture.data
                                    ))
                            elif file_ext == '.mp3':
                                # For MP3 files, try to extract APIC frames
                                try:
                                    orig_id3 = ID3(file_path)
                                    for key in orig_id3.keys():
                                        if key.startswith('APIC'):
                                            id3.add(orig_id3[key])
                                except Exception as e:
                                    logging.warning(f"Error extracting album art from MP3: {str(e)}")
                        except Exception as e:
                            logging.warning(f"Error transferring album art: {str(e)}")
                        
                        # Save the enhanced tags
                        id3.save(output_path)
                        logging.info(f"Applied enhanced metadata to converted MP3 file: {output_path}")
                    except Exception as e:
                        logging.warning(f"Error applying enhanced ID3 tags: {str(e)}")
                        
                else:
                    # If no metadata was extracted, try to use filename as title
                    try:
                        mp3_tags = EasyID3(output_path)
                    except Exception:
                        try:
                            mp3_tags = EasyID3()
                            mp3_tags.save(output_path)
                        except Exception as e:
                            logging.warning(f"Error creating ID3 tags for filename-based title: {str(e)}")
                            mp3_tags = None
                    
                    if mp3_tags:
                        try:
                            # Use filename as title
                            filename = os.path.basename(file_path)
                            title = os.path.splitext(filename)[0]
                            # Clean up the filename
                            title = re.sub(r'^\d+\s*[-_.]\s*', '', title)  # Remove leading numbers and separators
                            title = re.sub(r'[-_.]', ' ', title)  # Replace separators with spaces
                            mp3_tags['title'] = title
                            
                            # Try to use directory name as artist
                            dir_path = os.path.dirname(file_path)
                            dir_name = os.path.basename(dir_path)
                            if dir_name and dir_name != '':
                                mp3_tags['artist'] = dir_name
                                
                            mp3_tags.save()
                            logging.info(f"Applied filename as title to MP3 file: {title}")
                        except Exception as e:
                            logging.warning(f"Error setting filename as title: {str(e)}")
            except Exception as e:
                logging.warning(f"Error applying metadata to MP3 file: {str(e)}")
            
            # Ensure file is fully written before attempting to delete original
            time.sleep(1.0)  # Increased delay to ensure file is fully written
            
            # Delete original if requested
            if delete_original and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                max_attempts = 5  # Increased number of attempts
                for attempt in range(max_attempts):
                    try:
                        # Ensure file handles are closed
                        import gc
                        gc.collect()
                        
                        # Try to delete the file
                        os.remove(file_path)
                        logging.info(f"Deleted original file: {file_path}")
                        break
                    except PermissionError:
                        # If permission error, wait longer and try again
                        if attempt < max_attempts - 1:
                            logging.warning(f"Permission error on delete attempt {attempt+1}. Waiting longer...")
                            time.sleep(2)  # Longer wait for permission issues
                    except Exception as e:
                        if attempt < max_attempts - 1:
                            logging.warning(f"Delete attempt {attempt+1} failed: {str(e)}. Retrying...")
                            time.sleep(1)  # Wait before retrying
                        else:
                            logging.warning(f"Failed to delete original file after {max_attempts} attempts: {file_path}. Error: {str(e)}")
                            # As a last resort, try using system commands
                            try:
                                if sys.platform == 'win32':
                                    os.system(f'del /f /q "{file_path}"')
                                else:  # Unix-like
                                    os.system(f'rm -f "{file_path}"')
                                logging.info(f"Attempted to delete using system command: {file_path}")
                            except Exception as e2:
                                logging.warning(f"System command delete failed: {str(e2)}")
            
            return output_path
            
        except Exception as e:
            logging.error(f"Error converting {file_path} to MP3: {str(e)}")
            # Try one last desperate attempt with direct system command if everything else failed
            try:
                logging.info(f"Attempting last-resort conversion with system FFmpeg command...")
                if sys.platform == 'win32':
                    cmd = f'ffmpeg -y -i "{file_path}" -vn -ar 44100 -ac 2 -b:a 320k "{output_path}"'
                else:  # Unix-like
                    cmd = f'ffmpeg -y -i "{file_path}" -vn -ar 44100 -ac 2 -b:a 320k "{output_path}"'
                
                os.system(cmd)
                
                # Check if the output file was created and has content
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logging.info(f"Last-resort conversion successful: {output_path}")
                    return output_path
            except Exception as e2:
                logging.error(f"Last-resort conversion failed: {str(e2)}")
            
            return None
    
    @staticmethod
    def offer_conversion_dialog(parent, file_path, track):
        """
        Show a dialog offering to convert the file to MP3
        
        Args:
            parent: Parent window
            file_path: Path to the file to convert
            track: Track object to update if conversion is successful
            
        Returns:
            str: Path to the converted file if successful, None otherwise
        """
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Create a custom dialog
        dialog = tk.Toplevel(parent)
        dialog.title("Convert Audio File")
        dialog.geometry("450x200")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center the dialog on the parent window
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        dialog_width = 450
        dialog_height = 200
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Add padding
        frame = tk.Frame(dialog, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        # Message
        message = f"The file format '{file_ext}' may not play correctly.\n\nWould you like to convert '{file_name}' to MP3?"
        label = tk.Label(frame, text=message, wraplength=400, justify="left")
        label.pack(pady=(0, 20))
        
        # Delete original checkbox
        delete_var = tk.BooleanVar(value=True)
        delete_check = tk.Checkbutton(frame, text="Delete original file after conversion", variable=delete_var)
        delete_check.pack(anchor="w", pady=(0, 20))
        
        # Result variable
        result = [None]
        
        # Buttons
        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x")
        
        def on_convert():
            try:
                # Show conversion in progress
                for btn in [convert_btn, cancel_btn, try_anyway_btn]:
                    btn.config(state="disabled")
                label.config(text="Converting... Please wait.")
                dialog.update()
                
                # Convert the file
                converted_path = AudioConverter.convert_to_mp3(file_path, delete_var.get())
                
                if converted_path and os.path.exists(converted_path):
                    # Update the track's path
                    track.path = converted_path
                    result[0] = converted_path
                    messagebox.showinfo("Conversion Complete", f"Successfully converted to MP3.", parent=dialog)
                    dialog.destroy()
                else:
                    messagebox.showerror("Conversion Failed", "Failed to convert the file.", parent=dialog)
                    # Re-enable buttons
                    for btn in [convert_btn, cancel_btn, try_anyway_btn]:
                        btn.config(state="normal")
                    label.config(text=message)
            except Exception as e:
                messagebox.showerror("Conversion Error", f"Error during conversion: {str(e)}", parent=dialog)
                # Re-enable buttons
                for btn in [convert_btn, cancel_btn, try_anyway_btn]:
                    btn.config(state="normal")
                label.config(text=message)
        
        def on_try_anyway():
            result[0] = file_path  # Use original path
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        convert_btn = tk.Button(button_frame, text="Convert to MP3", command=on_convert, width=15)
        convert_btn.pack(side="left", padx=5)
        
        try_anyway_btn = tk.Button(button_frame, text="Try Anyway", command=on_try_anyway, width=15)
        try_anyway_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=15)
        cancel_btn.pack(side="left", padx=5)
        
        # Wait for the dialog to close
        parent.wait_window(dialog)
        
        return result[0]
