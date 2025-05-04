
import sys

from metadata_utils import load_audio_metadata, save_audio_metadata
from utils import (APP_NAME, SETTINGS_FILE, DEFAULT_COLUMNS, AVAILABLE_COLUMNS, 
                             M3U_ENCODING, format_duration)
import tkinterdnd2 as tkdnd
import logging # Add logging import





# --- Main Execution ---

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                        filename='app.log', 
                        filemode='w') # Overwrite log each run
    # Add a console handler as well if desired
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # console_handler.setFormatter(formatter)
    # logging.getLogger('').addHandler(console_handler)
    
    logging.info("Application starting...")

    # Set up error trapping
    try:
        import sys
        import traceback
        import datetime
        
        def custom_excepthook(exctype, value, tb):
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = f"crash_log_{timestamp}.txt"
            
            with open(log_file, "w") as f:
                f.write("=== CRASH REPORT ===\n")
                f.write(f"Time: {timestamp}\n")
                f.write(f"Exception Type: {exctype.__name__}\n")
                f.write(f"Exception Value: {str(value)}\n\n")
                f.write("Traceback:\n")
                traceback.print_tb(tb, file=f)
                f.write("\nFull Traceback:\n")
                traceback.print_exception(exctype, value, tb, file=f)
            
            # Also print to console for immediate visibility
            print(f"\n[CRITICAL] Crash logged to {log_file}")
            traceback.print_exception(exctype, value, tb)
            
            # Show error dialog
            try:
                import tkinter.messagebox as msgbox
                msgbox.showerror("Critical Error", 
                                f"The application has crashed.\n"
                                f"Crash report saved to:\n{log_file}")
            except:
                pass
                
        # Install the custom exception handler
        sys.excepthook = custom_excepthook
        
        # Run the application normally
        root = tkdnd.TkinterDnD.Tk()
        from playlist_manager_app import PlaylistManagerApp
        app = PlaylistManagerApp(master=root)
        app.pack(fill="both", expand=True)

        # --- Ensure settings are saved on close ---
        def on_close():
            if hasattr(app, 'save_settings'):
                app.save_settings()
            root.destroy()
        root.protocol("WM_DELETE_WINDOW", on_close)

        root.mainloop()
        
    except Exception as e:
        print(f"[CRITICAL] Exception in main thread: {e}")
        import traceback
        traceback.print_exc()
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("Critical Error", f"The application encountered a critical error:\n{e}")
        except:
            pass