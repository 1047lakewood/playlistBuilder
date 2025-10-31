import os
import subprocess
import tempfile
import shutil

def read(filePath):
    """
    Reads the metadata (Artist and Title) from an MP3 file.

    Args:
        filePath (str): Path to the MP3 file.

    Returns:
        tuple: (fileName, artist, title)
    """
    artist = ""
    title = ""
    
    # Use ffprobe to extract each tag separately with explicit output format
    try:
        # Get artist
        artist_result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "format_tags=artist",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filePath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            check=True
        )
        
        # Get title
        title_result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "format_tags=title",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filePath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            check=True
        )
        
        # Decode the outputs carefully
        artist = artist_result.stdout.decode('utf-8', errors='replace').strip().replace('\x00', '')
        title = title_result.stdout.decode('utf-8', errors='replace').strip().replace('\x00', '')
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(f"Error reading metadata from {filePath}: {error_msg}") from e

    fileName = os.path.basename(filePath)
    return (fileName, artist, title)

def set(filePath, newArtist, newTitle):
    """
    Writes new metadata (Artist and Title) to an MP3 file.
    The function uses ffmpeg to copy the streams and embed the new tags,
    writing to a temporary file which then replaces the original.

    Args:
        filePath (str): Path to the MP3 file.
        newArtist (str): New Artist value.
        newTitle (str): New Title value.
    """
    # Create a temporary file in the same directory.
    temp_dir = os.path.dirname(filePath)
    with tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=".mp3") as tmp:
        temp_file = tmp.name

    try:
        # Use ffmpeg to set new metadata while copying codecs to avoid re-encoding.
        subprocess.run(
            [
                "ffmpeg",
                "-i", filePath,
                "-metadata", f"artist={newArtist}",
                "-metadata", f"title={newTitle}",
                "-codec", "copy",
                "-y",  # Overwrite output file if it exists.
                temp_file
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Changed to handle binary output
            check=True
        )
    except subprocess.CalledProcessError as e:
        os.remove(temp_file)
        error_msg = e.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(f"Error setting metadata for {filePath}: {error_msg}") from e

    # Replace the original file with the new file.
    os.replace(temp_file, filePath)

def test_with_sample(sample_mp3_path=None):
    """
    Tests the metadata read and set functions on a sample MP3 file.
    If no sample file is provided, creates a test MP3 file with ffmpeg.

    Args:
        sample_mp3_path (str, optional): Path to an existing MP3 file for testing.
                                        If None, a temporary file will be created.

    Returns:
        bool: True if the test passes, False otherwise.
    """
    created_temp_file = False
    temp_file = None

    try:
        # If no sample file provided, create a simple MP3 file with ffmpeg
        if not sample_mp3_path:
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, "test_sample.mp3")
            created_temp_file = True
            
            print("Creating test MP3 file...")
            # Create a simple silent MP3 file with initial metadata
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-f", "lavfi",  # Use libavfilter virtual input
                    "-i", "anullsrc=r=44100:cl=mono",  # Generate silence
                    "-t", "1",  # 1 second duration
                    "-metadata", "artist=Original Artist",
                    "-metadata", "title=Original Title",
                    "-y",  # Overwrite output file if it exists
                    temp_file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Changed to handle binary output
                check=True
            )
            
            # Verify the file was created successfully
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                raise RuntimeError("Failed to create test MP3 file or file is empty")
                
            sample_mp3_path = temp_file
            print(f"Created temporary test file: {sample_mp3_path}")
            
            # Directly check the metadata with ffprobe for verification
            verify_cmd = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format_tags", sample_mp3_path],
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=False
            )
            print("Direct ffprobe verification of initial metadata:")
            print(verify_cmd.stdout.decode('utf-8', errors='replace'))
        
        # First, read the initial metadata
        print("\nTesting read() function on initial metadata...")
        file_name, artist, title = read(sample_mp3_path)
        print(f"Initial metadata: File: {file_name}, Artist: '{artist}', Title: '{title}'")
        
        # Set new metadata
        new_artist = "Test2 Artist"
        new_title = "Test2 Title"
        print(f"\nSetting new metadata - Artist: '{new_artist}', Title: '{new_title}'")
        set(sample_mp3_path, new_artist, new_title)
        
        # Directly check the metadata with ffprobe after setting
        verify_cmd = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format_tags", sample_mp3_path],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=False
        )
        print("Direct ffprobe verification after setting metadata:")
        print(verify_cmd.stdout.decode('utf-8', errors='replace'))
        
        # Read the updated metadata
        print("\nTesting read() function on updated metadata...")
        _, updated_artist, updated_title = read(sample_mp3_path)
        print(f"Updated metadata: Artist: '{updated_artist}', Title: '{updated_title}'")
        
        # Verify the metadata was set correctly
        if updated_artist == new_artist and updated_title == new_title:
            print("\n✅ Test passed! Metadata was successfully updated and read.")
            return True
        else:
            print("\n❌ Test failed! Metadata was not updated correctly.")
            if updated_artist != new_artist:
                print(f"  - Expected artist '{new_artist}', got '{updated_artist}'")
            if updated_title != new_title:
                print(f"  - Expected title '{new_title}', got '{updated_title}'")
            return False
            
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()  # Print the full traceback for better debugging
        return False
        
    finally:
        # Clean up the temporary file if we created one
        if created_temp_file and temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print(f"\nRemoved temporary test file: {temp_file}")
            except Exception as e:
                print(f"Warning: Could not remove temporary file {temp_file}: {str(e)}")

if __name__ == "__main__":
    # Example usage:
    # 1. Use with an existing MP3 file
    # test_with_sample(r"C:\path\to\your\sample.mp3")  # Note the 'r' prefix for raw strings
    
    # 2. Create and use a temporary test file
    
    test_with_sample(r"G:\Shiurim\R Avigdor Miller\TEST FOLDER01\OUTPUT\00_571 - Existing In Hashem+s Memory.mp3")
    
    # 2. Create and use a temporary test file
   # test_with_sample()
