import os
import tempfile
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1
import io

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
    
    try:
        audio = MP3(filePath)
        
        # Extract artist from ID3 tags
        if 'TPE1' in audio:
            artist = str(audio['TPE1'])
        
        # Extract title from ID3 tags
        if 'TIT2' in audio:
            title = str(audio['TIT2'])
            
    except Exception as e:
        raise RuntimeError(f"Error reading metadata from {filePath}: {str(e)}") from e

    fileName = os.path.basename(filePath)
    return (fileName, artist, title)

def set(filePath, newArtist, newTitle):
    """
    Writes new metadata (Artist and Title) to an MP3 file.

    Args:
        filePath (str): Path to the MP3 file.
        newArtist (str): New Artist value.
        newTitle (str): New Title value.
    """
    try:
        # Load existing ID3 tags or create new ones if they don't exist
        try:
            tags = ID3(filePath)
        except:
            tags = ID3()
        
        # Set new artist and title
        tags['TPE1'] = TPE1(encoding=3, text=newArtist)
        tags['TIT2'] = TIT2(encoding=3, text=newTitle)
        
        # Save the tags directly to the file
        tags.save(filePath)
        
    except Exception as e:
        raise RuntimeError(f"Error setting metadata for {filePath}: {str(e)}") from e

def test_with_sample(sample_mp3_path=None):
    """
    Tests the metadata read and set functions on a sample MP3 file.
    If no sample file is provided, creates a test MP3 file.

    Args:
        sample_mp3_path (str, optional): Path to an existing MP3 file for testing.
                                        If None, a temporary file will be created.

    Returns:
        bool: True if the test passes, False otherwise.
    """
    created_temp_file = False
    temp_file = None

    try:
        # If no sample file provided, create a simple MP3 file
        if not sample_mp3_path:
            import tempfile
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1
            
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, "test_sample.mp3")
            created_temp_file = True
            
            print("Creating test MP3 file...")
            
            # Create a minimal MP3 file (1 frame of silence)
            with open(temp_file, 'wb') as f:
                # This is a minimal valid MP3 file (essentially silence)
                silence_mp3 = b'\xFF\xFB\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                f.write(silence_mp3)
            
            # Add metadata to the file
            tags = ID3()
            tags['TPE1'] = TPE1(encoding=3, text="Original Artist")
            tags['TIT2'] = TIT2(encoding=3, text="Original Title")
            tags.save(temp_file)
            
            sample_mp3_path = temp_file
            print(f"Created temporary test file: {sample_mp3_path}")
            
            # Verify metadata with mutagen
            verify_audio = MP3(sample_mp3_path)
            print("Verification of initial metadata:")
            print(f"Tags: {verify_audio}")
        
        # First, read the initial metadata
        print("\nTesting read() function on initial metadata...")
        file_name, artist, title = read(sample_mp3_path)
        print(f"Initial metadata: File: {file_name}, Artist: '{artist}', Title: '{title}'")
        
        # Set new metadata
        new_artist = "Test2 Artist"
        new_title = "Test2 Title"
        print(f"\nSetting new metadata - Artist: '{new_artist}', Title: '{new_title}'")
        set(sample_mp3_path, new_artist, new_title)
        
        # Verify metadata with mutagen after setting
        verify_audio = MP3(sample_mp3_path)
        print("Verification after setting metadata:")
        print(f"Tags: {verify_audio}")
        
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
    # test_with_sample(r"C:\path\to\your\sample.mp3")
    
    test_with_sample(r"G:\Shiurim\R Avigdor Miller\TEST FOLDER01\OUTPUT\00_571 - Existing In Hashem+s Memory.mp3")
    
    # 2. Create and use a temporary test file
    # test_with_sample()