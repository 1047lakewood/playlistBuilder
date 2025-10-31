import os
import sys
import argparse

def replace_paths_in_m3u8(folder_path):
    """
    Replace all instances of 'F:\' with 'G:\Shiurim\' in m3u8 files.
    
    Args:
        folder_path (str): Path to the folder containing m3u8 files
    
    Returns:
        int: Number of files processed
    """
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory.")
        return 0
    
    count = 0
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.m3u8'):
            file_path = os.path.join(folder_path, filename)
            
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
            except UnicodeDecodeError:
                # Try with a different encoding if UTF-8 fails
                try:
                    with open(file_path, 'r', encoding='latin-1') as file:
                        content = file.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue
            
            # Replace the paths
            new_content = content.replace('F:\\', 'G:\\Shiurim\\')
            
            # Only write if changes were made
            if new_content != content:
                try:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"Updated: {file_path}")
                    count += 1
                except Exception as e:
                    print(f"Error writing to {file_path}: {e}")
            else:
                print(f"No changes needed in: {file_path}")
    
    return count

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Replace paths in m3u8 files')
    parser.add_argument('folder', help='Folder containing m3u8 files')
    parser.add_argument('--recursive', '-r', action='store_true', 
                        help='Process subfolders recursively')
    
    args = parser.parse_args()
    
    if args.recursive:
        total_files = 0
        for root, _, _ in os.walk(args.folder):
            print(f"Processing folder: {root}")
            total_files += replace_paths_in_m3u8(root)
        print(f"Total files processed: {total_files}")
    else:
        processed = replace_paths_in_m3u8(args.folder)
        print(f"Total files processed: {processed}")

if __name__ == "__main__":
    main()