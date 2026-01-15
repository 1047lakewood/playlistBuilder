from tkinter import ttk, Menu, simpledialog
from models.playlist import Playlist
import utils
from typing import List
from playlist_tab import PlaylistTabView
from tkinterdnd2 import DND_FILES

class PlaylistNotebookView:
    def __init__(self, parent, controller, callbacks):
        self.controller = controller
        # Use the notebook_frame from container_view instead of parent directly
        self.notebook = ttk.Notebook(parent.notebook_frame)
        self.callbacks = callbacks
        self.notebook.pack(fill="both", expand=True)
        self.dragging_tab_index = None
        # Bind right-click event to show context menu
        self.notebook.bind("<Button-3>", self.show_tab_context_menu)
        self.notebook.bind("<Button-1>", self.button_down)
        self.notebook.bind("<B1-Motion>", self.dragged)
        self.notebook.bind("<ButtonRelease-1>", self.button_up)
    # not sure
    def get_tab_playlists(self):
        playlists = []
        for tab in self.notebook.tabs():
            view = self.notebook.nametowidget(tab)
            playlists.append(view.playlist)
        return playlists
    def get_tab_state(self):
        tab_state = []
        for tab_id in self.notebook.tabs():
            try:
                view = self.notebook.nametowidget(tab_id)
                title = view.title
                playlist = view.playlist
                if playlist.type == Playlist.PlaylistType.API:
                    path = playlist.path
                    source_id = getattr(playlist, 'source_id', None)
                    # Store source_id for API playlists
                    tab_state.append((title, path, "api", source_id))
                else:
                    path = playlist.path
                    tab_state.append((title, path, "local", None))
                print(f"Saving tab: {title}, {path}")
            except Exception as e:
                print(f"Error getting tab state: {e}")
        print(f"Total tabs saved: {len(tab_state)}")
        return tab_state
    
    def get_api_tabs(self):
        """Get all tabs that are API/remote playlists."""
        api_tabs = []
        for tab_name in self.notebook.tabs():
            tab = self.notebook.nametowidget(tab_name)
            if hasattr(tab, 'playlist') and tab.playlist.type == Playlist.PlaylistType.API:
                api_tabs.append(tab)
        return api_tabs
    
    def get_tab_by_source(self, source_id: str):
        """Get a tab by its source ID."""
        for tab_name in self.notebook.tabs():
            tab = self.notebook.nametowidget(tab_name)
            if (hasattr(tab, 'playlist') and 
                tab.playlist.type == Playlist.PlaylistType.API and
                getattr(tab.playlist, 'source_id', None) == source_id):
                return tab
        return None
    def get_tabs(self):
        tabs = []
        for tab_name in self.notebook.tabs():
            tabs.append(self.notebook.nametowidget(tab_name))
        return tabs
    def add_tab(self, playlist: Playlist, title: str = "New Playlist"):
        # if current tab is empty, delete it
        try:
            if self.notebook.select():
                current_tab = self.notebook.select()
                current_tab_view = self.notebook.nametowidget(current_tab)
                if current_tab_view.is_empty():
                    self.remove_tab(current_tab_view)
                        
            new_tab = PlaylistTabView(self.notebook, self.controller, playlist=playlist, title=title, callbacks=self.callbacks)
            return new_tab
        except Exception as e:
            print("Failed to add tab")
            print(e)
            return None
    
    def get_selected_tab(self):
        selected_tab = self.notebook.select()
        return self.notebook.nametowidget(selected_tab)
    def get_selected_tab_playlist(self):
        selected_tab = self.get_selected_tab()
        return selected_tab.playlist

    def remove_tab(self, tab):
        # If this is a Remote Playlist tab, update the menu bar and currently playing bar
        if hasattr(tab, 'playlist') and hasattr(tab.playlist, 'type') and tab.playlist.type == Playlist.PlaylistType.API:
            if hasattr(tab.playlist, 'source_id') and tab.playlist.source_id:
                source_id = tab.playlist.source_id
                self.controller.menu_bar.set_source_connected(source_id, False)
                self.controller.container_view.remove_station(source_id)
                self.controller._currently_playing_contexts.pop(source_id, None)
        self.controller.controller_actions.close_playlist(tab.playlist)
        # Remove from notebook UI and fully destroy the widget so any background timers
        # (e.g., periodic "currently playing" polling) cannot resurrect the now playing bar.
        self.notebook.forget(tab)
        try:
            tab.destroy()
        except Exception:
            pass

    
    def remove_all_tabs(self):
        for tab in self.notebook.tabs():
            self.remove_tab(self.notebook.nametowidget(tab))
    
    def refresh_theme_colors(self):
        """Refresh theme colors for all tabs."""
        for tab_id in self.notebook.tabs():
            try:
                tab_view = self.notebook.nametowidget(tab_id)
                if hasattr(tab_view, 'refresh_theme_colors'):
                    tab_view.refresh_theme_colors()
            except Exception as e:
                print(f"Error refreshing tab colors: {e}")

    def reorder_tabs(self, old_index, new_index):
        if old_index == new_index:
            return
        self.notebook.insert(self.notebook.tabs()[new_index], self.notebook.tabs()[old_index])
        
# drag to reorder tabs
    def button_down(self, event):
        try:
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
            if tab_index >= 0 and tab_index < len(self.notebook.tabs()):
                self.dragging_tab_index = tab_index
        except Exception as e:
            pass
    
    def dragged(self, event):
        try:
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
            if tab_index >= 0 and tab_index < len(self.notebook.tabs()):
                if tab_index != self.dragging_tab_index:
                    self.reorder_tabs(self.dragging_tab_index, tab_index)
                    self.dragging_tab_index = tab_index
        except Exception as e:
            pass
    
    def button_up(self, event):
        self.dragging_tab_index = None





# renaming and delete tab
    def show_tab_context_menu(self, event):
        """Show context menu when right-clicking on a tab"""
        # Identify which tab was clicked
        try:
            tab_index = self.notebook.index(f"@{event.x},{event.y}")
            if tab_index >= 0 and tab_index < len(self.notebook.tabs()):
                tab_name = self.notebook.tabs()[tab_index]
                tab = self.notebook.nametowidget(tab_name)
                # Create context menu
                context_menu = Menu(self.notebook, tearoff=0)
                context_menu.add_command(label="Rename Tab", command=lambda: self.rename_tab(tab))
                context_menu.add_command(label="Delete Tab", command=lambda: self.delete_tab(tab))
                
                # Display the menu
                context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            pass
        finally:
            # Make sure to release the grab
            try:
                context_menu.grab_release()
            except:
                pass
    
    def rename_tab(self, tab):
        """Rename the tab at the given index"""
        new_title = simpledialog.askstring("Rename Tab", "Enter new tab name:", initialvalue=tab.title)
        if new_title:
            tab.title = new_title
            self.notebook.tab(tab, text=new_title)
            
    def delete_tab(self, tab):
        """Delete the tab at the given index"""
        self.remove_tab(tab)



