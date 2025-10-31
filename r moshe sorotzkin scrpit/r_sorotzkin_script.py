import os
import tkinter as tk
from tkinter import messagebox, filedialog
from pydub import AudioSegment
import glob
import re
import subprocess
import io
import pygame  # For responsive audio playback
import tempfile
import wave
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON

def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_latest_mp3():
    downloads = os.path.expanduser("~/Downloads")
    pattern = os.path.join(downloads, "*-RavMosheSoro*.mp3")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def sanitize_filename(text):
    """Remove or replace invalid filename characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', text.strip())

def select_file():
    return filedialog.askopenfilename(
        title="Select MP3 File",
        filetypes=[("MP3 files", "*.mp3")]
    )

def get_mp3_metadata(file_path):
    """Get metadata from MP3 file."""
    try:
        audio_file = MP3(file_path, ID3=ID3)
        metadata = {
            'title': str(audio_file.get('TIT2', [''])[0]),
            'artist': str(audio_file.get('TPE1', [''])[0]),
            'album': str(audio_file.get('TALB', [''])[0]),
            'year': str(audio_file.get('TDRC', [''])[0]),
            'genre': str(audio_file.get('TCON', [''])[0])
        }
        return metadata
    except Exception as e:
        print(f"Warning: Could not read metadata: {e}")
        return {'title': '', 'artist': '', 'album': '', 'year': '', 'genre': ''}

def set_mp3_metadata(file_path, metadata):
    """Set metadata on MP3 file."""
    try:
        audio_file = MP3(file_path, ID3=ID3)
        # Clear existing tags
        audio_file.delete()

        # Set new tags
        if metadata.get('title'):
            audio_file.tags.add(TIT2(encoding=3, text=metadata['title']))
        if metadata.get('artist'):
            audio_file.tags.add(TPE1(encoding=3, text=metadata['artist']))
        if metadata.get('album'):
            audio_file.tags.add(TALB(encoding=3, text=metadata['album']))
        if metadata.get('year'):
            audio_file.tags.add(TDRC(encoding=3, text=metadata['year']))
        if metadata.get('genre'):
            audio_file.tags.add(TCON(encoding=3, text=metadata['genre']))

        audio_file.save()
    except Exception as e:
        print(f"Warning: Could not set metadata: {e}")

def load_audio(file_path):
    try:
        return AudioSegment.from_mp3(file_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load MP3 file: {e}")
        return None

def init_pygame_mixer(audio):
    if audio is None:
        return
    sample_rate = audio.frame_rate
    channels = audio.channels
    pygame.mixer.quit()  # Safe to call even if not initialized
    pygame.mixer.init(frequency=sample_rate, size=-16, channels=channels, buffer=4096)

root = tk.Tk()
root.title("MP3 Processor")

# Check for ffmpeg
if not check_ffmpeg():
    messagebox.showerror("Error", "FFmpeg is not installed. Please install FFmpeg to use this application.")
    root.destroy()
    exit()

# Load initial MP3 file
file_path_var = tk.StringVar()
file_path_var.set(get_latest_mp3() or "")
if not file_path_var.get():
    file_path_var.set(select_file() or "")
    if not file_path_var.get():
        messagebox.showerror("Error", "No MP3 file selected.")
        root.destroy()
        exit()

audio = load_audio(file_path_var.get())
if audio is None:
    root.destroy()
    exit()

init_pygame_mixer(audio)  # Initialize mixer based on loaded audio

original_name = os.path.basename(file_path_var.get()).rsplit('.mp3', 1)[0]

# Get existing metadata
original_metadata = get_mp3_metadata(file_path_var.get())

# Variables
trim_var = tk.StringVar(value="0.0")
volume_var = tk.DoubleVar(value=0.0)
text_var = tk.StringVar()
year_var = tk.StringVar(value="5785")
output_name_var = tk.StringVar()
save_default_var = tk.BooleanVar(value=False)
save_dir_var = tk.StringVar(value=r"G:\Shiurim\R Moshe Sorotskin")

# Load default year
default_year_file = os.path.expanduser("~/.config/mp3_processor/default_year.txt")
os.makedirs(os.path.dirname(default_year_file), exist_ok=True)
if os.path.exists(default_year_file):
    with open(default_year_file, 'r') as f:
        year_var.set(f.read().strip())

# Function to update output name
def update_output_name(*args):
    add_text = text_var.get().strip()
    year = year_var.get().strip()
    new_name = original_name
    if add_text:
        new_name += f" {add_text}"
    if year:
        new_name += f" {year}"
    output_name_var.set(new_name)

text_var.trace("w", update_output_name)
year_var.trace("w", update_output_name)
update_output_name()  # Initial update

# GUI elements
loaded_label = tk.Label(root, text=f"Loaded File: {os.path.basename(file_path_var.get())}")
loaded_label.pack(pady=5)

def browse_mp3():
    new_path = select_file()
    if new_path:
        file_path_var.set(new_path)
        global audio, original_name, original_metadata
        audio = load_audio(new_path)
        if audio is None:
            return
        init_pygame_mixer(audio)  # Re-initialize mixer for new audio
        original_name = os.path.basename(new_path).rsplit('.mp3', 1)[0]
        original_metadata = get_mp3_metadata(new_path)
        loaded_label.config(text=f"Loaded File: {os.path.basename(new_path)}")
        update_output_name()

tk.Button(root, text="Browse MP3 File", command=browse_mp3).pack(pady=5)

# Trim section with stepper buttons
trim_frame = tk.Frame(root)
trim_frame.pack(pady=5)

tk.Label(trim_frame, text="Trim first seconds:").pack(side=tk.LEFT)

def increment_trim():
    try:
        current = float(trim_var.get())
        trim_var.set(f"{current + 0.3:.1f}")
    except ValueError:
        pass

def decrement_trim():
    try:
        current = float(trim_var.get())
        if current >= 0.3:
            trim_var.set(f"{current - 0.3:.1f}")
    except ValueError:
        pass

tk.Button(trim_frame, text="-", command=decrement_trim, width=2).pack(side=tk.LEFT)
tk.Entry(trim_frame, textvariable=trim_var, width=10).pack(side=tk.LEFT)
tk.Button(trim_frame, text="+", command=increment_trim, width=2).pack(side=tk.LEFT)

tk.Label(root, text="Volume adjustment (dB, negative to lower):").pack()
tk.Scale(root, from_=-20, to=0, orient=tk.HORIZONTAL, variable=volume_var, resolution=1, length=300).pack()  # Longer slider

# Preview button
def preview():
    try:
        trim_seconds = float(trim_var.get())
        if trim_seconds < 0:
            raise ValueError("Trim value cannot be negative.")
        trim_ms = int(trim_seconds * 1000)
        vol_db = volume_var.get()
        preview_dur_ms = 5000  # 5 seconds

        # Get the original audio's sample rate for debugging
        original_sample_rate = audio.frame_rate
        print(f"Original sample rate: {original_sample_rate} Hz")

        trimmed_audio = audio[trim_ms:]
        adjusted_audio = trimmed_audio + vol_db
        snippet = adjusted_audio[:preview_dur_ms]

        # Get cross-platform temp directory and save temp file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "preview.wav")

        # Export to temp file without resampling (keeps original rate)
        snippet.export(temp_file, format="wav")
        print(f"Temporary file saved at: {temp_file}")

        # Verify the exported WAV sample rate (debug)
        with wave.open(temp_file, 'rb') as wav_file:
            exported_sample_rate = wav_file.getframerate()
            print(f"Exported WAV sample rate: {exported_sample_rate} Hz")

        # Load and play the sound from the temp file
        sound = pygame.mixer.Sound(temp_file)
        channel = sound.play()

        # Non-blocking check for playback completion
        def check_playback():
            if not channel.get_busy():
                try:
                    os.remove(temp_file)  # Clean up temp file
                    print("Temporary file removed")
                except Exception as e:
                    print(f"Failed to remove temp file: {e}")
            else:
                root.after(10, check_playback)  # Check again after 10ms

        root.after(10, check_playback)  # Start checking playback status

    except ValueError as e:
        messagebox.showerror("Error", f"Invalid trim value: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"Preview failed: {e}")
tk.Button(root, text="Preview first 5 seconds", command=preview).pack(pady=10)

tk.Label(root, text="Additional text for filename:").pack()
tk.Entry(root, textvariable=text_var).pack()

tk.Label(root, text="Year to add:").pack()
tk.Entry(root, textvariable=year_var).pack()

tk.Label(root, text="Output Filename (without .mp3):").pack()
tk.Entry(root, textvariable=output_name_var, width=80).pack()  # Much bigger

tk.Checkbutton(root, text="Save this year as default", variable=save_default_var).pack(pady=5)

def select_save_dir():
    directory = filedialog.askdirectory(title="Select Save Directory")
    if directory:
        save_dir_var.set(directory)

tk.Label(root, text="Save Directory:").pack()
tk.Entry(root, textvariable=save_dir_var, width=50).pack()
tk.Button(root, text="Browse", command=select_save_dir).pack(pady=5)

def save_file():
    try:
        trim_seconds = float(trim_var.get())
        if trim_seconds < 0:
            raise ValueError("Trim value cannot be negative.")
        trim_ms = int(trim_seconds * 1000)
        vol_db = volume_var.get()
        year = sanitize_filename(year_var.get())
        output_name = sanitize_filename(output_name_var.get())
        save_dir = save_dir_var.get()

        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        trimmed_audio = audio[trim_ms:]
        adjusted_audio = trimmed_audio + vol_db

        new_name = f"{output_name}.mp3"
        save_path = os.path.join(save_dir, new_name)

        if os.path.exists(save_path):
            if not messagebox.askyesno("Confirm Overwrite", f"File {new_name} already exists. Overwrite?"):
                return

        adjusted_audio.export(save_path, format="mp3", codec="libmp3lame", parameters=["-q:a", "2"])

        # Set metadata
        new_metadata = original_metadata.copy()
        new_metadata['artist'] = 'Rav Moshe Sorotzkin'

        # Clean title by removing artist name variations and other common patterns
        clean_title = output_name
        artist_variations = [
            'Rav Moshe Sorotzkin',
            'R Moshe Sorotzkin',
            'Rav Moshe Soro',
            'R Moshe Soro',
            'Moshe Sorotzkin',
            'Rav Sorotzkin',


            '-R Moshe Soro',            'RavMosheSorotzkin',
            '-RavMosheSorotzkin'
        ]
        for variation in artist_variations:
            clean_title = re.sub(re.escape(variation), '', clean_title, flags=re.IGNORECASE)

        # Clean up extra spaces, dashes, and underscores
        clean_title = re.sub(r'\s+', ' ', clean_title.strip())
        clean_title = re.sub(r'^\s*-\s*|\s*-\s*$', '', clean_title)  # Remove leading/trailing dashes
        clean_title = re.sub(r'^\s*_\s*|\s*_\s*$', '', clean_title)  # Remove leading/trailing underscores
        clean_title = re.sub(r'^[-\s_]+|[-\s_]+$', '', clean_title)  # Remove any combination of leading/trailing dashes, spaces, underscores

        new_metadata['title'] = clean_title.strip()
        new_metadata['year'] = year_var.get().strip()
        set_mp3_metadata(save_path, new_metadata)

        # messagebox.showinfo("Success", f"File saved to: {save_path}")
        subprocess.run(["explorer", "/select,", save_path])
        if save_default_var.get():
            with open(default_year_file, 'w') as f:
                f.write(year)

        root.quit()
    except ValueError as e:
        messagebox.showerror("Error", f"Invalid input: {e}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save file: {e}")

tk.Button(root, text="Process and Save", command=save_file).pack(pady=10)

root.mainloop()