import tkinter as tk
from tkinter import ttk, filedialog
import os

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, current_settings, save_callback):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("600x250")  # Wider and taller for Browse button
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.current_settings = current_settings
        self.save_callback = save_callback
        self.selected_category = tk.StringVar(value="General")
        self.categories = ["General", "Persistence"]
        self._build_ui()
        self.center_window()

    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        # Left: Category list
        left = ttk.Frame(container)
        left.pack(side="left", fill="y")
        self.cat_list = tk.Listbox(left, listvariable=tk.StringVar(value=self.categories), height=5, exportselection=False)
        self.cat_list.pack(fill="y", expand=True)
        self.cat_list.bind("<<ListboxSelect>>", self._on_cat_select)
        self.cat_list.selection_set(0)
        # Right: Category pane
        self.right_frame = ttk.Frame(container)
        self.right_frame.pack(side="right", fill="both", expand=True)
        self._show_general_settings()

    def _on_cat_select(self, event):
        idx = self.cat_list.curselection()
        if not idx:
            return
        cat = self.cat_list.get(idx[0])
        self.selected_category.set(cat)
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        if cat == "General":
            self._show_general_settings()
        elif cat == "Persistence":
            self._show_persistence_settings()

    def _show_general_settings(self):
        # Artist Directory setting
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        label = ttk.Label(self.right_frame, text="Artist Directory:")
        label.grid(row=0, column=0, sticky="w", pady=(10, 2), padx=(10, 2))
        self.artist_dir_var = tk.StringVar(value=self.current_settings.get("artist_directory", ""))
        entry = ttk.Entry(self.right_frame, textvariable=self.artist_dir_var, width=24)
        entry.grid(row=1, column=0, sticky="w", padx=(10, 2), pady=(0, 0))
        browse_btn = ttk.Button(self.right_frame, text="Browse...", command=self._browse_artist_dir)
        browse_btn.grid(row=1, column=1, sticky="w", padx=(2, 10), pady=(0, 0))
        save_btn = ttk.Button(self.right_frame, text="Save", command=self._save)
        save_btn.grid(row=2, column=0, pady=(12, 0), padx=(10, 2), sticky="w")
        self.status_label = ttk.Label(self.right_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 0))

    def _browse_artist_dir(self):
        new_dir = filedialog.askdirectory(title="Select Artist Directory", initialdir=self.artist_dir_var.get() or ".")
        if new_dir:
            self.artist_dir_var.set(new_dir)

    def _save(self):
        self.current_settings["artist_directory"] = self.artist_dir_var.get()
        self.save_callback(self.current_settings)
        self.status_label.config(text="Saved.")
        # Do not close the window

    def _show_persistence_settings(self):
        # Settings JSON location
        label = ttk.Label(self.right_frame, text="Settings File Location:")
        label.grid(row=0, column=0, sticky="w", pady=(10, 2), padx=(10, 2))
        self.settings_path_var = tk.StringVar(value=self.current_settings.get("settings_file_path", ""))
        entry = ttk.Entry(self.right_frame, textvariable=self.settings_path_var, width=24)
        entry.grid(row=1, column=0, sticky="w", padx=(10, 2), pady=(0, 0))
        browse_btn = ttk.Button(self.right_frame, text="Browse...", command=self._browse_settings_path)
        browse_btn.grid(row=1, column=1, sticky="w", padx=(2, 10), pady=(0, 0))
        reset_btn = ttk.Button(self.right_frame, text="Reset to Default", command=self._reset_settings_path)
        reset_btn.grid(row=2, column=0, pady=(12, 0), padx=(10, 2), sticky="w")
        save_btn = ttk.Button(self.right_frame, text="Save", command=self._save_storage)
        save_btn.grid(row=2, column=1, pady=(12, 0), padx=(2, 10), sticky="e")
        self.status_label = ttk.Label(self.right_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 0))

    def _browse_settings_path(self):
        new_path = filedialog.asksaveasfilename(title="Select Settings File Location", defaultextension=".json",
                                                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if new_path:
            self.settings_path_var.set(new_path)

    def _reset_settings_path(self):
        default_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "playlistBuilder")
        if not os.path.isdir(default_dir):
            os.makedirs(default_dir, exist_ok=True)
        default_path = os.path.join(default_dir, "playlist_editor_settings.json")
        self.settings_path_var.set(default_path)
        self.status_label.config(text="Reset to default.")

    def _save_storage(self):
        self.current_settings["settings_file_path"] = self.settings_path_var.get()
        self.save_callback(self.current_settings)
        self.status_label.config(text="Saved.")

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
