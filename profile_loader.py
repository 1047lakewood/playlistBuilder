import tkinter as tk
from tkinter import simpledialog, messagebox
from font_config import DEFAULT_FONT, BOLD_FONT, DEFAULT_FONT_TUPLE

class ProfileSelectionDialog(simpledialog.Dialog):
    def __init__(self, parent, title, profiles, current_profile, action_type="load"):
        self.profiles = profiles
        self.current_profile = current_profile
        self.selected_profile = current_profile
        self.action_type = action_type  # 'load', 'save', 'delete'
        self.new_profile_name = ""
        super().__init__(parent, title)

    def body(self, master):
        # Create a frame for the radio buttons
        self.profile_frame = tk.Frame(master)
        self.profile_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create a label
        action_text = "Select" if self.action_type == "load" else "Save to"
        tk.Label(self.profile_frame, text=f"{action_text} profile:", font=DEFAULT_FONT).pack(anchor="w")

        # Create radio buttons for each profile
        self.profile_var = tk.StringVar(value=self.current_profile)
        for profile in self.profiles:
            rb = tk.Radiobutton(self.profile_frame, text=profile, value=profile, variable=self.profile_var, font=DEFAULT_FONT)
            rb.pack(anchor="w", padx=20)

        # Add option to create a new profile if saving
        if self.action_type in ["save", "load"]:
            # Separator
            tk.Frame(self.profile_frame, height=1, bg="gray").pack(fill="x", pady=5)
            
            # New profile option
            new_profile_frame = tk.Frame(self.profile_frame)
            new_profile_frame.pack(fill="x", pady=5)
            
            self.new_profile_rb = tk.Radiobutton(new_profile_frame, text="Create new profile:", 
                                               value="__new__", variable=self.profile_var, font=DEFAULT_FONT)
            self.new_profile_rb.pack(side="left")
            
            self.new_profile_entry = tk.Entry(new_profile_frame, width=20, font=DEFAULT_FONT)
            self.new_profile_entry.pack(side="left", padx=5)
            self.new_profile_entry.bind("<FocusIn>", self.select_new_profile)

        return self.profile_frame

    def select_new_profile(self, event):
        self.profile_var.set("__new__")

    def validate(self):
        selected = self.profile_var.get()
        if selected == "__new__":
            new_name = self.new_profile_entry.get().strip()
            if not new_name:
                messagebox.showerror("Error", "Please enter a name for the new profile")
                return False
            self.new_profile_name = new_name
        self.selected_profile = selected
        return True

    def apply(self):
        if self.selected_profile == "__new__":
            self.result = self.new_profile_name
        else:
            self.result = self.selected_profile
        
        # Bring the main window to the foreground
        self.parent.deiconify()  # Ensure window is not minimized
        self.parent.focus_force()  # Force focus
        self.parent.lift()  # Bring window to the top



