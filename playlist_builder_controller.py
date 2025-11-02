import os
from container_view import ContainerView
from menu_bar import MenuBar
from keyboard_bindings import KeyboardBindings
from playlist_notebook_view import PlaylistNotebookView,PlaylistTabView
from tkinter import ttk, messagebox, Toplevel, Label, Button
from controller_actions import ControllerActions
from PlaylistService.playlist_service import PlaylistServiceManager
from persistence import Persistence
from profile_loader import ProfileLoader
from file_utils import FileUtils    
from tree_interaction_controller import TreeInteractionController
from settings_dialog import SettingsDialog

class PlaylistBuilderController:
    def __init__(self, root):
        self.root = root
        self.root.title("Playlist Builder")
        self.container_view = ContainerView(root, self)
        self.menu_bar = MenuBar(self.root)
        self.bindings = KeyboardBindings(self.root)
        
        self.persistence = Persistence(self)
        self.profile_loader = ProfileLoader(self)
        
        self.controller_actions = ControllerActions(self)


        self.playlist_service = PlaylistServiceManager()


        self.callbacks = {
            "button_down": self.button_down,
            "dragged": self.dragged,
            "button_up": self.button_up,
            "copy": self.copy_tracks,
            "cut": self.cut_tracks,
            "delete": self.delete_tracks,
            "paste": self.paste_tracks,
            "drop_files_in_tab": self.dropped_files_in_tab,
            "hover_with_files": self.hover_with_files,
            "double_click": self.handle_double_click,
            "search": self.toggle_search
        }



        # Add about and settings actions
        self.actions = self.controller_actions.actions
        self.actions["about"] = self.show_about_dialog
        self.actions["settings"] = self.open_settings_dialog
        
        self.bindings.bind(self.actions)
        self.bindings.bind(self.callbacks)

        # Menu Bar
        # Combine actions and callbacks for the menu bar
        combined_callbacks = {**self.actions, **self.callbacks}
        self.menu_bar.create_menu_bar(combined_callbacks, self.get_binding_display_names())
        self.root.config(menu=self.menu_bar)

        
        

        
        self.notebook_view = PlaylistNotebookView(self.container_view, self, self.callbacks)
        self.tree_interaction_controller = TreeInteractionController(self)

        self._currently_playing_context = None
        self.container_view.update_currently_playing_bar()

        current_profile = self.persistence.get_current_profile_name() 
        self.profile_loader.load_profile(current_profile)

    # tree interaction - tree events
    def button_down(self, event): self.tree_interaction_controller.button_down(event)
    def dragged(self, event): self.tree_interaction_controller.dragged(event)
    def button_up(self, event): self.tree_interaction_controller.button_up(event)

    def copy_tracks(self, event=None): self.tree_interaction_controller.copy_tracks(event)
    def cut_tracks(self, event=None): self.tree_interaction_controller.cut_tracks(event)
    def delete_tracks(self, event=None): self.tree_interaction_controller.delete_tracks(event)
    def paste_tracks(self, event=None): self.tree_interaction_controller.paste_tracks(event)
    def dropped_files_in_tab(self, event): self.tree_interaction_controller.dropped_files_in_tab(event)
    def hover_with_files(self, event): self.tree_interaction_controller.hover_with_files(event)
    # get tree info
    def get_selected_tab(self): return self.notebook_view.get_selected_tab()
    def get_selected_tab_tree(self): return self.get_selected_tab().tree
    def get_selected_tab_playlist(self): return self.get_selected_tab().playlist
    def get_selected_rows(self):
        row_ids = self.get_selected_tab_tree().selection()
        row_indices = [self.get_selected_tab_tree().index(row_id) for row_id in row_ids]
        tracks = [self.get_selected_tab_playlist().tracks[i] for i in row_indices]
        return (row_ids, row_indices, tracks)




    def load_playlist(self, playlist_path, title):
        playlist = self.playlist_service.load_playlist_from_path(playlist_path)
        self.notebook_view.add_tab(playlist, title)

    def get_binding_display_names(self):
        display_names = {}
        # Get display names for actions
        for action_name in self.actions.keys():
            display_names[action_name] = self.bindings.get_display_name(action_name)
        # Get display names for callbacks
        for callback_name in self.callbacks.keys():
            if callback_name in self.bindings.bindings:
                display_names[callback_name] = self.bindings.get_display_name(callback_name)
        return display_names

    def open_file_location(self):
        selected_tracks = self.get_selected_rows()[2]
        if len(selected_tracks) != 1:
            messagebox.showerror("Error", "Please select only one track")
            return
        FileUtils.open_file_location(selected_tracks[0].path)
    
    def open_in_audacity(self):
        selected_tracks = self.get_selected_rows()[2]
        if len(selected_tracks) != 1:
            messagebox.showerror("Error", "Please select only one track")
            return
        FileUtils.open_in_audacity(selected_tracks[0].path)
        
    def handle_double_click(self, event):
        """Handle double-click on a track to open the prelisten view"""
        try:
            # Get the clicked item
            tree = self.get_selected_tab_tree()
            item = tree.identify('item', event.x, event.y)
            if not item:
                return
                
            # Get the track
            index = tree.index(item)
            track = self.get_selected_tab_playlist().tracks[index]
            
            # Check if file exists
            if not track.exists:
                messagebox.showerror("Error", "Cannot prelisten: File does not exist")
                return
                
            # Show the prelisten view
            self.container_view.show_prelisten_view(track)
        except Exception as e:
            print(f"Error in handle_double_click: {str(e)}")
            messagebox.showerror("Error", f"Failed to open prelisten view: {str(e)}")
            
    def toggle_search(self, event=None):
        """Toggle the search frame in the current tab"""
        try:
            tab = self.get_selected_tab()
            if tab:
                tab.toggle_search()
        except Exception as e:
            print(f"Error toggling search: {str(e)}")
            messagebox.showerror("Error", f"Failed to toggle search: {str(e)}")

    def notify_currently_playing(self, track, tab_view, can_focus):
        """Update the top bar with currently playing information.

        Args:
            track: Track instance or None.
            tab_view: PlaylistTabView where the track resides.
            can_focus: Whether we can scroll to the track.
        """
        if not track:
            self._currently_playing_context = None
            self.container_view.update_currently_playing_bar()
            return

        display_text = self._format_track_display(track)
        bar_text = f"Currently Playing: {display_text}"

        if can_focus and track.path:
            self._currently_playing_context = {"tab": tab_view, "track_path": track.path}
            self.container_view.update_currently_playing_bar(bar_text, clickable=True, on_click=self.scroll_to_currently_playing)
        else:
            self._currently_playing_context = {"tab": tab_view, "track_path": track.path if track.path else None}
            self.container_view.update_currently_playing_bar(bar_text, clickable=False)

    def scroll_to_currently_playing(self, event=None):
        """Focus the tree on the currently playing track."""
        if not self._currently_playing_context:
            return

        track_path = self._currently_playing_context.get("track_path")
        if not track_path:
            return

        tab_view = self._currently_playing_context.get("tab")
        tab_view = self._resolve_tab_for_track(tab_view, track_path)
        if not tab_view:
            return

        try:
            self.notebook_view.notebook.select(tab_view)
        except Exception:
            pass

        tab_view.scroll_to_track(track_path)

    def _resolve_tab_for_track(self, tab_view, track_path):
        """Ensure we have a valid tab reference for a track path."""
        if tab_view and tab_view in self.notebook_view.get_tabs():
            return tab_view

        # Fallback: locate tab containing the track path
        for candidate in self.notebook_view.get_tabs():
            for track in candidate.playlist.tracks:
                if track.path == track_path:
                    self._currently_playing_context["tab"] = candidate
                    return candidate
        return None

    def _format_track_display(self, track):
        parts = []
        if getattr(track, "artist", None):
            parts.append(track.artist)
        if getattr(track, "title", None):
            parts.append(track.title)
        if parts:
            return " - ".join(parts)
        if getattr(track, "path", None):
            return os.path.basename(track.path)
        return "Unknown Track"
            
    def open_settings_dialog(self, event=None):
        """Open the settings dialog modally."""
        try:
            SettingsDialog(self.root, on_apply=self.refresh_theme_colors)
        except Exception as e:
            print(f"Error opening settings dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to open settings dialog: {str(e)}")
    
    def refresh_theme_colors(self):
        """Refresh theme colors for all widgets after settings change."""
        try:
            # Refresh container view (currently playing bar)
            if hasattr(self, 'container_view') and hasattr(self.container_view, 'refresh_theme_colors'):
                self.container_view.refresh_theme_colors()
            
            # Refresh all notebook tabs
            if hasattr(self, 'notebook_view') and hasattr(self.notebook_view, 'refresh_theme_colors'):
                self.notebook_view.refresh_theme_colors()
            
            # Refresh prelisten view if it exists
            if hasattr(self, 'container_view') and self.container_view.prelisten_view:
                if hasattr(self.container_view.prelisten_view, 'refresh_theme_colors'):
                    self.container_view.prelisten_view.refresh_theme_colors()
        except Exception as e:
            print(f"Error refreshing theme colors: {e}")

    def show_about_dialog(self, event=None):
        """Show the About dialog with program name and developer information"""
        try:
            about_window = Toplevel(self.root)
            about_window.title("About Playlist Builder")
            about_window.geometry("300x200")
            about_window.resizable(False, False)
            about_window.transient(self.root)  # Set as transient to main window
            about_window.grab_set()  # Make modal
            
            # Center the window relative to the main window
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (300 // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (150 // 2)
            about_window.geometry(f"+{x}+{y}")
            
            # Add content
            Label(about_window, text="Playlist Builder 2", font=("Helvetica", 16, "bold")).pack(pady=(20, 5))
            Label(about_window, text="Version 0.5.2").pack()
            Label(about_window, text="Developed by AM Leonard").pack(pady=(5, 15))
            Label(about_window, text="for Harav Shlomo Perr").pack(pady=(0, 5))
            Label(about_window, text="104.7 (88.7) Lakewood").pack(pady=(0, 5))
            # Close button
            Button(about_window, text="Close", command=about_window.destroy).pack(pady=(5, 15))
            
            # Make sure the window appears on top
            about_window.lift()
            about_window.focus_force()
            
        except Exception as e:
            print(f"Error showing about dialog: {str(e)}")
            messagebox.showerror("Error", f"Failed to show about dialog: {str(e)}")