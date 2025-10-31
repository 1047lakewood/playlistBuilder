# --- START OF FILE make playlists from keyword FILES_threaded_no_precount.py ---

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import sys
import time
import threading
import queue

# --- Configuration ---
DEFAULT_SCAN_FOLDER = "G:\\"
DEFAULT_PLAYLIST_NAME = "playlist.m3u8"
MP3_EXTENSION = ".mp3"
CASE_SENSITIVE_MATCH = False
# --- Optimizations ---
# How often to update the 'files scanned' count in the GUI label
# Make this less frequent for very fast scans if needed, more frequent for slow scans
SCAN_COUNT_UPDATE_INTERVAL = 5000 # Update label every 5000 files scanned
QUEUE_CHECK_INTERVAL_MS = 100 # How often main thread checks queue (milliseconds)
# ---------------------

# Define constants for queue messages for clarity
QUEUE_MESSAGE = "MSG"
QUEUE_ERROR = "ERR"
QUEUE_DONE = "DONE"
QUEUE_SCAN_PROGRESS = "SCAN_PROG" # Renamed for clarity

class MP3PlaylistCreator(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("MP3 Keyword Playlist Creator (Append Mode - No Pre-count)") # Updated title
        self.geometry("600x480")

        # --- Threading Specific ---
        self.status_queue = queue.Queue()
        self.scan_thread = None
        self.is_scanning = False

        # --- Variables ---
        self.folder_path = tk.StringVar(value=DEFAULT_SCAN_FOLDER)
        self.keywords_str = tk.StringVar()
        self.playlist_file = tk.StringVar(value=DEFAULT_PLAYLIST_NAME)

        # --- Widgets ---
        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1) # Status text area gets expansion

        # --- Folder Selection ---
        tk.Label(main_frame, text="Folder to Scan:").grid(row=0, column=0, sticky=tk.W, pady=2)
        folder_entry = tk.Entry(main_frame, textvariable=self.folder_path, width=50)
        folder_entry.grid(row=0, column=1, sticky=tk.EW, padx=(5, 0), pady=2)
        self.browse_folder_btn = tk.Button(main_frame, text="Browse...", command=self.browse_folder)
        self.browse_folder_btn.grid(row=0, column=2, sticky=tk.EW, padx=(5, 0), pady=2)

        # --- Keyword Input ---
        tk.Label(main_frame, text="Keywords (comma-sep):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.keywords_entry = tk.Entry(main_frame, textvariable=self.keywords_str, width=50)
        self.keywords_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=(5, 0), pady=2)

        # --- Playlist Output ---
        tk.Label(main_frame, text="Output Playlist:").grid(row=2, column=0, sticky=tk.W, pady=2)
        playlist_entry = tk.Entry(main_frame, textvariable=self.playlist_file, width=50)
        playlist_entry.grid(row=2, column=1, sticky=tk.EW, padx=(5, 0), pady=2)
        self.save_as_btn = tk.Button(main_frame, text="Save As...", command=self.save_playlist_as)
        self.save_as_btn.grid(row=2, column=2, sticky=tk.EW, padx=(5, 0), pady=2)

        # --- Action Button ---
        self.scan_btn = tk.Button(main_frame, text="Scan and Add to Playlist", command=self.start_scan_thread)
        self.scan_btn.grid(row=3, column=0, columnspan=3, pady=10)

        # --- Progress Bar (Indeterminate) ---
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=(5,0))
        self.progress_label = tk.Label(main_frame, text="") # Label for scan count
        self.progress_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(0,5))


        # --- Status Area ---
        tk.Label(main_frame, text="Status:").grid(row=6, column=0, sticky=tk.NW, pady=(5,0))
        self.status_text = scrolledtext.ScrolledText(main_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.status_text.grid(row=6, column=1, columnspan=2, sticky=tk.NSEW, padx=(5, 0), pady=(5,0))

        # Set initial state
        self._update_ui_state()

    def _update_ui_state(self):
        """Enable/disable widgets based on scanning state."""
        state = tk.DISABLED if self.is_scanning else tk.NORMAL
        self.scan_btn.config(state=state)
        self.browse_folder_btn.config(state=state)
        self.keywords_entry.config(state=state)
        self.save_as_btn.config(state=state)

        if not self.is_scanning:
            self.progress_label.config(text="")
            self.progress.stop() # Stop indeterminate animation
            self.scan_btn.config(text="Scan and Add to Playlist") # Reset button text
        else:
            self.scan_btn.config(text="Scanning...") # Change button text
            self.progress_label.config(text="Starting scan...")
            self.progress.start() # Start indeterminate animation

    def log_status(self, message):
        """Appends a message to the status text area FROM THE MAIN THREAD."""
        if self.status_text:
            self.status_text.config(state=tk.NORMAL)
            self.status_text.insert(tk.END, message + "\n")
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)

    def clear_status(self):
        """Clears the status text area FROM THE MAIN THREAD."""
        if self.status_text:
            self.status_text.config(state=tk.NORMAL)
            self.status_text.delete('1.0', tk.END)
            self.status_text.config(state=tk.DISABLED)

    def browse_folder(self):
        if self.is_scanning: return
        directory = filedialog.askdirectory(initialdir=self.folder_path.get())
        if directory:
            self.folder_path.set(directory)

    def save_playlist_as(self):
        if self.is_scanning: return
        filepath = filedialog.asksaveasfilename(
            initialfile=self.playlist_file.get(),
            defaultextension=".m3u8",
            filetypes=[("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")]
        )
        if filepath:
            self.playlist_file.set(filepath)

    # -------------------------------------------------------------------------
    # Threading Logic
    # -------------------------------------------------------------------------

    def start_scan_thread(self):
        """Initiates the scan in a background thread."""
        if self.is_scanning:
            self.log_status("Scan already in progress.")
            return

        folder = self.folder_path.get()
        keywords_raw = self.keywords_str.get()
        playlist_path = self.playlist_file.get()

        # Quick input validation
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", f"Invalid folder: {folder}")
            return
        if not keywords_raw:
            messagebox.showerror("Error", "Keywords required.")
            return
        if not playlist_path:
            messagebox.showerror("Error", "Output playlist required.")
            return
        keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]
        if not keywords:
             messagebox.showerror("Error", "Keywords invalid.")
             return

        # Start the thread
        self.clear_status()
        self.log_status("Starting scan...")
        self.is_scanning = True
        self._update_ui_state() # Disables buttons, starts progress bar animation

        self.scan_thread = threading.Thread(
            target=self._perform_scan_in_thread,
            args=(folder, keywords, playlist_path),
            daemon=True
        )
        self.scan_thread.start()

        # Start queue checking
        self.after(QUEUE_CHECK_INTERVAL_MS, self._process_status_queue)

    def _process_status_queue(self):
        """Checks the queue for messages from the worker thread and updates GUI."""
        try:
            while True: # Process all messages currently in queue
                message_type, data = self.status_queue.get_nowait()

                if message_type == QUEUE_MESSAGE:
                    self.log_status(data)
                elif message_type == QUEUE_SCAN_PROGRESS:
                    # Update label with files scanned count
                    files_scanned = data
                    self.progress_label.config(text=f"Scanned {files_scanned:,} files...")
                elif message_type == QUEUE_ERROR:
                    self.log_status(f"ERROR: {data}")
                    messagebox.showerror("Scan Error", data)
                    self.is_scanning = False # Stop process on error
                    self._update_ui_state()
                    return # Stop checking queue
                elif message_type == QUEUE_DONE:
                    final_message, files_added = data # Expecting (message, count)
                    self.log_status(final_message)
                    if files_added is not None:
                         messagebox.showinfo("Scan Complete", f"{final_message}\nFiles added/found: {files_added:,}")
                    else:
                         messagebox.showinfo("Scan Complete", final_message)

                    self.is_scanning = False # Mark as done
                    self._update_ui_state()
                    return # Stop checking the queue

        except queue.Empty:
            # No messages currently in queue, do nothing
            pass
        except Exception as e:
            # Unexpected error processing queue
            self.log_status(f"FATAL: Error processing status queue: {e}")
            try: # Try to reset state even after error
                 self.is_scanning = False
                 self._update_ui_state()
            except Exception: pass # Ignore errors during error handling cleanup
            return # Stop checking queue

        # Reschedule check if scan is still running
        if self.is_scanning:
            self.after(QUEUE_CHECK_INTERVAL_MS, self._process_status_queue)


    def _put_status(self, msg_type, data):
        """Helper to safely put messages onto the queue."""
        if self.status_queue:
            self.status_queue.put((msg_type, data))

    def _perform_scan_in_thread(self, folder, keywords, playlist_path):
        """This function runs in the background thread. NO PRE-COUNT."""
        start_time = time.time()
        files_actually_added = None

        try:
            # --- Pre-process keywords ---
            if not CASE_SENSITIVE_MATCH:
                keywords_to_check = [k.lower() for k in keywords]
                match_info = "(case-insensitive)"
            else:
                keywords_to_check = keywords
                match_info = "(case-sensitive)"

            self._put_status(QUEUE_MESSAGE, f"Scanning folder: {folder}")
            self._put_status(QUEUE_MESSAGE, f"Keywords: {', '.join(repr(k) for k in keywords)} {match_info}")

            # --- NO PRE-COUNTING ---

            found_files = []
            files_scanned = 0
            dirs_scanned = 0
            last_status_update_files = 0

            # --- Scanning Logic ---
            for root, _, files in os.walk(folder, topdown=True): # topdown=True might be slightly faster sometimes
                dirs_scanned += 1
                # Filter files list *before* iterating if possible (micro-optimization)
                # mp3_files = [f for f in files if f.lower().endswith(MP3_EXTENSION)]
                # Not strictly necessary, loop below handles it.

                for filename in files:
                    files_scanned += 1
                    try:
                        # Check extension first (cheap)
                        if filename.lower().endswith(MP3_EXTENSION):
                            name_to_check = filename if CASE_SENSITIVE_MATCH else filename.lower()
                            # Use generator expression with any() for early exit
                            if any(kw in name_to_check for kw in keywords_to_check):
                                full_path = os.path.abspath(os.path.join(root, filename))
                                found_files.append(full_path)

                    except Exception as file_err:
                         print(f"Warning (thread): Error processing file '{filename}': {file_err}")
                         # Avoid flooding queue with file errors
                         # self._put_status(QUEUE_MESSAGE, f"WARN: Skip file error: {filename[:30]}...")

                    # --- Update Scan Progress Count Periodically ---
                    if files_scanned - last_status_update_files >= SCAN_COUNT_UPDATE_INTERVAL:
                        self._put_status(QUEUE_SCAN_PROGRESS, files_scanned)
                        last_status_update_files = files_scanned

            # Send final scan count
            self._put_status(QUEUE_SCAN_PROGRESS, files_scanned)

            scan_duration = time.time() - start_time
            self._put_status(QUEUE_MESSAGE, f"Scan complete ({scan_duration:.2f}s). Found {len(found_files):,} potential matches in {files_scanned:,} files scanned.")

            if not found_files:
                self._put_status(QUEUE_DONE, ("No matching MP3 files found to add.", 0))
                return

            # --- Playlist Writing/Appending ---
            # (This part remains the same as the previous threaded version)
            self._put_status(QUEUE_MESSAGE, f"Processing playlist file: {playlist_path}")
            start_write_time = time.time()

            existing_paths = set()
            write_mode = 'w'
            needs_header = True
            read_existing_success = True

            playlist_dir = os.path.dirname(playlist_path)
            if playlist_dir and not os.path.exists(playlist_dir):
                 os.makedirs(playlist_dir, exist_ok=True)
                 self._put_status(QUEUE_MESSAGE, f"Created directory: {playlist_dir}")

            read_start_time = time.time()
            if os.path.exists(playlist_path) and os.path.getsize(playlist_path) > 0:
                 self._put_status(QUEUE_MESSAGE, "Reading existing playlist...")
                 write_mode = 'a'
                 needs_header = False
                 try:
                     with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f_read:
                         lines_read = 0; first_line_checked = False
                         for line in f_read:
                             lines_read += 1; line_strip = line.strip()
                             if line_strip:
                                 existing_paths.add(line_strip)
                                 if not first_line_checked:
                                      needs_header = line_strip.upper() != "#EXTM3U"
                                      if needs_header: self._put_status(QUEUE_MESSAGE,"Warning: Existing playlist missing header.")
                                      first_line_checked = True
                     read_duration = time.time() - read_start_time
                     self._put_status(QUEUE_MESSAGE, f"Read {len(existing_paths):,} existing entries ({read_duration:.2f}s).")
                     if write_mode == 'a' and needs_header: self._put_status(QUEUE_MESSAGE,"Warning: Appending to playlist that may be invalid.")
                 except Exception as read_err:
                     self._put_status(QUEUE_MESSAGE, f"Warning: Could not read existing playlist ({read_err}). Will OVERWRITE.")
                     write_mode = 'w'; needs_header = True; existing_paths.clear(); read_existing_success = False
            elif os.path.exists(playlist_path): write_mode = 'w'; needs_header = True
            else: write_mode = 'w'; needs_header = True

            files_actually_added = 0
            with open(playlist_path, write_mode, encoding='utf-8') as f:
                if write_mode == 'w' and needs_header:
                    f.write("#EXTM3U\n")
                for mp3_path in found_files:
                    if mp3_path not in existing_paths:
                        f.write(mp3_path + "\n")
                        existing_paths.add(mp3_path)
                        files_actually_added += 1

            write_duration = time.time() - start_write_time
            total_duration = time.time() - start_time

            final_message = ""
            if write_mode == 'w':
                 verb = "CREATED" if read_existing_success else "OVERWROTE"
                 final_message = f"Successfully {verb} playlist '{os.path.basename(playlist_path)}' ({files_actually_added:,} entries)."
            else:
                 if files_actually_added > 0: final_message = f"Successfully ADDED {files_actually_added:,} new unique files to '{os.path.basename(playlist_path)}'."
                 else: final_message = f"No new unique files found to add to '{os.path.basename(playlist_path)}'."

            final_message += f" (Total time: {total_duration:.2f}s)"
            self._put_status(QUEUE_DONE, (final_message, files_actually_added))

        except Exception as e:
            import traceback
            err_msg = f"Error during scan/write: {e}\n{traceback.format_exc()}"
            print(err_msg)
            self._put_status(QUEUE_ERROR, f"An error occurred: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    if not os.path.exists(DEFAULT_SCAN_FOLDER):
         print(f"Warning: Default folder '{DEFAULT_SCAN_FOLDER}' not found.")
    app = MP3PlaylistCreator()
    app.mainloop()

# --- END OF FILE make playlists from keyword FILES_threaded_no_precount.py ---