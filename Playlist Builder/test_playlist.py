import os
import logging
import tkinter as tk
from tkinter import ttk, filedialog
from playlist_tab import PlaylistTab, CUSTOM_COLUMNS

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DummyApp:
    def __init__(self):
        self.current_settings = {}
        
    def set_status(self, message):
        print(f"STATUS: {message}")
        
    def update_idletasks(self):
        pass
        
    def update_prelisten_info(self, track_data):
        pass

def main():
    root = tk.Tk()
    root.title("Playlist Test")
    root.geometry("800x600")
    
    # Create a dummy app controller
    app = DummyApp()
    
    # Create a notebook to hold tabs
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Create a playlist tab
    tab = PlaylistTab(notebook, app)
    notebook.add(tab, text="Test Tab")
    
    # Add a button to open a playlist
    def open_playlist():
        filepath = filedialog.askopenfilename(
            title="Open Playlist",
            filetypes=[("M3U Playlists", "*.m3u *.m3u8"), ("All Files", "*.*")]
        )
        if filepath:
            logger.info(f"Selected playlist: {filepath}")
            success = tab.load_playlist_from_file(filepath)
            logger.info(f"Load result: {success}")
            logger.info(f"Track count: {len(tab._track_data)}")
            for i, track in enumerate(tab._track_data[:5]):  # Show first 5 tracks
                logger.info(f"Track {i+1}: {track.get('title')} - {track.get('path')} - Exists: {track.get('exists')}")
    
    button_frame = ttk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=10)
    
    open_button = ttk.Button(button_frame, text="Open Playlist", command=open_playlist)
    open_button.pack(side=tk.LEFT, padx=5)
    
    root.mainloop()

if __name__ == "__main__":
    main()
