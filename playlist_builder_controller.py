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
            "search": self.toggle_search,
            "on_interaction": self.on_user_interaction
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
        
        # Populate remote sources menu after playlist_service is initialized
        self._setup_remote_sources_menu()

        self.notebook_view = PlaylistNotebookView(self.container_view, self, self.callbacks)
        self.tree_interaction_controller = TreeInteractionController(self)

        # Track currently playing context per source_id
        self._currently_playing_contexts = {}

        current_profile = self.persistence.get_current_profile_name()
        self.profile_loader.load_profile(current_profile)
        # NOTE:
        # Remote playlists are restored from the current profile. We intentionally do NOT
        # auto-connect all configured remote sources on startup, so that unchecking a remote
        # source persists across app restarts.

    def refresh_remote_sources_menu(self):
        """Refresh the remote sources menu with current configuration."""
        self._setup_remote_sources_menu()

    def _auto_connect_all_remote_sources(self):
        """Automatically connect all available remote playlist sources."""
        try:
            sources = self.playlist_service.get_available_sources()
            if not sources:
                print("No remote sources configured for auto-connection.")
                return

            print(f"Auto-connecting {len(sources)} remote playlist source(s): {sources}")

            # Update status bar to show connecting message
            import tkinter.messagebox as messagebox
            connecting_msg = f"Connecting to {len(sources)} remote source(s)..."
            self.root.title(f"Playlist Builder - {connecting_msg}")

            for source_id, source_name in sources:
                print(f"Attempting to connect to {source_name} ({source_id})...")
                try:
                    self.controller_actions.toggle_remote_source(source_id, True)
                    print(f"Successfully connected to {source_name}")
                except Exception as e:
                    print(f"Failed to connect to {source_name}: {e}")
                    # Don't show error dialogs during auto-connect, just log
                    continue

            # Reset title
            current_profile = self.persistence.get_current_profile_name()
            self.root.title(f"Playlist Builder - {current_profile}")

        except Exception as e:
            print(f"Error during auto-connection setup: {e}")
            import traceback
            traceback.print_exc()

    # tree interaction - tree events
    def button_down(self, event): self.tree_interaction_controller.button_down(event)
    def dragged(self, event): self.tree_interaction_controller.dragged(event)
    def button_up(self, event): self.tree_interaction_controller.button_up(event)

    def on_user_interaction(self, event=None):
        """Notify the current tab that user is interacting (for auto-reload deferral)."""
        try:
            tab = self.get_selected_tab()
            if tab and hasattr(tab, 'mark_user_interacting'):
                tab.mark_user_interacting()
        except Exception:
            pass

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
    
    def _setup_remote_sources_menu(self):
        """Setup the remote sources submenu with available sources."""
        sources = self.playlist_service.get_available_sources()
        self.menu_bar.populate_remote_sources(
            sources, 
            self.controller_actions.toggle_remote_source
        )

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
        # Get source info from the tab's playlist
        source_id = getattr(tab_view.playlist, 'source_id', None) if tab_view else None
        source_name = self._get_source_name(source_id) if source_id else None
        
        if not track:
            if source_id:
                self._currently_playing_contexts.pop(source_id, None)
                self.container_view.update_currently_playing_bar(
                    text="Currently Playing: —",
                    source_id=source_id,
                    source_name=source_name
                )
            return

        display_text = self._format_track_display(track)
        bar_text = f"Currently Playing: {display_text}"

        if can_focus and track.path:
            context = {"tab": tab_view, "track_path": track.path}
            if source_id:
                self._currently_playing_contexts[source_id] = context
            self.container_view.update_currently_playing_bar(
                bar_text, 
                clickable=True, 
                on_click=lambda sid=source_id: self.scroll_to_currently_playing(sid),
                source_id=source_id,
                source_name=source_name
            )
        else:
            context = {"tab": tab_view, "track_path": track.path if track.path else None}
            if source_id:
                self._currently_playing_contexts[source_id] = context
            self.container_view.update_currently_playing_bar(
                bar_text, 
                clickable=False,
                source_id=source_id,
                source_name=source_name
            )
    
    def _get_source_name(self, source_id):
        """Get the display name for a source_id."""
        if not source_id:
            return None
        for sid, name in self.playlist_service.get_available_sources():
            if sid == source_id:
                return name
        return source_id  # Fallback to ID if name not found

    def scroll_to_currently_playing(self, source_id=None, event=None):
        """Focus the tree on the currently playing track.
        
        Args:
            source_id: The source to scroll to. If None, uses the first available context.
        """
        # Get the context for this source
        if source_id and source_id in self._currently_playing_contexts:
            context = self._currently_playing_contexts[source_id]
        elif self._currently_playing_contexts:
            # Fallback to first available
            context = next(iter(self._currently_playing_contexts.values()))
        else:
            return

        track_path = context.get("track_path")
        if not track_path:
            return

        tab_view = context.get("tab")
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
        """Refresh theme colors and remote sources menu for all widgets after settings change."""
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

            # Refresh remote sources menu
            self.refresh_remote_sources_menu()
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
            Label(about_window, text="Version 0.7.5").pack()
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