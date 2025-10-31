import os
import tkinter as tk
from tkinter import messagebox, filedialog
from pydub import AudioSegment
import glob
import re
import subprocess
import io
import pygame
import tempfile
import wave
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

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
    pygame.mixer.quit()
    pygame.mixer.init(frequency=sample_rate, size=-16, channels=channels, buffer=4096)

def update_waveform():
    if audio is None:
        return
    try:
        trim_seconds = float(trim_var.get())
        if trim_seconds < 0:
            raise ValueError("Trim value cannot be negative.")
        trim_ms = int(trim_seconds * 1000)
        vol_db = volume_var.get()

        trimmed_audio = audio[trim_ms:]
        adjusted_audio = trimmed_audio + vol_db

        samples = np.array(adjusted_audio.get_array_of_samples())
        sample_rate = adjusted_audio.frame_rate
        duration = len(adjusted_audio) / 1000.0

        # Downsample to ~10,000 points for performance
        target_samples = 10000
        if len(samples) > target_samples:
            step = len(samples) // target_samples
            samples = samples[::step]
            time = np.linspace(0, duration, num=len(samples))
        else:
            time = np.linspace(0, duration, num=len(samples))

        max_amplitude = np.iinfo(np.int16).max
        normalized_samples = samples / max_amplitude

        ax.clear()
        # Mimic Audacity's bar-like waveform using stem plot
        markerline, stemlines, baseline = ax.stem(time, normalized_samples, linefmt='b-', markerfmt='none', basefmt='k-')
        plt.setp(stemlines, 'color', 'blue')
        plt.setp(baseline, 'color', 'black', 'linewidth', 0.5)

        # Highlight clipping
        clipping = np.abs(normalized_samples) > 1.0
        if np.any(clipping):
            ax.plot(time[clipping], normalized_samples[clipping], 'r.', label='Clipping')

        ax.set_title(f"Waveform (Full Audio: {duration/60:.1f} minutes)")
        ax.set_xlabel("Time (minutes)")
        ax.set_ylabel("Amplitude")
        ax.set_ylim(-1.2, 1.2)
        ax.set_xticks(np.linspace(0, duration, 5))
        ax.set_xticklabels([f"{t/60:.1f}" for t in np.linspace(0, duration, 5)])
        ax.grid(True)
        ax.legend()

        canvas.draw()
    except Exception as e:
        print(f"Waveform update failed: {e}")

root = tk.Tk()
root.title("MP3 Processor for Rav Moshe Sorotzkin")

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

init_pygame_mixer(audio)
original_name = os.path.basename(file_path_var.get()).rsplit('.mp3', 1)[0]

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
update_output_name()

# GUI elements
loaded_label = tk.Label(root, text=f"Loaded File: {os.path.basename(file_path_var.get())}")
loaded_label.pack(pady=5)

def browse_mp3():
    new_path = select_file()
    if new_path:
        file_path_var.set(new_path)
        global audio, original_name
        audio = load_audio(new_path)
        if audio is None:
            return
        init_pygame_mixer(audio)
        original_name = os.path.basename(new_path).rsplit('.mp3', 1)[0]
        loaded_label.config(text=f"Loaded File: {os.path.basename(new_path)}")
        update_output_name()
        update_waveform()  # Update waveform on new file load

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
tk.Scale(root, from_=-20, to=0, orient=tk.HORIZONTAL, variable=volume_var, resolution=1, length=300).pack()

# Waveform plot setup
plot_frame = tk.Frame(root)
plot_frame.pack(pady=10, fill=tk.BOTH, expand=True)
fig, ax = plt.subplots(figsize=(10, 2))  # Wider for better Audacity-like view
canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Initial waveform update
trim_var.trace("w", lambda *args: update_waveform())
volume_var.trace("w", lambda *args: update_waveform())
update_waveform()  # Load waveform on startup

# Preview button
def preview():
    try:
        trim_seconds = float(trim_var.get())
        if trim_seconds < 0:
            raise ValueError("Trim value cannot be negative.")
        trim_ms = int(trim_seconds * 1000)
        vol_db = volume_var.get()
        preview_dur_ms = 5000

        trimmed_audio = audio[trim_ms:]
        adjusted_audio = trimmed_audio + vol_db
        snippet = adjusted_audio[:preview_dur_ms]

        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "preview.wav")
        snippet.export(temp_file, format="wav")
        print(f"Temporary file saved at: {temp_file}")

        with wave.open(temp_file, 'rb') as wav_file:
            exported_sample_rate = wav_file.getframerate()
            print(f"Exported WAV sample rate: {exported_sample_rate} Hz")

        sound = pygame.mixer.Sound(temp_file)
        channel = sound.play()

        def check_playback():
            if not channel.get_busy():
                try:
                    os.remove(temp_file)
                    print("Temporary file removed")
                except Exception as e:
                    print(f"Failed to remove temp file: {e}")
            else:
                root.after(10, check_playback)

        root.after(10, check_playback)

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
tk.Entry(root, textvariable=output_name_var, width=80).pack()

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

        adjusted_audio.export(save_path, format="mp3", codec="libmp3lame", parameters=["-q:a", 2])
        messagebox.showinfo("Success", f"File saved to: {save_path}")

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