
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import shutil

class M3U8PathReplacerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8 Path Replacer & File Mover")
        self.root.resizable(True, True)

        # Configure column/row weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Create main frame with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)

        # --- Folder Selection ---
        folder_frame = ttk.LabelFrame(main_frame, text="M3U8 Folder Selection", padding="10")
        folder_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        folder_frame.columnconfigure(1, weight=1)

        self.folder_path = tk.StringVar()
        ttk.Label(folder_frame, text="M3U8 Folder:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(folder_frame, text="Browse...", command=self.browse_m3u8_folder).grid(row=0, column=2, padx=5, pady=5)

        # Recursive option
        self.recursive = tk.BooleanVar(value=False)
        ttk.Checkbutton(folder_frame, text="Process subfolders recursively", variable=self.recursive).grid(
            row=1, column=0, columnspan=3, sticky="w", padx=5, pady=5
        )

        # --- Path Replacement & Moving ---
        replace_frame = ttk.LabelFrame(main_frame, text="Path Replacement & File Moving", padding="10")
        replace_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        replace_frame.columnconfigure(1, weight=1) # Make entry expand

        # Find Path
        ttk.Label(replace_frame, text="Find Path:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.find_text = tk.StringVar(value="F:\\") # Example default
        ttk.Entry(replace_frame, textvariable=self.find_text).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(replace_frame, text="Browse...", command=self.browse_find_path).grid(row=0, column=2, padx=5, pady=5)

        # Replace Path
        ttk.Label(replace_frame, text="Replace With:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.replace_text = tk.StringVar(value="G:\\Shiurim\\") # Example default
        ttk.Entry(replace_frame, textvariable=self.replace_text).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(replace_frame, text="Browse...", command=self.browse_replace_path).grid(row=1, column=2, padx=5, pady=5)

        # Move Files Option
        self.move_files_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(replace_frame, text="Move media files from 'Find Path' to 'Replace With' path", variable=self.move_files_var).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=5, pady=5
        )

        # --- Processing Controls ---
        control_frame = ttk.Frame(main_frame, padding="5")
        control_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        control_frame.columnconfigure(0, weight=1) # Push button to the right

        self.start_button = ttk.Button(control_frame, text="Start Processing", command=self.start_processing)
        self.start_button.grid(row=0, column=1, padx=5, pady=5) # Place button on the right

        # --- Log Area ---
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Make the log expandable
        main_frame.rowconfigure(3, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, width=60, height=10)
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scrollbar.set)

        # --- Progress Bar ---
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=4, column=0, sticky="ew", padx=5, pady=10)

        # --- Status Bar & Exit ---
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=5, column=0, sticky="ew", padx=5, pady=5)
        bottom_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(bottom_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        ttk.Button(bottom_frame, text="Exit", command=root.destroy).grid(row=0, column=1, sticky="e", padx=5)

        # Initialize other variables
        self.processing_thread = None
        self.total_files = 0
        self.processed_files = 0
        self.files_changed = 0
        self.files_moved = 0

        # Set appropriate window size to fit content
        self.root.update_idletasks()
        self.root.geometry("")
        self.root.minsize(550, 500)

    def _format_path_with_backslashes(self, path, ensure_trailing_slash=False):
        """Formats a path string to use backslashes, optionally ensuring a trailing backslash."""
        if not path:
            return ""
        # Replace all forward slashes with backslashes
        formatted_path = path.replace('/', '\\')
        # Ensure trailing backslash if requested and path is not just a drive root (like C:)
        if ensure_trailing_slash and not formatted_path.endswith('\\'):
             # Avoid double backslashes if path is already e.g., 'C:\\'
             # But add if it's 'C:'
             if len(formatted_path) > 1 and formatted_path.endswith(':'):
                  formatted_path += '\\'
             elif len(formatted_path) > 0: # For non-drive paths or just '/' -> '\'
                  formatted_path += '\\'

        return formatted_path


    def browse_m3u8_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder Containing M3U8 Files")
        if folder_path:
            # Format the path with backslashes for display in the Entry
            display_path = self._format_path_with_backslashes(folder_path)
            self.folder_path.set(display_path)

    def browse_find_path(self):
        path = filedialog.askdirectory(title="Select Base Path to Find (Directory)")
        if path:
            # Format the path with backslashes and ensure trailing backslash for display
            display_path = self._format_path_with_backslashes(path, ensure_trailing_slash=True)
            self.find_text.set(display_path)

    def browse_replace_path(self):
        path = filedialog.askdirectory(title="Select Base Path to Replace With (Directory)")
        if path:
            # Format the path with backslashes and ensure trailing backslash for display
            display_path = self._format_path_with_backslashes(path, ensure_trailing_slash=True)
            self.replace_text.set(display_path)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_progress(self):
        if self.total_files > 0:
            progress = (self.processed_files / self.total_files) * 100
            self.progress_var.set(progress)
            status_msg = f"Processed: {self.processed_files}/{self.total_files} | M3U8 Changed: {self.files_changed}"
            # Check the state of the checkbox directly, not the temporary variable in process_folders
            if self.move_files_var.get():
                 status_msg += f" | Files Moved: {self.files_moved}"
            self.status_var.set(status_msg)
        else:
            self.progress_var.set(0)
            self.status_var.set("No .m3u8 files found")

    def count_m3u8_files(self, folder_path):
        """Count the total number of m3u8 files to process."""
        count = 0
        if not os.path.isdir(folder_path):
             # Log this earlier if needed, but validation should catch it
             return 0

        try:
            if self.recursive.get():
                for root_dir, _, files in os.walk(folder_path):
                    count += sum(1 for f in files if f.lower().endswith('.m3u8'))
            else:
                 count = sum(1 for f in os.listdir(folder_path)
                             if f.lower().endswith('.m3u8') and os.path.isfile(os.path.join(folder_path, f)))
        except OSError as e:
            self.log(f"Error accessing folder {folder_path} during counting: {e}")
            messagebox.showerror("Folder Access Error", f"Could not access folder to count files:\n{folder_path}\n{e}")
            return 0 # Return 0 if folder is inaccessible

        return count

    def replace_paths_in_m3u8(self, folder_path):
        """Replace path strings in m3u8 files and optionally move files."""
        if not os.path.isdir(folder_path):
            self.log(f"Skipping: {folder_path} is not a valid directory.")
            return

        # Normalize paths from entry fields for reliable comparison and operations
        try:
            find_text_raw = self.find_text.get()
            replace_text_raw = self.replace_text.get()

            # Basic check; more robust validation is in process_folders
            if not find_text_raw or not replace_text_raw:
                 self.log("Error: Find/Replace paths are empty. Skipping folder.")
                 return

            # Use os.path.normpath to handle mixed slashes correctly internally
            # and add separator logic *after* normalization for reliable prefix matching.
            find_path = os.path.normpath(find_text_raw)
            replace_path = os.path.normpath(replace_text_raw)

            # Ensure find path ends with separator for correct startswith check
            if not find_path.endswith(os.sep):
                find_path += os.sep
            # Ensure replace path ends with separator for correct joining
            if not replace_path.endswith(os.sep):
                replace_path += os.sep

        except Exception as e:
            self.log(f"Error normalizing internal paths from GUI: {e}")
            return # Stop processing this folder if paths are invalid

        move_files = self.move_files_var.get()

        self.log(f"\nProcessing M3U8 files in: {folder_path}")
        if move_files:
            self.log(f"  Attempting to move files from normalized '{find_path}' to normalized '{replace_path}'")
        else:
            self.log(f"  Replacing normalized path prefix '{find_path}' with normalized '{replace_path}'")

        try:
            items_in_folder = os.listdir(folder_path)
        except OSError as e:
            self.log(f"Error listing directory {folder_path}: {e}")
            return # Cannot process this folder

        for filename in items_in_folder:
            if filename.lower().endswith('.m3u8'):
                file_path = os.path.join(folder_path, filename)
                if not os.path.isfile(file_path):
                    continue

                self.log(f"  Processing M3U8: {filename}")
                original_content_lines = []
                modified_content_lines = []
                file_changed_flag = False
                encoding_to_use = 'utf-8' # Default encoding

                # Read the file content line by line
                try:
                    with open(file_path, 'r', encoding=encoding_to_use) as file:
                        original_content_lines = file.readlines()
                except UnicodeDecodeError:
                    # Try with a different encoding if UTF-8 fails
                    self.log(f"  Warning: UTF-8 decoding failed for {filename}. Trying latin-1.")
                    encoding_to_use = 'latin-1'
                    try:
                        with open(file_path, 'r', encoding=encoding_to_use) as file:
                            original_content_lines = file.readlines()
                    except Exception as e:
                        self.log(f"  Error reading {file_path} with {encoding_to_use}: {e}")
                        # Increment counters and skip this file
                        self.processed_files += 1
                        self.update_progress()
                        continue
                except Exception as e:
                    self.log(f"  Error reading {file_path}: {e}")
                    # Increment counters and skip this file
                    self.processed_files += 1
                    self.update_progress()
                    continue

                # Process lines for replacement and moving
                for line_num, line in enumerate(original_content_lines):
                    stripped_line = line.strip()
                    # Skip comments and empty lines
                    if not stripped_line or stripped_line.startswith('#'):
                        modified_content_lines.append(line)
                        continue

                    # Normalize the path found in the M3U8 file for comparison
                    try:
                         # Use normpath to handle mixed slashes in the M3U8 file path
                         # Use normcase for case-insensitive comparison (important on Windows)
                         line_path_normed = os.path.normcase(os.path.normpath(stripped_line))
                         find_path_normed = os.path.normcase(find_path) # normpath + os.sep added above

                    except Exception:
                        # Handle potential errors if the line contains invalid path chars during normalization
                        self.log(f"  Warning: Skipping invalid path on line {line_num+1} in {filename}: {stripped_line}")
                        modified_content_lines.append(line) # Keep original line
                        continue

                    # Check if the normalized line path starts with the normalized find path
                    if line_path_normed.startswith(find_path_normed):
                        # Path matches the 'Find Path' prefix
                        old_full_path = os.path.normpath(stripped_line) # Get the normalized original path
                        # Calculate the relative path part
                        # Need to be careful if original path had different case than find_path
                        # Best to get the relative path *after* the matched part of the original line
                        # Find the index where the find_path ends in the original stripped line (case-insensitive)
                        try:
                             # Use a temp normcase version of stripped_line to find the index
                             lower_stripped = stripped_line.lower() if sys.platform == 'win32' else stripped_line # Only lower on Windows for normcase effect
                             lower_find_path_raw = self.find_text.get().lower() if sys.platform == 'win32' else self.find_text.get()
                             # Find the end index of the raw find path in the raw stripped line (case-insensitive search)
                             find_path_end_index = lower_stripped.find(lower_find_path_raw)
                             if find_path_end_index != -1:
                                 # Extract the relative part from the ORIGINAL stripped line
                                 relative_path_part = stripped_line[find_path_end_index + len(self.find_text.get()):]
                                 # Clean up leading separators if necessary
                                 relative_path_part = relative_path_part.lstrip('/\\')
                             else:
                                 # Fallback: Calculate relative path from normalized paths (less precise for original format)
                                 relative_path_part = old_full_path[len(find_path):] # This uses the normalized find_path length

                        except Exception as e:
                             self.log(f"  Error calculating relative path for '{stripped_line}': {e}")
                             modified_content_lines.append(line)
                             continue # Skip this line

                        # Construct the new path using the normalized replace path and the calculated relative part
                        new_full_path_norm = os.path.normpath(os.path.join(replace_path, relative_path_part))

                        moved_successfully = False
                        if move_files:
                            # Attempt to move the physical file
                            try:
                                if os.path.exists(old_full_path):
                                    # Ensure destination directory exists
                                    new_dir = os.path.dirname(new_full_path_norm)
                                    os.makedirs(new_dir, exist_ok=True)

                                    self.log(f"    Moving: '{old_full_path}' -> '{new_full_path_norm}'")
                                    shutil.move(old_full_path, new_full_path_norm)
                                    self.files_moved += 1
                                    moved_successfully = True
                                    # self.log(f"    Move successful.")
                                else:
                                    self.log(f"    Skipping move (Source not found): {old_full_path}")
                                    # If source doesn't exist, update the path in the playlist anyway,
                                    # assuming the new location is where it *should* be or will be placed later.
                                    # Treat this as "success" for the path update step.
                                    moved_successfully = True

                            except OSError as e:
                                self.log(f"    Error moving file {old_full_path}: {e}")
                                # If move failed, keep the original line in the playlist
                                modified_content_lines.append(line)
                                continue # Skip to next line

                        # Update the line in the playlist content ONLY IF moving was successful OR if moving was disabled
                        if not move_files or moved_successfully:
                             # Format the new path for the playlist line using backslashes, as requested
                             new_line_path_formatted = self._format_path_with_backslashes(new_full_path_norm)

                             # Preserve original line ending
                             line_ending = ''
                             if line.endswith('\r\n'):
                                 line_ending = '\r\n'
                             elif line.endswith('\n'):
                                 line_ending = '\n'

                             # Check if the path *string* actually changed before marking file as changed
                             # Compare the stripped original line with the newly formatted path string
                             if stripped_line != new_line_path_formatted:
                                 modified_content_lines.append(new_line_path_formatted + line_ending)
                                 file_changed_flag = True
                             else:
                                 # Path didn't change after replacement/formatting (e.g., find=replace, or already had correct path)
                                 modified_content_lines.append(line) # Append original line
                                 # No change flag needed
                                 # self.log("    Path already correct or no change: " + stripped_line)


                    else:
                        # Line doesn't start with find_path, keep original line
                        modified_content_lines.append(line)

                # Write the modified content back if changes were made
                if file_changed_flag:
                    try:
                        with open(file_path, 'w', encoding=encoding_to_use) as file:
                            file.writelines(modified_content_lines)
                        self.log(f"  Updated M3U8 file paths.")
                        self.files_changed += 1
                    except Exception as e:
                        self.log(f"  Error writing updated M3U8 to {file_path}: {e}")
                else:
                    self.log(f"  No path changes needed in M3U8 file.")

                # Always increment processed files after handling a file, even if skipped or error
                self.processed_files += 1
                self.update_progress()
                self.log(f"  Finished M3U8: {filename}")


    def process_folders(self):
        """Process all folders according to settings."""
        m3u8_folder_path = self.folder_path.get()
        find_text = self.find_text.get()
        replace_text = self.replace_text.get()
        move_files_enabled_initially = self.move_files_var.get() # Store initial intent

        # --- Validation ---
        if not m3u8_folder_path or not os.path.isdir(m3u8_folder_path):
            messagebox.showerror("Error", "Please select a valid M3U8 Folder.")
            self.start_button.config(state=tk.NORMAL)
            self.status_var.set("Validation failed")
            return

        if not find_text:
            messagebox.showerror("Error", "Please enter or browse for the 'Find Path'.")
            self.start_button.config(state=tk.NORMAL)
            self.status_var.set("Validation failed")
            return
        if not replace_text:
            messagebox.showerror("Error", "Please enter or browse for the 'Replace With' path.")
            self.start_button.config(state=tk.NORMAL)
            self.status_var.set("Validation failed")
            return

        # Normalize paths for comparison
        # Use normpath on the raw input strings for robust comparison
        try:
            norm_find = os.path.normpath(find_text)
            norm_replace = os.path.normpath(replace_text)
        except Exception as e:
             messagebox.showerror("Path Error", f"Could not normalize Find/Replace paths for validation: {e}")
             self.start_button.config(state=tk.NORMAL)
             self.status_var.set("Path validation failed")
             return


        if move_files_enabled_initially and os.path.normcase(norm_find) == os.path.normcase(norm_replace):
             messagebox.showwarning("Warning", "Find path and Replace path are the same (ignoring case/slashes).\nCannot move files to the same location. File moving will be skipped, only path replacement will occur.")
             # Temporarily disable moving for this run by setting the variable
             # The log message below will reflect the *actual* action taken
             self.move_files_var.set(False)

        # --- Start Processing ---
        self.start_button.config(state=tk.DISABLED) # Disable button during processing
        self.log_text.delete(1.0, tk.END) # Clear the log

        # Reset counters
        self.processed_files = 0
        self.files_changed = 0
        self.files_moved = 0

        # Count files before starting
        self.total_files = self.count_m3u8_files(m3u8_folder_path)
        if self.total_files == 0:
            self.log("No .m3u8 files found in the selected folder(s). Nothing to do.")
            self.status_var.set("No .m3u8 files found")
            self.start_button.config(state=tk.NORMAL)
            self.progress_var.set(100) # Mark progress as complete
            return


        self.log(f"Starting processing...")
        self.log(f"M3U8 Folder: {m3u8_folder_path}")
        self.log(f"Recursive: {self.recursive.get()}")
        self.log(f"Find Path (GUI): {find_text}") # Log GUI input format
        self.log(f"Replace With (GUI): {replace_text}") # Log GUI input format
        self.log(f"Move Files: {self.move_files_var.get()}") # Log the actual state of the variable

        self.log(f"Found {self.total_files} .m3u8 files to process.")
        self.update_progress()


        try:
            if self.recursive.get():
                for root_dir, _, _ in os.walk(m3u8_folder_path):
                    # Pass the current root directory to process files within it
                    self.replace_paths_in_m3u8(root_dir)
            else:
                self.replace_paths_in_m3u8(m3u8_folder_path)

            self.log(f"\n--- Processing Summary ---")
            self.log(f"Total M3U8 files processed: {self.processed_files}")
            self.log(f"M3U8 files updated: {self.files_changed}")
            # Check the state AFTER potential disabling due to find==replace
            if self.move_files_var.get() or (move_files_enabled_initially and os.path.normcase(norm_find) == os.path.normcase(norm_replace)):
                 # If moving was requested OR disabled because paths matched, report move count
                 self.log(f"Media files moved: {self.files_moved}")
            self.log(f"Processing complete.")
            self.status_var.set("Processing completed")

        except Exception as e:
             self.log(f"\n--- An unexpected error occurred during processing ---")
             self.log(f"Error: {e}")
             import traceback
             self.log(traceback.format_exc())
             self.status_var.set("Error during processing")
             messagebox.showerror("Processing Error", f"An unexpected error occurred:\n{e}")
        finally:
             self.start_button.config(state=tk.NORMAL) # Re-enable button
             self.progress_var.set(100) # Ensure progress bar shows complete
             # Re-enable the move files checkbox in case it was disabled internally
             # We can only re-enable it AFTER the thread finishes.
             # self.move_files_var.set(move_files_enabled_initially) # This should ideally run on the main thread

             # Refresh final status message (will use current counts)
             self.update_progress()
             if self.processed_files < self.total_files:
                 self.status_var.set(f"Completed (processed {self.processed_files}/{self.total_files} M3U8 files)")


    def start_processing(self):
        """Start the processing in a separate thread to keep the UI responsive."""
        if self.processing_thread and self.processing_thread.is_alive():
            messagebox.showwarning("In Progress", "Processing is already running.")
            return

        # Run validation checks before starting thread
        m3u8_folder_path = self.folder_path.get()
        find_text = self.find_text.get()
        replace_text = self.replace_text.get()

        if not m3u8_folder_path or not os.path.isdir(m3u8_folder_path):
            messagebox.showerror("Error", "Please select a valid M3U8 Folder.")
            return
        if not find_text:
            messagebox.showerror("Error", "Please enter or browse for the 'Find Path'.")
            return
        if not replace_text:
            messagebox.showerror("Error", "Please enter or browse for the 'Replace With' path.")
            return

        # If validation passes, start the thread
        self.processing_thread = threading.Thread(target=self.process_folders, daemon=True)
        self.processing_thread.start()

def main():
    root = tk.Tk()
    app = M3U8PathReplacerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()