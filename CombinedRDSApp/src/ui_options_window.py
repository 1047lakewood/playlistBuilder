import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import logging

# Placeholders for managers/handlers if needed directly (passed in constructor)
# from config_manager import ConfigManager
# from intro_loader_handler import IntroLoaderHandler

class OptionsWindow(Toplevel):
    """Window for application options (Whitelist, Blacklist, Debug)."""
    def __init__(self, parent, config_manager, intro_loader_handler):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Options")
        self.geometry("600x450") # Adjust size as needed

        self.config_manager = config_manager
        self.intro_loader_handler = intro_loader_handler

        # Store initial lists to detect changes
        self.initial_whitelist = self.config_manager.get_whitelist().copy()
        self.initial_blacklist = self.config_manager.get_blacklist().copy()
        self.changes_pending = False # Track if lists were modified

        self.create_widgets()

        self.protocol("WM_DELETE_WINDOW", self.on_close)


    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # --- Whitelist Tab ---
        whitelist_frame = ttk.Frame(notebook, padding="10")
        notebook.add(whitelist_frame, text="Artist Whitelist")
        self.whitelist_listbox = self.create_list_editor(
            whitelist_frame,
            "Whitelist",
            self.initial_whitelist # Pass initial list
        )

        # --- Blacklist Tab ---
        blacklist_frame = ttk.Frame(notebook, padding="10")
        notebook.add(blacklist_frame, text="Artist Blacklist")
        self.blacklist_listbox = self.create_list_editor(
            blacklist_frame,
            "Blacklist",
            self.initial_blacklist # Pass initial list
        )

        # --- Debug Tab (Re-added) ---
        debug_frame = ttk.Frame(notebook, padding="10")
        notebook.add(debug_frame, text="Debug")
        debug_label = ttk.Label(debug_frame, text="Debug Tools", font=("Segoe UI", 10, "bold"))
        debug_label.pack(pady=(0,10))

        # Add button to "touch" the XML file
        touch_button = ttk.Button(debug_frame, text="Touch XML File", command=self.touch_xml_file_action)
        touch_button.pack(pady=5)
        touch_help = ttk.Label(debug_frame, text="Updates the XML file's modification time to force the Intro Loader to re-check it.", wraplength=380)
        touch_help.pack(pady=2)


        # --- Bottom Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Save & Close", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side=tk.RIGHT, padx=5)


    def create_list_editor(self, parent_frame, list_name, initial_list):
        """Helper to create the listbox, entry, and buttons for Whitelist/Blacklist."""
        ttk.Label(parent_frame, text=f"Enter artist name exactly as it appears in XML (case-insensitive match):").pack(anchor=tk.W)

        list_container = ttk.Frame(parent_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # Listbox with Scrollbar
        listbox_frame = ttk.Frame(list_container)
        listbox_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 5))

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, exportselection=False, height=10)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Populate Listbox
        for item in initial_list:
            listbox.insert(tk.END, item)

        # Entry and Buttons Frame
        entry_button_frame = ttk.Frame(list_container)
        entry_button_frame.pack(fill=tk.Y, side=tk.LEFT)

        entry_var = tk.StringVar()
        entry = ttk.Entry(entry_button_frame, textvariable=entry_var, width=30)
        entry.pack(pady=(0, 5))

        def mark_change_flag():
            self.changes_pending = True

        def add_item():
            item = entry_var.get().strip()
            if item and item not in listbox.get(0, tk.END):
                listbox.insert(tk.END, item)
                entry_var.set("")
                mark_change_flag() # Mark changes when item added
        ttk.Button(entry_button_frame, text="Add", command=add_item).pack(fill=tk.X, pady=2)

        def delete_item():
            selected_indices = listbox.curselection()
            if selected_indices:
                # Delete from bottom up to avoid index issues
                for i in reversed(selected_indices):
                    listbox.delete(i)
                mark_change_flag() # Mark changes when item deleted
        ttk.Button(entry_button_frame, text="Delete", command=delete_item).pack(fill=tk.X, pady=2)

        # Return the listbox widget so it can be accessed for saving
        return listbox

    def touch_xml_file_action(self):
        """Calls the handler method to touch the XML file, without confirmation."""
        logging.debug("Touch XML File button clicked.")
        try:
            # Call the new method in the handler
            success = self.intro_loader_handler.touch_monitored_xml()
            if success:
                logging.info("Debug touch XML successful via Options window.")
                # Optionally provide non-modal feedback, e.g., update a status label if one existed here
            else:
                logging.error("Debug touch XML failed via Options window. Check logs.")
                # Optionally show error, but user requested no alerts
        except Exception as e:
             logging.exception("Exception calling touch_monitored_xml.")
             # Avoid showing error popup as requested

    def save_and_close(self):
        """Saves the whitelist/blacklist if changed and closes."""
        # Get current lists from listboxes
        new_whitelist = list(self.whitelist_listbox.get(0, tk.END))
        new_blacklist = list(self.blacklist_listbox.get(0, tk.END))

        # Check if changes were actually made (or if flag was set)
        if self.changes_pending or new_whitelist != self.initial_whitelist or new_blacklist != self.initial_blacklist:
            try:
                self.config_manager.set_whitelist(new_whitelist)
                self.config_manager.set_blacklist(new_blacklist)
                self.config_manager.save_config()
                logging.info("Whitelist/Blacklist changes saved.")
                messagebox.showinfo("Saved", "Whitelist/Blacklist settings saved.", parent=self)
                self.changes_pending = False # Reset flag after successful save
            except Exception as e:
                 logging.exception("Failed to save Whitelist/Blacklist.")
                 messagebox.showerror("Save Error", f"Failed to save settings:\n{e}", parent=self)
                 return # Don't close if save failed

        self.destroy()

    def on_close(self):
        """Checks for unsaved changes on close."""
        new_whitelist = list(self.whitelist_listbox.get(0, tk.END))
        new_blacklist = list(self.blacklist_listbox.get(0, tk.END))

        # Check flag first, then compare lists as backup
        if self.changes_pending or new_whitelist != self.initial_whitelist or new_blacklist != self.initial_blacklist:
            response = messagebox.askyesnocancel("Unsaved Changes", "Whitelist or Blacklist has been modified. Save changes before closing?", parent=self)
            if response is True: # Yes
                self.save_and_close()
            elif response is False: # No
                self.destroy() # Close without saving
            # else: Cancel, do nothing
        else:
            self.destroy() # No changes, just close

# Example usage for testing
if __name__ == "__main__":
    print("This script defines the OptionsWindow UI component.")
    # root = tk.Tk()
    # class MockConfig: # Define mocks if needed for standalone testing
    #     def get_whitelist(self): return ["Artist A"]
    #     def get_blacklist(self): return ["Artist B"]
    #     def set_whitelist(self, l): pass
    #     def set_blacklist(self, l): pass
    #     def save_config(self): print("Mock Save")
    # class MockLoader:
    #     def trigger_xml_change(self): print("Mock Trigger XML"); return True
    # mock_cfg = MockConfig()
    # mock_ldr = MockLoader()
    # OptionsWindow(root, mock_cfg, mock_ldr)
    # root.mainloop()
