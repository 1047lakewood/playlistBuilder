from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TPE1
import os
import concurrent.futures
import time
import argparse

def process_file(filepath):
    try:
        # Load the file
        audio = MP3(filepath, ID3=ID3)
        
        # Check if ID3 tags exist
        if not audio.tags:
            return False, f"No ID3 tags in {filepath}"
        
        # Check artist tag
        artist_tag = audio.tags.get('TPE1')
        if not artist_tag:
            return False, f"No artist tag in {filepath}"
        
        artist = str(artist_tag)
        
        # Check if artist starts with "R "
        if artist.startswith("R "):
            # Replace "R " with "Rav "
            new_artist = "Rav " + artist[2:]
            audio.tags.add(TPE1(encoding=3, text=new_artist))
            audio.save()
            return True, f"Updated: {artist} → {new_artist} in {os.path.basename(filepath)}"
        else:
            return False, f"Artist doesn't start with 'R ' in {filepath}"
            
    except Exception as e:
        return False, f"Error processing {filepath}: {e}"

def batch_process(input_folder, max_workers=None):
    start_time = time.time()
    success_count = 0
    processed_count = 0
    
    # Get all MP3 files
    mp3_files = []
    for root, _, files in os.walk(input_folder):
        for filename in files:
            if filename.lower().endswith('.mp3'):
                mp3_files.append(os.path.join(root, filename))
    
    file_count = len(mp3_files)
    print(f"Found {file_count} MP3 files to process")
    
    # Process files in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_file, filepath) for filepath in mp3_files]
        
        for future in concurrent.futures.as_completed(futures):
            processed_count += 1
            success, message = future.result()
            
            if success:
                success_count += 1
                print(f"[{processed_count}/{file_count}] {message}")
            
            if processed_count % 100 == 0 or processed_count == file_count:
                elapsed = time.time() - start_time
                remaining = elapsed * (file_count - processed_count) / processed_count if processed_count > 0 else 0
                print(f"Progress: {processed_count}/{file_count} ({processed_count/file_count*100:.1f}%) - "
                      f"ETA: {remaining/60:.1f} minutes")
    
    elapsed_time = time.time() - start_time
    print(f"\nSummary:")
    print(f"Processed {file_count} files in {elapsed_time/60:.2f} minutes")
    print(f"Modified {success_count} files with artist names starting with 'R '")
    print(f"Average processing time: {elapsed_time/file_count:.4f} seconds per file")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename artists starting with 'R ' to 'Rav ' in MP3 files")
    parser.add_argument("input_folder", help="Folder containing MP3 files (will search recursively)")
    parser.add_argument("-w", "--workers", type=int, default=None, 
                        help="Number of worker processes (default: CPU count)")
    args = parser.parse_args()
    
    if not os.path.isdir(args.input_folder):
        print(f"Error: {args.input_folder} is not a valid directory")
        exit(1)
        
    print(f"Starting to process MP3 files in {args.input_folder} and all subfolders")
    batch_process(args.input_folder, max_workers=args.workers)