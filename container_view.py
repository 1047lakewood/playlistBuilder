import tkinter as tk
from tkinter import messagebox, Frame
from tkinter import ttk
from playlist_notebook_view import PlaylistNotebookView
from prelisten_view import PrelistenView
import theme_manager



class ContainerView(Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True, padx=5, pady=0)  # Reduced padding, especially on top

        # Currently playing bar at the top (initially hidden)
        self.currently_playing_frame = tk.Frame(self, bg=theme_manager.get_color("currently_playing_bg", "#d4edda"))
        # Don't pack initially - will be shown when remote playlist is loaded

        self._currently_playing_callback = None
        self.currently_playing_label = tk.Label(
            self.currently_playing_frame,
            text="Currently Playing: —",
            anchor="w",
            bg=theme_manager.get_color("currently_playing_bg", "#d4edda"),
            fg=theme_manager.get_color("currently_playing_fg", "#155724"),
            padx=12,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        )
        self.currently_playing_label.pack(fill="x")
        self.currently_playing_label.bind("<Button-1>", self._handle_currently_playing_click)

        # Create a frame for the notebook view with a subtle border and background using ttk style
        self.notebook_frame = ttk.Frame(self, style="NotebookFrame.TFrame")
        self.notebook_frame.pack(fill="both", expand=True, padx=0, pady=0)  # Remove padding inside the container
        
        # This will store the prelisten view when active
        self.prelisten_view = None
        self.prelisten_height = 150  # Default height for prelisten view
        
        # Track the original notebook frame height
        self.original_notebook_height = None


    # def add_actions(self):
    #     self.actions = {
    #         "open": (self.open_playlist, "Ctrl+O"),
    #         "save": (self.save_playlist, "Ctrl+S")
    #         }
            
    def show_prelisten_view(self, track):
        """Show the prelisten view for a track"""
        # If there's already a prelisten view, close it first
        if self.prelisten_view:
            self.close_prelisten_view()
        
        # Store the original notebook height if not already stored
        if not self.original_notebook_height:
            self.original_notebook_height = self.notebook_frame.winfo_height()
        
        # Resize the notebook frame to make room for the prelisten view
        self.notebook_frame.configure(height=self.original_notebook_height - self.prelisten_height)
        
        # Create the prelisten view
        self.prelisten_view = PrelistenView(self, track, self.close_prelisten_view)
        self.prelisten_view.pack(side="bottom", fill="x")
        self.prelisten_view.configure(height=self.prelisten_height)
        
    def close_prelisten_view(self):
        """Close the prelisten view and restore the notebook view"""
        if self.prelisten_view:
            self.prelisten_view.destroy()
            self.prelisten_view = None
            
            # Restore the notebook frame to its original size
            if self.original_notebook_height:
                self.notebook_frame.configure(height=self.original_notebook_height)

    def show_currently_playing_bar(self):
        """Show the currently playing bar if not already visible."""
        if not self.currently_playing_frame.winfo_ismapped():
            self.currently_playing_frame.pack(fill="x", padx=0, pady=(0, 4), before=self.notebook_frame)

    def hide_currently_playing_bar(self):
        """Hide the currently playing bar."""
        if self.currently_playing_frame.winfo_ismapped():
            self.currently_playing_frame.pack_forget()

    def update_currently_playing_bar(self, text="Currently Playing: —", clickable=False, on_click=None):
        """Update the currently playing bar text and click behaviour."""
        self.currently_playing_label.config(text=text)

        if clickable and on_click:
            self._currently_playing_callback = on_click
            self.currently_playing_label.config(cursor="hand2", 
                                               fg=theme_manager.get_color("currently_playing_hover", "#0f5132"))
        else:
            self._currently_playing_callback = None
            self.currently_playing_label.config(cursor="", 
                                               fg=theme_manager.get_color("currently_playing_fg", "#155724"))

    def _handle_currently_playing_click(self, _event):
        if self._currently_playing_callback:
            self._currently_playing_callback()
    
    def refresh_theme_colors(self):
        """Refresh colors from theme manager."""
        bg_color = theme_manager.get_color("currently_playing_bg", "#d4edda")
        fg_color = theme_manager.get_color("currently_playing_fg", "#155724")
        
        # Update frame and label backgrounds
        self.currently_playing_frame.config(bg=bg_color)
        self.currently_playing_label.config(bg=bg_color, fg=fg_color)

