import os
import argparse
import mp3_metadata_api
import sys
import io
import traceback

# Set stdout to handle Unicode properly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def read_all_mp3_metadata(folder_path):
    """
    Read metadata from all MP3 files in a folder and its subfolders.
    
    Args:
        folder_path: Path to the folder containing MP3 files
    """
    # Find all MP3 files in the folder and subfolders
    mp3_files = []
    
    # Handle potential encoding issues when walking directories
    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.mp3'):
                    mp3_files.append(os.path.join(root, file))
    except UnicodeDecodeError as e:
        print(f"Error reading directory structure: {str(e).encode('ascii', 'replace').decode()}")
        print("Try running the script from a directory with simpler path names.")
        return
    
    total_files = len(mp3_files)
    print(f"Found {total_files} MP3 files to read")
    
    for index, file_path in enumerate(mp3_files, 1):
        try:
            # Get the filename without extension
            filename = os.path.basename(file_path)
            
            # Log the current operation
            print(f"File {index}/{total_files}: Reading metadata for {filename}")
            
            # Read metadata
            metadata = mp3_metadata_api.read(file_path)
            print(f"  Metadata: {metadata}")
            
        except UnicodeEncodeError:
            # Handle encoding errors more gracefully
            safe_path = file_path.encode('ascii', 'replace').decode()
            print(f"File {index}/{total_files}: Warning - Filename contains characters that can't be displayed in console")
            print(f"  File path (ASCII only): {safe_path}")
            try:
                metadata = mp3_metadata_api.read(file_path)
                print(f"  Metadata retrieved successfully")
            except Exception as e:
                print(f"  Error reading metadata: {str(e).encode('ascii', 'replace').decode()}")
        except Exception as e:
            # For other errors, provide a safe error message
            safe_path = file_path.encode('ascii', 'replace').decode()
            safe_error = str(e).encode('ascii', 'replace').decode()
            print(f"Error reading metadata for file {safe_path}: {safe_error}")
    
    print(f"Read metadata from {total_files} MP3 files successfully")

