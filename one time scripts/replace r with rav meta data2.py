from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TPE1
import os
import concurrent.futures
import time
import argparse

def process_file(filepath):
    try:
        # Load the file - most efficient way to access tags
        audio = MP3(filepath, ID3=ID3)
        
        # Quick check if tags exist and have artist
        if not audio.tags or 'TPE1' not in audio.tags:
            return False
        
        # Get artist as string - faster string comparison
        artist = str(audio.tags['TPE1'])
        
        # Quick string check - only proceed if needed
        if not artist.lower().startswith("harav "):
            return False
            
        # Update the artist tag
        new_artist = "Rav " + artist[6:]
        audio.tags.add(TPE1(encoding=3, text=new_artist))
        audio.save()
        return True
            
    except Exception as e:
        # Slightly more informative error handling
        # print(f"Error processing {filepath}: {str(e)}")
        return False

def batch_process(input_folder, start_subfolder=None, max_workers=None, chunk_size=1000):
    start_time = time.time()
    success_count = 0
    file_count = 0
    start_subfolder_found = start_subfolder is None  # If no start_subfolder specified, start immediately
    current_subfolder = ""
    
    # Process in chunks for better memory management
    mp3_files = []
    
    # Find the absolute path of start_subfolder if specified
    start_subfolder_abs = None
    if start_subfolder:
        start_subfolder_abs = os.path.abspath(os.path.join(input_folder, start_subfolder))
        print(f"Will start processing from subfolder: {start_subfolder}")
        
    # Find MP3 files (optimized scanning)
    print(f"Scanning for MP3 files in {input_folder}...")
    for root, dirs, files in os.walk(input_folder):
        # Check if we've reached the starting subfolder
        if not start_subfolder_found:
            if os.path.abspath(root) == start_subfolder_abs or root.startswith(start_subfolder_abs + os.sep):
                start_subfolder_found = True
                print(f"Found starting subfolder: {root}")
            else:
                continue  # Skip this folder and continue searching
        
        # Verbose output about current subfolder
        if current_subfolder != root:
            current_subfolder = root
            print(f"\nProcessing subfolder: {current_subfolder}")
        
        # Process MP3 files in this folder
        folder_file_count = 0
        for filename in files:
            if filename.lower().endswith('.mp3'):
                mp3_files.append(os.path.join(root, filename))
                file_count += 1
                folder_file_count += 1
                
                # Process in chunks to avoid memory issues
                if len(mp3_files) >= chunk_size:
                    print(f"Processing batch of {len(mp3_files)} files...")
                    success_count += process_chunk(mp3_files, max_workers)
                    mp3_files = []
                    print(f"Processed {file_count} files so far, changed {success_count}")
        
        if folder_file_count > 0:
            print(f"Found {folder_file_count} MP3 files in {current_subfolder}")
    
    # Process remaining files
    if mp3_files:
        print(f"Processing final batch of {len(mp3_files)} files...")
        success_count += process_chunk(mp3_files, max_workers)
    
    elapsed_time = time.time() - start_time
    print(f"\nComplete! Modified {success_count} out of {file_count} files")
    print(f"Total time: {elapsed_time/60:.2f} minutes")
    
    if file_count > 0:
        print(f"Speed: {file_count/elapsed_time:.1f} files per second")

def process_chunk(file_list, max_workers):
    chunk_success = 0
    
    # Process files in parallel with minimal overhead
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_file, file_list)
        
        # Count successes
        for result in results:
            if result:
                chunk_success += 1
    
    return chunk_success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename artists starting with 'R ' to 'Rav ' in MP3 files")
    parser.add_argument("input_folder", help="Folder containing MP3 files (will search recursively)")
    parser.add_argument("-s", "--start-subfolder", 
                        help="Subfolder name to start processing from (relative to input_folder)")
    parser.add_argument("-w", "--workers", type=int, default=None, 
                        help="Number of worker processes (default: CPU count)")
    parser.add_argument("-c", "--chunk-size", type=int, default=1000,
                        help="Number of files to process in each batch (default: 1000)")
    args = parser.parse_args()
    
    if not os.path.isdir(args.input_folder):
        print(f"Error: {args.input_folder} is not a valid directory")
        exit(1)
        
    if args.start_subfolder and not os.path.isdir(os.path.join(args.input_folder, args.start_subfolder)):
        print(f"Error: Start subfolder '{args.start_subfolder}' not found in {args.input_folder}")
        exit(1)
        
    batch_process(args.input_folder, args.start_subfolder, max_workers=args.workers, chunk_size=args.chunk_size)