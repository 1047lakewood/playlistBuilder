from pydub import AudioSegment
from pydub.generators import Sine
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the output directory
output_dir = "output_audio_files"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    logging.info(f"Created directory: {output_dir}")

def create_tone_mp3(duration_seconds, filename):
    """Creates an MP3 file with a sine wave tone of a given duration."""
    try:
        # Duration in milliseconds
        duration_ms = duration_seconds * 1000
        
        # Create a 440 Hz sine wave tone
        tone = Sine(180).to_audio_segment(duration=duration_ms)
        
        # Reduce volume to make it "a bit of sound"
        tone = tone - 20

        # Export the segment to an MP3 file
        output_path = os.path.join(output_dir, filename)
        tone.export(output_path, format="mp3")
        logging.info(f"Successfully created {output_path} ({duration_seconds} seconds)")
    except Exception as e:
        logging.error(f"Failed to create {filename}: {e}")

if __name__ == "__main__":
    logging.info("Starting to create audio files...")

    # Define the files to be created: (duration_in_seconds, filename_prefix)
    files_to_create = [
        (60, "one_minute"),
        (30, "thirty_seconds"),
        (120, "two_minutes")
    ]

    # Create two of each file type
    for duration, prefix in files_to_create:
        for i in range(1, 3):
            filename = f"{prefix}_{i}.mp3"
            create_tone_mp3(duration, filename)

    logging.info("Finished creating all audio files.")
