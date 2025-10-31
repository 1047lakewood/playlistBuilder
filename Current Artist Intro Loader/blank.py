def create_blank_mp3(filename="blank.mp3", duration_seconds=1):
    """
    Creates a blank MP3 file with the specified duration.
    
    Args:
        filename: The name of the output MP3 file
        duration_seconds: Duration of the blank audio in seconds
    """
    try:
        from pydub import AudioSegment
        
        # Create a silent audio segment
        silence = AudioSegment.silent(duration=duration_seconds * 1000)  # duration in milliseconds
        
        # Export as MP3
        silence.export(filename, format="mp3")
        
        print(f"Successfully created blank MP3 file: {filename} ({duration_seconds} seconds)")
        
    except ImportError:
        print("This script requires the pydub library.")
        print("Install it using: pip install pydub")
        print("Note: You may also need to install ffmpeg for this to work.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        output_filename = sys.argv[1]
        duration = 1 if len(sys.argv) <= 2 else float(sys.argv[2])
        create_blank_mp3(output_filename, duration)
    else:
        create_blank_mp3()