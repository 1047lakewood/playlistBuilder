import tkinter as tk
from tkinter import messagebox, Frame
from tkinter import ttk
from playlist_notebook_view import PlaylistNotebookView
from prelisten_view import PrelistenView



class ContainerView(Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True, padx=5, pady=0)  # Reduced padding, especially on top

        # Currently playing bar at the top (initially hidden)
        self.currently_playing_frame = tk.Frame(self, bg="#d4edda")
        # Don't pack initially - will be shown when remote playlist is loaded

        # Store callbacks and data per source
        self._station_callbacks = {}  # source_id -> callback
        self._station_labels = {}     # source_id -> label widget
        self._station_order = []      # ordered list of source_ids
        
        # Container for station labels
        self._stations_container = tk.Frame(self.currently_playing_frame, bg="#d4edda")
        self._stations_container.pack(fill="x", expand=True)

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

    def update_currently_playing_bar(self, text="Currently Playing: —", clickable=False, on_click=None, source_id=None, source_name=None):
        """Update the currently playing bar for a specific source.
        
        Args:
            text: Display text for currently playing track
            clickable: Whether clicking should scroll to the track
            on_click: Callback when clicked
            source_id: Unique identifier for the source/station
            source_name: Display name for the source (used in label)
        """
        if source_id is None:
            # Legacy call without source_id - use default
            source_id = "_default"
            source_name = source_name or ""
        
        # Create label for this source if it doesn't exist
        if source_id not in self._station_labels:
            self._create_station_label(source_id, source_name)
        
        label = self._station_labels[source_id]
        
        # Build display text with source name prefix if we have multiple stations
        if source_name and len(self._station_labels) > 1:
            display_text = f"[{source_name}] {text}"
        else:
            display_text = text
            
        label.config(text=display_text)

        if clickable and on_click:
            self._station_callbacks[source_id] = on_click
            label.config(cursor="hand2", fg="#0f5132")
        else:
            self._station_callbacks[source_id] = None
            label.config(cursor="", fg="#155724")
    
    def _create_station_label(self, source_id, source_name):
        """Create a new label for a station."""
        # Add to order tracking
        if source_id not in self._station_order:
            self._station_order.append(source_id)

        label = tk.Label(
            self._stations_container,
            text="Currently Playing: —",
            anchor="w",
            bg="#d4edda",
            fg="#155724",
            padx=12,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        )
        label.pack(side="left", fill="x", expand=True)
        label.bind("<Button-1>", lambda e, sid=source_id: self._handle_station_click(sid))

        self._station_labels[source_id] = label
        self._station_callbacks[source_id] = None
    
    def remove_station(self, source_id):
        """Remove a station's label from the bar."""
        if source_id in self._station_labels:
            self._station_labels[source_id].destroy()
            del self._station_labels[source_id]
        if source_id in self._station_callbacks:
            del self._station_callbacks[source_id]
        if source_id in self._station_order:
            self._station_order.remove(source_id)
        
        # Hide bar if no stations left
        if not self._station_labels:
            self.hide_currently_playing_bar()

    def _handle_station_click(self, source_id):
        """Handle click on a specific station's label."""
        callback = self._station_callbacks.get(source_id)
        if callback:
            callback()
    
    def refresh_theme_colors(self):
        """Refresh colors - using hardcoded defaults."""
        bg_color = "#d4edda"
        fg_color = "#155724"
        
        # Update frame backgrounds
        self.currently_playing_frame.config(bg=bg_color)
        self._stations_container.config(bg=bg_color)
        
        # Update all station labels
        for label in self._station_labels.values():
            label.config(bg=bg_color, fg=fg_color)

