import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import re
import time # To measure performance if needed

# --- Core Logic ---

def find_m3u8_files_in_folder(folder_path):
    """Recursively finds all .m3u8 files in a given folder."""
    m3u8_files = []
    if not os.path.isdir(folder_path):
        return []
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.lower().endswith(".m3u8"):
                m3u8_files.append(os.path.join(root, filename))
    return m3u8_files

def get_existing_urls(playlist_path):
    """Reads an existing M3U8 file and returns a set of all URLs found."""
    existing_urls = set()
    if not os.path.exists(playlist_path):
        return existing_urls # Return empty set if file doesn't exist

    try:
        # Use utf-8 encoding, common for M3U8, ignore errors for robustness
        with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                # Simple check: is it likely a URL?
                if line and not line.startswith('#'):
                     # More robust check might be needed depending on M3U8 variations
                     if line.startswith('http://') or line.startswith('https://') or '/' in line:
                         existing_urls.add(line)
    except Exception as e:
        print(f"Warning: Could not read existing URLs from {playlist_path}: {e}")
        # Decide if this should be a fatal error or just a warning
        # Returning empty set means duplicates might be re-added if reading fails
    return existing_urls


def find_matching_streams(playlist_paths, keywords_str):
    """
    Reads M3U8 playlists, finds streams matching ANY of the keywords (case-insensitive),
    and returns a list of unique (EXTINF, URL) tuples found in this run.

    Args:
        playlist_paths (list): A list of paths to the input M3U8 files.
        keywords_str (str): A comma-separated string of keywords.

    Returns:
        tuple: (list_of_tuples, error_message_string_or_None)
               list_of_tuples contains unique (extinf_line, url_line) found in this run.
    """
    # Process keywords: split, strip, lowercase, remove empty
    keywords_lower = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]

    if not keywords_lower:
        return [], "Keyword list cannot be empty after processing."

    found_streams_this_run = []
    # Use a set to track URLs found *just in this processing run* for efficiency
    seen_urls_this_run = set()
    extinf_line = None
    error_messages = []

    print(f"Searching for any of keywords: {keywords_lower}")

    for playlist_path in playlist_paths:
        try:
            # Use utf-8 encoding, common for M3U8, ignore errors for robustness
            with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                print(f"Processing file: {playlist_path}") # Debugging output
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()
                    if not line: # Skip empty lines
                        continue

                    if line.startswith('#EXTINF:'):
                        # Store the potential EXTINF line
                        extinf_line = line
                    # Check if line is likely a URL/stream path
                    elif extinf_line and line and not line.startswith('#'):
                        # Assume this line is the URL if it follows an EXTINF and isn't another tag
                        url_line = line
                        extinf_lower = extinf_line.lower()
                        # Check if ANY keyword matches
                        if any(keyword in extinf_lower for keyword in keywords_lower):
                            # Check if we've already seen this URL *in this run*
                            if url_line not in seen_urls_this_run:
                                found_streams_this_run.append((extinf_line, url_line))
                                seen_urls_this_run.add(url_line)
                                # print(f"  Found match: {extinf_line[:50]}... / {url_line[:50]}...") # Debugging

                        # Reset extinf_line regardless of match, ready for the next pair
                        extinf_line = None
                    elif not line.startswith('#'):
                        # If we encounter a potential URL without a preceding EXTINF, reset
                         # or if it's just a non-comment line that isn't a URL following EXTINF
                        extinf_line = None

        except FileNotFoundError:
            error_msg = f"Error: File not found - {playlist_path}"
            print(error_msg)
            error_messages.append(error_msg)
            extinf_line = None # Reset state if file error occurs
        except Exception as e:
            error_msg = f"Error processing file {playlist_path}: {e}"
            print(error_msg)
            error_messages.append(error_msg)
            extinf_line = None # Reset state if other error occurs


    # Join errors into a single string or return None if no errors
    final_error_message = "\n".join(error_messages) if error_messages else None

    return found_streams_this_run, final_error_message