class ProfileLoader:
    def __init__(self, controller):
        self.controller = controller
    
    def load_profile(self, profile_name=None):
        """Load a profile. If profile_name is None, show a dialog to select a profile."""
        persistence = self.controller.persistence
        
        # If no profile name provided, show selection dialog
        if profile_name is None or profile_name not in persistence.get_profile_names():
            profiles = persistence.get_profile_names()
            current_profile = persistence.get_current_profile_name()
            
            dialog = ProfileSelectionDialog(
                self.controller.root, 
                "Load Profile", 
                profiles, 
                current_profile,
                "load"
            )
            
            if dialog.result is None:  # User cancelled
                return
                
            selected_profile = dialog.result
            
            # Create new profile if needed
            if selected_profile not in profiles:
                persistence.create_profile(selected_profile)
                
            profile_name = selected_profile
        
        # Suppress auto-saving while we are restoring a profile (we don't want each restored tab
        # to immediately rewrite settings.json).
        setattr(self.controller, "_is_loading_profile", True)
        try:
            # Clear current tabs
            notebook_view = self.controller.notebook_view
            notebook_view.remove_all_tabs()

            # Load playlists from the selected profile
            playlists = persistence.load_profile_settings(profile_name)
            for playlist_info in playlists:
                if playlist_info["type"] == "api":
                    # For Remote Playlists, use the source_id
                    source_id = playlist_info.get("source_id")
                    if source_id:
                        self.controller.controller_actions.toggle_remote_source(source_id, True)
                    else:
                        print(f"Warning: Skipping API playlist without source_id (legacy format)")
                else:
                    # For regular playlists, load them directly
                    self.controller.load_playlist(playlist_info["path"], playlist_info["title"])

            # Update UI - this will handle showing the Remote Playlist if needed
            self.controller.controller_actions.reload_open_playlists()

            # Set as current profile
            persistence.set_current_profile(profile_name)
        finally:
            # Re-enable auto-save after profile load completes (even if something fails).
            setattr(self.controller, "_is_loading_profile", False)

    def save_profile(self, profile_name=None):
        """Save current tabs to a profile. If profile_name is None, show a dialog to select a profile."""
        persistence = self.controller.persistence
        
        # If no profile name provided, show selection dialog   
        if profile_name is None:
            profiles = persistence.get_profile_names()
            current_profile = persistence.get_current_profile_name()
            
            dialog = ProfileSelectionDialog(
                self.controller.root, 
                "Save Profile", 
                profiles, 
                current_profile,
                "save"
            )
            
            if dialog.result is None:  # User cancelled
                return
                
            selected_profile = dialog.result
            
            # Create new profile if needed
            if selected_profile not in profiles:
                persistence.create_profile(selected_profile)
                
            # Set as current profile
            persistence.set_current_profile(selected_profile)
            profile_name = selected_profile
        
        # Get current tab state
        playlists = []
        tab_state = self.controller.controller_actions.get_tab_state()
        print(f"Saving profile {profile_name} with {len(tab_state)} tabs")
        
        for playlist in tab_state:
            title = playlist[0]
            path = playlist[1]
            ptype = playlist[2]
            source_id = playlist[3] if len(playlist) > 3 else None
            
            if ptype == "api":
                playlists.append({
                    "title": title, 
                    "path": path, 
                    "type": "api",
                    "source_id": source_id
                })
            else:
                playlists.append({"title": title, "path": path, "type": "local"})
            print(f"Added to profile: {title}, {path}, {ptype}")
            
        # Save to profile
        persistence.save_profile_settings(playlists, profile_name)
        print(f"Profile {profile_name} saved with {len(playlists)} playlists")
        
        # Update window title
        persistence.set_current_profile(profile_name)
        
        return playlists
        
    def manage_profiles(self, event=None):
        """Show dialog to manage profiles (rename, delete)"""
        persistence = self.controller.persistence
        profiles = persistence.get_profile_names()
        current_profile = persistence.get_current_profile_name()
        
        # Create a dialog window
        dialog = tk.Toplevel(self.controller.root)
        dialog.title("Manage Profiles")
        dialog.geometry("400x300")
        dialog.transient(self.controller.root)
        dialog.grab_set()
        dialog.focus_set()
        
        # Create a frame for the profile list
        frame = tk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Label
        tk.Label(frame, text="Profiles:", font=BOLD_FONT).pack(anchor="w")
        
        # Create a listbox for profiles
        listbox_frame = tk.Frame(frame)
        listbox_frame.pack(fill="both", expand=True, pady=5)
        
        listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE)
        listbox.pack(side="left", fill="both", expand=True)
        
        # Add scrollbar
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        for profile in profiles:
            listbox.insert(tk.END, profile)
            if profile == current_profile:
                listbox.selection_set(profiles.index(profile))
        
        # Buttons frame
        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=10)
        
        # Delete button
        def delete_profile():
            selected_idx = listbox.curselection()
            if not selected_idx:
                messagebox.showinfo("Info", "Please select a profile to delete")
                return
                
            profile_to_delete = profiles[selected_idx[0]]
            

                
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete the profile '{profile_to_delete}'?"):
                if persistence.delete_profile(profile_to_delete):
                    # Refresh the list
                    profiles.remove(profile_to_delete)
                    listbox.delete(selected_idx[0])
                    
                    # If current profile was deleted, update window title
                    if profile_to_delete == current_profile:
                        dialog.destroy()
                        self.load_profile(profiles[0])
                        # Bring the main window to the foreground
                        self.controller.root.deiconify()
                        self.controller.root.focus_force()
                        self.controller.root.lift()
                        title = f"Playlist Builder - {profiles[0]}"
                        self.controller.root.title(title)
        
        # Create new profile button
        def create_new_profile():
            new_name = simpledialog.askstring("New Profile", "Enter name for new profile:")
            if new_name and new_name.strip():
                new_name = new_name.strip()
                if new_name in profiles:
                    messagebox.showinfo("Info", f"Profile '{new_name}' already exists")
                    return
                    
                if persistence.create_profile(new_name):
                    profiles.append(new_name)
                    listbox.insert(tk.END, new_name)
                    listbox.selection_clear(0, tk.END)
                    listbox.selection_set(profiles.index(new_name))
                    persistence.set_current_profile(new_name)
                    title = f"Playlist Builder - {new_name}"
                    self.controller.root.title(title)
        
        # Switch to selected profile
        def switch_to_profile():
            selected_idx = listbox.curselection()
            if not selected_idx:
                messagebox.showinfo("Info", "Please select a profile to switch to")
                return
                
            profile_to_switch = profiles[selected_idx[0]]
            
            if profile_to_switch == current_profile:
                return
                
            dialog.destroy()
            self.load_profile(profile_to_switch)
            # Bring the main window to the foreground
            self.controller.root.deiconify()
            self.controller.root.focus_force()
            self.controller.root.lift()
            
        # Add buttons
        tk.Button(button_frame, text="Delete", command=delete_profile, font=DEFAULT_FONT).pack(side="left", padx=5)
        tk.Button(button_frame, text="New Profile", command=create_new_profile, font=DEFAULT_FONT).pack(side="left", padx=5)
        tk.Button(button_frame, text="Switch To", command=switch_to_profile, font=DEFAULT_FONT).pack(side="left", padx=5)
        tk.Button(button_frame, text="Close", command=dialog.destroy, font=DEFAULT_FONT).pack(side="right", padx=5)
        
        # Function to bring main window to foreground when dialog closes
        def on_dialog_close():
            dialog.destroy()
            # Bring the main window to the foreground
            self.controller.root.deiconify()  # Ensure window is not minimized
            self.controller.root.focus_force()  # Force focus
            self.controller.root.lift()  # Bring window to the top
            
        # Update the close button to use our custom close function
        button_frame.winfo_children()[-1].config(command=on_dialog_close)
        
        # Also handle the window close button (X)
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Make dialog modal
        dialog.wait_window()