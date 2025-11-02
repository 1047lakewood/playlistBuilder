import tkinter as tk
from tkinterdnd2 import TkinterDnD
from container_view import ContainerView
from menu_bar import MenuBar
from keyboard_bindings import KeyboardBindings
from playlist_builder_controller import PlaylistBuilderController
from font_config import configure_ttk_styles

def main():
    root = TkinterDnD.Tk()
    root.geometry("1400x800")
    
    # Configure fonts for the application
    configure_ttk_styles()

    controller = PlaylistBuilderController(root)
    # container_view = ContainerView(root, menu_bar=menu_bar, bindings = keyboard_bindings)
    

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