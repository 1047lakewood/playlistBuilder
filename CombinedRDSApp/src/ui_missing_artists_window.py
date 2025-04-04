import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import logging

# Placeholder for IntroLoaderHandler if needed directly (passed in constructor)
# from intro_loader_handler import IntroLoaderHandler

class MissingArtistsWindow(Toplevel):
    """Window to display and manage the missing artists log."""
    def __init__(self, parent, intro_loader_handler):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Missing Artist Intros Log")
        self.geometry("900x500")

        self.intro_loader_handler = intro_loader_handler
        self.log_entries = [] # Store parsed entries {id, timestamp, artist, filepath, raw_line}

        self.create_widgets()
        self.load_log_entries()

         # Handle closing the window (optional, destroy is default)
         # self.protocol("WM_DELETE_WINDOW", self.destroy)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(toolbar, text="Refresh", command=self.load_log_entries).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=2)

        # Treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("Timestamp", "Artist", "Filepath"),
                            show='headings', selectmode="extended") # Changed from "browse" to "extended"
        self.tree.heading("Timestamp", text="Timestamp", anchor=tk.W)
        self.tree.heading("Artist", text="Artist Name", anchor=tk.W)
        self.tree.heading("Filepath", text="Source File Path", anchor=tk.W)

        self.tree.column("Timestamp", width=150, stretch=False)
        self.tree.column("Artist", width=200, stretch=False)
        self.tree.column("Filepath", width=500, stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

    def load_log_entries(self):
        """Loads/reloads entries from the handler and populates the treeview."""
        logging.debug("Loading missing artist log entries...")
        try:
            self.log_entries = self.intro_loader_handler.get_missing_artists()
            self.tree.delete(*self.tree.get_children())

            if not self.log_entries:
                logging.info("Missing artists log is empty or could not be read.")
                # Optionally display a message in the treeview
                # self.tree.insert("", tk.END, text="Log file is empty or unreadable.")
                return

            for entry in self.log_entries:
                # Use the 'id' (line number) from parsing as the item ID
                item_id = entry["id"]
                self.tree.insert("", tk.END, iid=item_id, values=(
                    entry["timestamp"], entry["artist"], entry["filepath"]
                ))
            logging.debug(f"Loaded {len(self.log_entries)} entries into missing artists view.")
        except Exception as e:
            logging.exception("Error loading missing artist entries into treeview.")
            messagebox.showerror("Load Error", f"Failed to load missing artists log:\n{e}", parent=self)


    def delete_selected_entry(self):
        """Deletes the selected entries from the log file and refreshes."""
        selected_item_ids = self.tree.selection() # Returns a tuple of selected item IDs
        if not selected_item_ids:
            messagebox.showwarning("No Selection", "Please select one or more log entries to delete.", parent=self)
            return

        num_selected = len(selected_item_ids)
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {num_selected} selected log entr{'y' if num_selected == 1 else 'ies'}?",
            parent=self
        )
        if not confirm:
            return

        raw_lines_to_delete = []
        found_all = True
        for item_id in selected_item_ids:
            found_line = False
            for entry in self.log_entries:
                # Compare IDs (which should be unique line numbers from parsing)
                if str(entry["id"]) == str(item_id): # Ensure type match for comparison
                    raw_lines_to_delete.append(entry["raw_line"])
                    found_line = True
                    break
            if not found_line:
                logging.error(f"Could not find raw line data for selected tree item ID: {item_id}")
                found_all = False
                # Continue trying to delete others, but report error later

        if not raw_lines_to_delete:
            messagebox.showerror("Error", "Could not find data for any selected entries.", parent=self)
            return
        if not found_all:
            messagebox.showwarning("Partial Error", "Could not find data for some selected entries. Attempting to delete the found ones.", parent=self)


        logging.info(f"Attempting to delete {len(raw_lines_to_delete)} log entries.")
        try:
            # *** Assuming delete_missing_artist_entry can handle a list ***
            # If not, this call will fail or need modification in the handler
            success = self.intro_loader_handler.delete_missing_artist_entry(raw_lines_to_delete)
            if success:
                logging.info(f"{len(raw_lines_to_delete)} log entries deleted successfully.")
                # Success message removed for quicker workflow
                self.load_log_entries() # Refresh the list
            else:
                logging.warning("Handler reported failure deleting log entry.")
                messagebox.showerror("Error", "Failed to delete the log entry. Check application logs.", parent=self)
        except Exception as e:
            logging.exception("Exception occurred while calling delete_missing_artist_entry.")
            messagebox.showerror("Error", f"An error occurred during deletion:\n{e}", parent=self)

# Example usage for testing
if __name__ == "__main__":
    print("This script defines the MissingArtistsWindow UI component.")
    # root = tk.Tk()
    # class MockLoader: # Define mocks if needed for standalone testing
    #     def get_missing_artists(self): return [{"id":0, "timestamp":"2025-01-01", "artist":"Test Artist", "filepath":"/path/to/file", "raw_line":"raw"}]
    #     def delete_missing_artist_entry(self, line): print(f"Mock Delete: {line}"); return True
    # mock_ldr = MockLoader()
    # MissingArtistsWindow(root, mock_ldr)
    # root.mainloop()
