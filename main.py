import tkinter as tk
from tkinterdnd2 import TkinterDnD
from container_view import ContainerView
from menu_bar import MenuBar
from keyboard_bindings import KeyboardBindings
from playlist_builder_controller import PlaylistBuilderController
from font_config import configure_ttk_styles
import os
import sys


def _configure_stdio_encoding():
    """
    Prevent Windows console UnicodeEncodeError ('charmap' codec can't encode...)
    when printing file paths/metadata containing non-ASCII characters.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            # Best-effort only; app should still run even if reconfigure isn't supported.
            pass

def main():
    _configure_stdio_encoding()
    root = TkinterDnD.Tk()
    root.geometry("1400x800")  # Default size

    # Configure fonts and styles for the application
    configure_ttk_styles()

    controller = PlaylistBuilderController(root)

    # Restore saved window geometry and state (must be done after window is realized)
    saved_geometry, saved_state = controller.persistence.get_window_geometry()
    if saved_geometry:
        root.update_idletasks()  # Ensure window is fully realized
        root.geometry(saved_geometry)
    if saved_state and saved_state != "normal":
        root.state(saved_state)

    def on_closing():
        if hasattr(controller, 'on_close'):
            controller.on_close()  # optional: cleanup logic inside App class
        root.destroy()
    
    def on_resize(event):
        if resize_after_id:
            root.after_cancel(resize_after_id)
        resize_after_id = root.after(200, handle_resize)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.protocol("WM_SIZE", on_resize)

    root.mainloop()
    # # Perform any cleanup here (save state, close threads, etc.)
    # if messagebox.askokcancel("Quit", "Do you want to quit?"):
    #     print("Closing the app cleanly...")
    # else:
    #     return

if __name__ == "__main__":
    main()