def save_or_append_playlist(output_path, streams_to_add):
    """
    Saves or appends the list of streams to an M3U8 file.
    If the file exists, it reads existing URLs and only appends new unique streams.
    If the file doesn't exist, it creates it with a header.

    Args:
        output_path (str): The path to save/append the playlist.
        streams_to_add (list): A list of (extinf_line, url_line) tuples found in the current run.

    Returns:
        tuple: (success_bool, message_string)
               Message string explains outcome or error.
    """
    if not output_path:
        return False, "Output file path not specified."
    if not output_path.lower().endswith(".m3u8"):
         output_path += ".m3u8" # Ensure correct extension

    added_count = 0
    try:
        # 1. Get URLs already present in the destination file (if it exists)
        existing_urls = get_existing_urls(output_path)
        print(f"Output file '{os.path.basename(output_path)}' exists: {os.path.exists(output_path)}. Found {len(existing_urls)} existing URLs.")

        # 2. Determine file mode and if header is needed
        file_exists = os.path.exists(output_path)
        is_empty = os.path.getsize(output_path) == 0 if file_exists else True
        mode = 'a' if file_exists else 'w' # Append if exists, write if new
        needs_header = not file_exists or is_empty

        # 3. Open file and write header if necessary
        with open(output_path, mode, encoding='utf-8') as f:
            if needs_header:
                f.write("#EXTM3U\n")
                print("Writing header.")

            # 4. Iterate through streams found in *this run*
            for extinf, url in streams_to_add:
                # 5. Check if the URL is already in the destination file
                if url not in existing_urls:
                    f.write(f"{extinf}\n")
                    f.write(f"{url}\n")
                    existing_urls.add(url) # Add to set to prevent adding duplicates from *this run* if any snuck through
                    added_count += 1

        if added_count > 0:
             action = "Appended" if file_exists else "Created"
             message = f"{action} playlist '{os.path.basename(output_path)}' and added {added_count} new unique streams."
             print(message)
             return True, message
        elif not streams_to_add:
             message = f"No new streams found matching criteria to add to '{os.path.basename(output_path)}'."
             print(message)
             return True, message # Considered success, just nothing to do
        else:
             message = f"All {len(streams_to_add)} found streams were already present in '{os.path.basename(output_path)}'. No changes made."
             print(message)
             return True, message # Considered success, just nothing to do

    except Exception as e:
        error_msg = f"Error saving/appending file {output_path}: {e}"
        print(error_msg)
        return False, error_msg


# --- GUI Class ---

