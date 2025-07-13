from tkinter import ttk, Menu, Entry, Frame, StringVar, Label, Toplevel
import utils
from font_config import DEFAULT_FONT, BOLD_FONT, DEFAULT_FONT_TUPLE

class PlaylistTabContextMenu:
    def __init__(self, parent):
        self.parent = parent
        self.context_menu = Menu(self.parent, tearoff=0)
        self.context_menu.add_command(label="Edit Metadata", command=self.parent.controller.controller_actions.open_edit_metadata_dialog)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Cut", command=self.parent.controller.cut_tracks)
        self.context_menu.add_command(label="Copy", command=self.parent.controller.copy_tracks)
        self.context_menu.add_command(label="Paste", command=self.parent.controller.paste_tracks)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Delete", command=self.parent.controller.delete_tracks)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Open File Location", command=self.parent.controller.open_file_location)
        self.context_menu.add_command(label="Open in Audacity", command=self.parent.controller.open_in_audacity)
        self.context_menu.add_command(label="Convert to MP3", command=self.parent.controller.controller_actions.convert_tracks_to_mp3)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rename File Path", command=self.parent.controller.controller_actions.rename_track_file_path_dialog)
        self.context_menu.add_command(label="Rename by Browsing", command=self.parent.controller.controller_actions.rename_track_by_browsing_dialog)
        self.context_menu.add_command(label="Replace from Macro Output", command=self.parent.controller.controller_actions.replace_from_macro_output_action)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Reload Remote Playlist", command=self.parent.controller.controller_actions.reload_api_playlist_action)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Calculate Start Times", command=self.parent.controller.controller_actions.open_calculate_start_times_dialog)


    def show(self, event):
        row_id = self.parent.tree.identify_row(event.y_root - self.parent.tree.winfo_rooty())
        selected_rows = self.parent.tree.selection()
        if len(selected_rows) > 1:
            if row_id not in selected_rows:    
                self.parent.tree.selection_set(row_id)
        else:
            self.parent.tree.selection_set(row_id)


        self.context_menu.tk_popup(event.x_root, event.y_root)
     

