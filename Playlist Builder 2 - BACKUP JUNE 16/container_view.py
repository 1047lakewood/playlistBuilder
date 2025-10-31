import tkinter as tk
from tkinter import messagebox, Frame
from playlist_notebook_view import PlaylistNotebookView
from prelisten_view import PrelistenView



class ContainerView(Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.pack(fill="both", expand=True, padx=5, pady=0)  # Reduced padding, especially on top
        
        # Create a frame for the notebook view with a subtle border and background using ttk style
        self.notebook_frame = tk.ttk.Frame(self, style="NotebookFrame.TFrame")
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