class PlaylistFilterApp:
    def __init__(self, master):
        self.master = master
        master.title("M3U8 Playlist Filter (Folder & Append)")
        master.geometry("700x500") # Increased size

        self.input_files = set() # Use a set to automatically handle duplicate paths
        self.input_folder = None
        self.output_file = ""

        # --- Input Selection Frame ---
        self.frame_input_select = tk.Frame(master, padx=10, pady=5)
        self.frame_input_select.pack(fill=tk.X)

        self.btn_select_files = tk.Button(self.frame_input_select, text="Select Files", command=self.select_input_files)
        self.btn_select_files.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_select_folder = tk.Button(self.frame_input_select, text="Select Folder", command=self.select_input_folder)
        self.btn_select_folder.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_input_status = tk.Label(self.frame_input_select, text="Inputs: None selected.", anchor="w", justify=tk.LEFT)
        self.lbl_input_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Keyword Section ---
        self.frame_keyword = tk.Frame(master, padx=10, pady=5)
        self.frame_keyword.pack(fill=tk.X)

        self.lbl_keyword = tk.Label(self.frame_keyword, text="Keywords (comma-sep):", width=20, anchor="w") # Wider label
        self.lbl_keyword.pack(side=tk.LEFT)

        self.entry_keyword = tk.Entry(self.frame_keyword)
        self.entry_keyword.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Output File Section ---
        self.frame_output = tk.Frame(master, padx=10, pady=5)
        self.frame_output.pack(fill=tk.X)

        self.btn_select_output = tk.Button(self.frame_output, text="Set Output M3U8 File", command=self.select_output_file)
        self.btn_select_output.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_output_file = tk.Label(self.frame_output, text="Output: Not set.", anchor="w", justify=tk.LEFT)
        self.lbl_output_file.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Action Button ---
        self.frame_action = tk.Frame(master, padx=10, pady=10)
        self.frame_action.pack(fill=tk.X)

        self.btn_process = tk.Button(self.frame_action, text="Find & Add Streams", command=self.process_files, font=('Helvetica', 10, 'bold'))
        self.btn_process.pack()

        # --- Status Area ---
        self.frame_status = tk.Frame(master, padx=10, pady=5)
        self.frame_status.pack(fill=tk.BOTH, expand=True)

        self.lbl_status_head = tk.Label(self.frame_status, text="Status / Log:", anchor="w")
        self.lbl_status_head.pack(fill=tk.X)

        self.txt_status = scrolledtext.ScrolledText(self.frame_status, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.txt_status.pack(fill=tk.BOTH, expand=True)

    def log_status(self, message):
        """Appends a message to the status text area."""
        try:
            self.txt_status.configure(state=tk.NORMAL)
            self.txt_status.insert(tk.END, message + "\n")
            self.txt_status.see(tk.END) # Scroll to the bottom
            self.txt_status.configure(state=tk.DISABLED)
            self.master.update_idletasks() # Refresh GUI
        except tk.TclError:
            # Handle cases where the widget might be destroyed during shutdown
            print(f"Log (widget destroyed?): {message}")


    def clear_log(self):
        """Clears the status text area."""
        try:
            self.txt_status.configure(state=tk.NORMAL)
            self.txt_status.delete('1.0', tk.END)
            self.txt_status.configure(state=tk.DISABLED)
        except tk.TclError:
             pass # Ignore if widget is already gone


    def _update_input_status_label(self):
        """Updates the label showing selected inputs."""
        parts = []
        if self.input_folder:
            parts.append(f"Folder: ...{os.path.basename(self.input_folder)}")
        if self.input_files:
             # Get files *not* inside the selected folder if a folder is also selected
             files_outside_folder = self.input_files
             if self.input_folder:
                 folder_norm = os.path.normpath(self.input_folder)
                 files_outside_folder = {f for f in self.input_files if not os.path.normpath(f).startswith(folder_norm)}

             if files_outside_folder:
                 parts.append(f"{len(files_outside_folder)} individual file(s)")

        if not parts:
            status_text = "Inputs: None selected."
        else:
            status_text = "Inputs: " + " | ".join(parts)

        # Limit length to prevent excessive GUI width
        max_len = 80
        if len(status_text) > max_len:
            status_text = status_text[:max_len-3] + "..."

        self.lbl_input_status.config(text=status_text)

    def select_input_files(self):
        # Ask for multiple files
        selected_files = filedialog.askopenfilenames(
            title="Select Individual M3U8 Playlist Files",
            filetypes=[("M3U8 Playlists", "*.m3u8"), ("All Files", "*.*")]
        )
        if selected_files:
            count_before = len(self.input_files)
            self.input_files.update(selected_files) # Add to the set
            added_count = len(self.input_files) - count_before
            self.log_status(f"Added {added_count} individual input file(s). Total unique inputs: {len(self.input_files)}.")
            self._update_input_status_label()
        else:
            self.log_status("Individual file selection cancelled or no files chosen.")


    def select_input_folder(self):
        """Selects a folder and finds M3U8 files within it."""
        selected_folder = filedialog.askdirectory(title="Select Folder Containing M3U8 Playlists")
        if selected_folder:
            self.input_folder = selected_folder
            self.log_status(f"Input folder selected: {self.input_folder}")
            self.log_status("Scanning folder for .m3u8 files (recursive)...")
            self.master.update_idletasks() # Show message before potentially long scan
            found_in_folder = find_m3u8_files_in_folder(self.input_folder)
            if found_in_folder:
                 count_before = len(self.input_files)
                 self.input_files.update(found_in_folder) # Add to the set
                 added_from_folder = len(self.input_files) - count_before
                 self.log_status(f"Found {len(found_in_folder)} .m3u8 files in folder. Added {added_from_folder} new unique paths.")
            else:
                 self.log_status(f"No .m3u8 files found in folder: {self.input_folder}")
            self._update_input_status_label()
        else:
            self.log_status("Folder selection cancelled.")
            # Optionally clear self.input_folder if selection is cancelled?
            # self.input_folder = None
            # self._update_input_status_label()


    def select_output_file(self):
        # Ask where to save the new file
        selected_file = filedialog.asksaveasfilename(
            title="Set Output/Append Playlist File",
            defaultextension=".m3u8",
            filetypes=[("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")]
        )
        if selected_file:
            self.output_file = selected_file
            # Add .m3u8 extension if missing (asksaveasfilename doesn't always enforce it)
            # Important: Check before adding to avoid .m3u8.m3u8
            if not self.output_file.lower().endswith(".m3u8"):
                self.output_file += ".m3u8"
            self.lbl_output_file.config(text=f"Output: {os.path.basename(self.output_file)}")
            self.log_status(f"Output file set to: {self.output_file}")
        else:
            self.log_status("Output file selection cancelled.")

    def process_files(self):
        self.clear_log()
        self.log_status("Starting processing...")
        start_time = time.time()

        # --- Validations ---
        if not self.input_files:
            messagebox.showerror("Error", "Please select input M3U8 files or a folder containing them.")
            self.log_status("Error: No input sources selected.")
            return

        keywords_str = self.entry_keyword.get() # Get raw string
        # Check if keywords are present *after* potential splitting/stripping
        processed_keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        if not processed_keywords:
            messagebox.showerror("Error", "Please enter one or more keywords (comma-separated).")
            self.log_status("Error: Keyword(s) are missing or invalid.")
            return

        if not self.output_file:
            messagebox.showerror("Error", "Please specify an output file path.")
            self.log_status("Error: Output file path not set.")
            return

        # --- Disable button during processing ---
        self.btn_process.config(state=tk.DISABLED, text="Processing...")
        self.master.update_idletasks() # Make sure GUI updates

        # --- Run Core Logic ---
        try:
            # Convert set of paths to list for processing function
            input_paths_list = sorted(list(self.input_files))
            self.log_status(f"Processing {len(input_paths_list)} unique M3U8 file(s).")
            self.log_status(f"Searching for keywords: {processed_keywords}") # Log the processed list

            found_streams, file_errors = find_matching_streams(input_paths_list, keywords_str)

            if file_errors:
                self.log_status("--- File Reading Issues Encountered ---")
                self.log_status(file_errors)
                self.log_status("--- Continuing processing despite issues ---")

            self.log_status(f"Found {len(found_streams)} potentially new matching streams in this run.")

            if not found_streams:
                 self.log_status("No streams matching the criteria were found in the input files during this run.")
                 # Don't show a pop-up if nothing found, log is enough unless appending
                 if os.path.exists(self.output_file):
                      self.log_status(f"Output file '{os.path.basename(self.output_file)}' remains unchanged.")
                 else:
                      self.log_status(f"Output file '{os.path.basename(self.output_file)}' was not created as no streams were found.")

            else:
                # --- Save/Append Results ---
                self.log_status(f"Saving/Appending results to: {self.output_file}")
                success, message = save_or_append_playlist(self.output_file, found_streams)

                if success:
                    messagebox.showinfo("Processing Complete", message)
                    self.log_status(f"Success: {message}")
                else:
                    messagebox.showerror("Save/Append Error", f"Failed to update the playlist:\n{message}")
                    self.log_status(f"Error: {message}")

        except Exception as e:
            # Catch unexpected errors during the process
            error_msg = f"An unexpected critical error occurred: {e}"
            import traceback
            traceback.print_exc() # Print full traceback to console for debugging
            messagebox.showerror("Processing Error", error_msg)
            self.log_status(f"FATAL ERROR: {error_msg}")

        finally:
             # --- Re-enable button ---
            end_time = time.time()
            self.log_status(f"Processing finished in {end_time - start_time:.2f} seconds.")
            self.btn_process.config(state=tk.NORMAL, text="Find & Add Streams")
            self.master.update_idletasks()

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PlaylistFilterApp(root)
    root.mainloop()