def process_mp3_files(folder_path, title_separator_count, custom_artist=None):
    """
    Process all MP3 files in a folder and its subfolders.
    
    Args:
        folder_path: Path to the folder containing MP3 files
        title_separator_count: The number of separators (underscores or spaces) after which to extract the title
        custom_artist: Optional custom artist name to use instead of folder name
    """
    # Get the artist name from the custom value or folder name
    folder_name = os.path.basename(os.path.normpath(folder_path))
    artist_name = custom_artist if custom_artist else folder_name
    
    print(f"Using artist name: '{artist_name}'")
    print(f"Using title separator count: {title_separator_count}")
    
    # Find all MP3 files in the folder and subfolders
    mp3_files = []
    
    # Handle potential encoding issues when walking directories
    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.mp3'):
                    mp3_files.append(os.path.join(root, file))
    except UnicodeDecodeError as e:
        print(f"Error reading directory structure: {str(e).encode('ascii', 'replace').decode()}")
        print("Try running the script from a directory with simpler path names.")
        return
    
    total_files = len(mp3_files)
    print(f"Found {total_files} MP3 files to process")
    
    for index, file_path in enumerate(mp3_files, 1):
        try:
            # Get the filename without extension
            filename = os.path.basename(file_path)
            filename_without_ext = os.path.splitext(filename)[0]
            
            # Replace hyphens with underscores
            normalized_filename = filename_without_ext.replace('-', '_')
            
            # Split by both underscores and spaces and count separators
            parts = []
            current_part = ""
            separator_positions = []
            
            for i, char in enumerate(normalized_filename):
                if char == '_' or char == ' ':
                    if current_part:  # Only add non-empty parts
                        parts.append(current_part)
                        current_part = ""
                    separator_positions.append(i)
                else:
                    current_part += char
            
            # Add the last part if not empty
            if current_part:
                parts.append(current_part)
            
           
        
            
            # Determine title start position
            if title_separator_count < len(parts):
                # Extract title parts based on the requested separator count
                title_parts = parts[title_separator_count:]
                
                # Check for ZTL or SHLITA as first word and adjust title if found
                if title_parts and title_parts[0].upper() in ["ZTL", "SHLITA"]:
                    print(f"  Found '{title_parts[0]}' as first word after separator - skipping it for title")
                    title_parts = title_parts[1:]  # Skip the first word
                
                # Format the title (capitalize each word)
                title = ' '.join(title_parts).title() if title_parts else filename_without_ext.replace('_', ' ').title()
            else:
                # If not enough parts, use the whole filename as title
                title = filename_without_ext.replace('_', ' ').title()
            
            # Log the current operation (safely)
            try:
                print(f"File {index}/{total_files}: Setting metadata for {filename}")
                print(f"  Title will be set to: {title}")
            except UnicodeEncodeError:
                safe_file = filename.encode('ascii', 'replace').decode()
                safe_title = title.encode('ascii', 'replace').decode()
                print(f"File {index}/{total_files}: Setting metadata for {safe_file}")
                print(f"  Title will be set to: {safe_title}")
            
            # Read current metadata (optional, for verification)
            try:
                current_metadata = mp3_metadata_api.read(file_path)
                print(f"  Current metadata: {current_metadata}")
            except Exception as meta_e:
                print(f"  Error reading current metadata: {str(meta_e).encode('ascii', 'replace').decode()}")
                continue  # Skip to next file if we can't read metadata
            
            # Set the new metadata
            try:
                mp3_metadata_api.set(file_path, artist_name, title)
            except Exception as set_e:
                print(f"  Error setting metadata: {str(set_e).encode('ascii', 'replace').decode()}")
                continue  # Skip to next file if we can't set metadata
            
            # Verify the changes (optional)
            try:
                updated_metadata = mp3_metadata_api.read(file_path)
                print(f"  Updated metadata: {updated_metadata}")
            except Exception as verify_e:
                print(f"  Error verifying updated metadata: {str(verify_e).encode('ascii', 'replace').decode()}")
            
        except UnicodeEncodeError:
            # Handle encoding errors more gracefully
            safe_path = file_path.encode('ascii', 'replace').decode()
            print(f"File {index}/{total_files}: Warning - Filename contains characters that can't be displayed in console")
            print(f"  File path (ASCII only): {safe_path}")
            
            try:
                # Still try to process the file
                filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
                
                # Process normally but with minimal output
                normalized_filename = filename_without_ext.replace('-', '_')
                
                # Split by both underscores and spaces
                parts = []
                current_part = ""
                
                for char in normalized_filename:
                    if char == '_' or char == ' ':
                        if current_part:
                            parts.append(current_part)
                            current_part = ""
                    else:
                        current_part += char
                
                if current_part:
                    parts.append(current_part)
                
                # Determine title
                if title_separator_count < len(parts):
                    title_parts = parts[title_separator_count:]
                    
                    # Check for ZTL or SHLITA as first word and adjust
                    if title_parts and title_parts[0].upper() in ["ZTL", "SHLITA"]:
                        title_parts = title_parts[1:]  # Skip the first word
                    
                    title = ' '.join(title_parts).title() if title_parts else filename_without_ext.replace('_', ' ').title()
                else:
                    title = filename_without_ext.replace('_', ' ').title()
                
                # Set the metadata
                mp3_metadata_api.set(file_path, artist_name, title)
                print(f"  Metadata updated successfully")
                
            except Exception as sub_e:
                print(f"  Error processing file: {str(sub_e).encode('ascii', 'replace').decode()}")
                
        except Exception as e:
            # For other errors, provide a safe error message and print traceback for debugging
            safe_path = file_path.encode('ascii', 'replace').decode()
            safe_error = str(e).encode('ascii', 'replace').decode()
            print(f"Error processing file {safe_path}: {safe_error}")
            print("Traceback:")
            traceback.print_exc(file=sys.stdout)
    
    print(f"Processed {total_files} MP3 files successfully")

if __name__ == "__main__":
    # Set UTF-8 mode for Windows if possible
    if sys.platform == 'win32':
        # Force UTF-8 encoding in Windows
        try:
            # For Python 3.7+
            os.system('chcp 65001 > nul')
        except:
            pass

    parser = argparse.ArgumentParser(description="Update MP3 metadata in bulk")
    parser.add_argument("folder_path", help="Path to the folder containing MP3 files")
    parser.add_argument("-t", type=int, default=None, 
                        help="Number of separators (underscores or spaces) after which to extract the title. If not provided, will use the number of words in the folder name.")
    parser.add_argument("-a", "--artist", type=str, default=None,
                        help="Custom artist name to use instead of folder name")
    parser.add_argument("--read-only", action="store_true", 
                        help="Only read metadata without making changes")
    
    args = parser.parse_args()
    
    # Handle potential encoding issues with folder path
    try:
        # Automatically determine -t based on folder name if not explicitly provided
        if args.t is None:
            folder_name = os.path.basename(os.path.normpath(args.folder_path))
            word_count = len(folder_name.split())
            args.t = word_count
            print(f"Automatically determined -t value: {args.t} based on folder name: '{folder_name}'")
        
        if args.read_only:
            read_all_mp3_metadata(args.folder_path)
        else:
            process_mp3_files(args.folder_path, args.t, args.artist)
    except UnicodeDecodeError as e:
        print(f"Error with folder path encoding: {str(e).encode('ascii', 'replace').decode()}")
        print("Try running the script from a directory with simpler path names or specify full path with double quotes.")
    except Exception as e:
        print(f"Unexpected error: {str(e).encode('ascii', 'replace').decode()}")
        print("Traceback:")
        traceback.print_exc(file=sys.stdout)