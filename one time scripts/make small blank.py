import numpy as np
from scipy.io import wavfile
import os
import subprocess

def create_silent_mp3(filename="silent.mp3", duration=1.0):
    """Create a completely silent MP3 file."""
    # Sample rate (standard CD quality)
    sample_rate = 44100
    
    # Generate silent audio (all zeros)
    samples = np.zeros(int(duration * sample_rate), dtype=np.float32)
    
    # First create WAV file
    wav_filename = filename.replace(".mp3", ".wav")
    wavfile.write(wav_filename, sample_rate, samples)
    
    # Convert WAV to MP3 using ffmpeg
    subprocess.call([
        "ffmpeg", "-i", wav_filename,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        filename
    ])
    
    # Clean up the temporary WAV file
    os.remove(wav_filename)
    
    print(f"Created silent MP3 file: {filename}")

def create_near_silent_mp3(filename="near_silent.mp3", duration=1.0, amplitude=0.0001):
    """Create an MP3 file with nearly imperceptible sound."""
    # Sample rate (standard CD quality)
    sample_rate = 44100
    
    # Generate extremely quiet white noise
    samples = np.random.normal(0, amplitude, int(duration * sample_rate)).astype(np.float32)
    
    # First create WAV file
    wav_filename = filename.replace(".mp3", ".wav")
    wavfile.write(wav_filename, sample_rate, samples)
    
    # Convert WAV to MP3 using ffmpeg
    subprocess.call([
        "ffmpeg", "-i", wav_filename,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        filename
    ])
    
    # Clean up the temporary WAV file
    os.remove(wav_filename)
    
    print(f"Created near-silent MP3 file: {filename}")

if __name__ == "__main__":
    # Create a completely silent MP3
    create_silent_mp3()
    
    # Create an MP3 with barely perceptible sound
    create_near_silent_mp3()
    
    print("Done! Both files have been created.")