class Tooltip:
    """Tooltip widget that appears when hovering over an element"""
    def __init__(self, parent):
        self.parent = parent
        self.tip_window = None
        self.id = None
        self.x = self.y = 0
        self.scheduled_id = None

    def show_tip(self, text, x, y):
        """Display text in a tooltip window"""
        if self.tip_window or not text:
            return
            
        # Create tooltip window
        self.tip_window = Toplevel(self.parent)
        self.tip_window.withdraw()
        self.tip_window.overrideredirect(True)  # Remove window decorations
        
        # Create label with tooltip text with improved styling
        label = Label(self.tip_window, text=text, justify='left',
                      background='#F5F5F5', relief='solid', borderwidth=1,
                      font=("Segoe UI", 10, "normal"), padx=8, pady=5)
        label.pack()
        
        # Position tooltip below cursor
        self.tip_window.geometry(f"+{x-500}+{y+15}")
        self.tip_window.deiconify()

    def hide_tip(self):
        """Hide the tooltip"""
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class PlaylistTabTreeView(ttk.Treeview):
    def __init__(self, parent, callbacks):
        self.parent = parent
        self.callbacks = callbacks
        self.columns = ["#", "Start Time", "•", "Artist", "Title", "Duration", "Path"]
        super().__init__(parent, columns=self.columns, show="headings")
        
        # Apply font to treeview
        self.configure(style="Treeview")

        # Create and style scrollbar
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=self.yview)
        self.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.pack(side="left", fill="both", expand=True, padx=5, pady=5)  # Add padding around treeview
        
        # Set Headings with improved styling
        for col in self.columns:
            self.heading(col, text=col.title())

        # Improved column widths and styling
        self.column("#", width=50, stretch=False, anchor="center")
        self.column("Start Time", width=140, stretch=False)
        self.column("•", width=20, stretch=False, anchor="center")
        self.column("Artist", width=220, stretch=False)
        self.column("Title", width=220, stretch=True)
        self.column("Duration", width=90, anchor="center", stretch=False)
        self.column("Path", width=150, stretch=True)
        
        # Configure tags for row styling with improved colors
        self.tag_configure("missing_file", foreground="#FF3B30")  # Brighter red
        self.tag_configure("search_match", background="#E8F0FE")  # Lighter blue
        self.tag_configure("search_current", background="#BBDEFB")  # Medium blue
        self.tag_configure("currently_playing", background="#E0FFE0")  # Softer green
        
        # Add alternating row colors for better readability
        self.tag_configure("even_row", background="#F9F9F9")
        self.tag_configure("odd_row", background="#FFFFFF")
        
        # Add some internal padding to cells for better text spacing
        style = ttk.Style()
        style.configure("Treeview", padding=5)

        # Create tooltip for path column
        self.tooltip = Tooltip(self)
        
        # Bind events for showing/hiding tooltip
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", lambda event: self.tooltip.hide_tip())

        # Initialize scheduled tooltip attribute
        self.scheduled_tooltip = None
        self.hover_item = None
        self.hover_column = None
        self.hover_x = 0
        self.hover_y = 0
        
        self.bind("<Button-1>", self.callbacks["button_down"])
        self.bind("<B1-Motion>", self.callbacks["dragged"])
        self.bind("<ButtonRelease-1>", self.callbacks["button_up"])
        self.bind("<Double-1>", self.callbacks["double_click"])
        
    def show_delayed_tooltip(self):
        """Show the tooltip after delay has passed"""
        if self.hover_item and self.hover_column:
            values = self.item(self.hover_item, 'values')
            if len(values) > 6 and values[6]:  # Make sure path exists
                # Show tooltip with full path
                self.tooltip.show_tip(values[6], self.hover_x, self.hover_y)
    
    def on_motion(self, event):
        """Show tooltip when hovering over the path column after a delay"""
        # Cancel any existing scheduled tooltip
        if hasattr(self, 'scheduled_tooltip') and self.scheduled_tooltip:
            self.after_cancel(self.scheduled_tooltip)
            self.scheduled_tooltip = None
        
        # Hide any existing tooltip
        self.tooltip.hide_tip()
        
        # Get the item and column under cursor
        item = self.identify_row(event.y)
        column = self.identify_column(event.x)
        
        if not item or not column:
            return
            
        # Get column index (columns are numbered #1, #2, etc.)
        column_idx = int(column[1:]) - 1
        
        # Check if hovering over the Path column (index 6)
        if column_idx == 6:  # Path is the 7th column (index 6)
            # Get the path value from the item
            values = self.item(item, 'values')
            if len(values) > 6 and values[6]:  # Make sure path exists
                # Store current position and path for delayed tooltip
                self.hover_item = item
                self.hover_column = column
                self.hover_x = event.x_root
                self.hover_y = event.y_root
                
                # Schedule tooltip to appear after 500ms (half second)
                self.scheduled_tooltip = self.after(500, self.show_delayed_tooltip)


class SearchFrame(Frame):
    def __init__(self, parent, search_callback, close_callback, next_callback=None, prev_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.search_callback = search_callback
        self.close_callback = close_callback
        self.next_callback = next_callback
        self.prev_callback = prev_callback
        
        # Create a frame with a search field and buttons
        self.search_var = StringVar()
        self.search_var.trace_add("write", lambda name, index, mode: self.search_callback(self.search_var.get()))
        
        # Label
        Label(self, text="Search:", font=DEFAULT_FONT).pack(side="left", padx=(5, 0))
        
        # Search entry - fixed width of 250 pixels
        self.search_entry = Entry(self, textvariable=self.search_var, width=30, font=DEFAULT_FONT)
        self.search_entry.pack(side="left", padx=5, pady=5)
        # Set the width to 250 pixels
        self.search_entry.config(width=25)  # Approximately 250 pixels with default font
        self.search_entry.focus_set()
        
        # Previous button - smaller size
        if prev_callback:
            prev_button = ttk.Button(self, text="↑", width=1, command=prev_callback)
            prev_button.pack(side="left", padx=1)
        
        # Next button - smaller size
        if next_callback:
            next_button = ttk.Button(self, text="↓", width=1, command=next_callback)
            next_button.pack(side="left", padx=1)
        
        # Close button - smaller size
        close_button = ttk.Button(self, text="×", width=1, command=self.close_callback)
        close_button.pack(side="left", padx=1)
        
        # Bind keys
        self.search_entry.bind("<Escape>", lambda event: self.close_callback())
        self.search_entry.bind("<Return>", lambda event: self.next_callback() if self.next_callback else None)
        self.search_entry.bind("<Shift-Return>", lambda event: self.prev_callback() if self.prev_callback else None)
        self.search_entry.bind("<F3>", lambda event: self.next_callback() if self.next_callback else None)
        self.search_entry.bind("<Shift-F3>", lambda event: self.prev_callback() if self.prev_callback else None)
        
    def get_search_text(self):
        return self.search_var.get()