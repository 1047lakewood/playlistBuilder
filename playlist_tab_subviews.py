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
        self.context_menu.add_command(label="Search with Everything", command=self.parent.controller.search_with_everything)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Rename File Path", command=self.parent.controller.controller_actions.rename_track_file_path_dialog)
        self.context_menu.add_command(label="Rename by Browsing", command=self.parent.controller.controller_actions.rename_track_by_browsing_dialog)
        self.context_menu.add_command(label="Replace from Macro Output", command=self.parent.controller.controller_actions.replace_from_macro_output_action)
        self.context_menu.add_command(label="Add AM to Filename", command=self.parent.controller.controller_actions.add_am_to_filename_action)
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
        self.scheduled_id = None

    def show_tip(self, text, x, y):
        """Display text in a tooltip window"""
        if self.tip_window or not text:
            return

        # Create tooltip window
        self.tip_window = Toplevel(self.parent)
        self.tip_window.withdraw()
        self.tip_window.overrideredirect(True)  # Remove window decorations
        self.tip_window.attributes('-topmost', True)

        # Create frame for better visual appearance
        frame = Frame(self.tip_window, background='#2D2D2D', padx=1, pady=1)
        frame.pack(fill='both', expand=True)

        # Create label with tooltip text - dark theme for contrast
        label = Label(frame, text=text, justify='left',
                      background='#2D2D2D', foreground='#FFFFFF',
                      font=("Consolas", 9), padx=8, pady=4)
        label.pack()

        # Position tooltip to the left and below cursor
        self.tip_window.geometry(f"+{x-400}+{y+18}")
        self.tip_window.deiconify()

    def hide_tip(self):
        """Hide the tooltip and cancel any scheduled show"""
        if self.scheduled_id:
            try:
                self.parent.after_cancel(self.scheduled_id)
            except Exception:
                pass
            self.scheduled_id = None
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
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
        
        # Configure tags for row styling using theme colors
        self.refresh_theme_colors()
        
    def refresh_theme_colors(self):
        """Refresh treeview tag colors - using hardcoded defaults."""
        self.tag_configure("missing_file", foreground="#FF3B30")
        self.tag_configure("search_match", background="#E8F0FE")
        self.tag_configure("search_current", background="#BBDEFB")
        self.tag_configure("currently_playing", background="#E0FFE0")
        
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
        self.bind("<Leave>", self._on_leave)

        # Initialize hover tracking
        self.hover_item = None
        self.hover_column = None
        self.hover_x = 0
        self.hover_y = 0

        self.bind("<Button-1>", self._on_button_down)
        self.bind("<B1-Motion>", self._on_dragged)
        self.bind("<ButtonRelease-1>", self._on_button_up)
        self.bind("<Double-1>", self.callbacks["double_click"])

    def _on_leave(self, event):
        """Handle mouse leaving the treeview - hide tooltip."""
        self.tooltip.hide_tip()
        self.hover_item = None
        self.hover_column = None

    def _on_button_down(self, event):
        """Handle button down - mark interaction and forward to callback."""
        self.tooltip.hide_tip()  # Hide tooltip on click
        if "on_interaction" in self.callbacks:
            self.callbacks["on_interaction"](event)
        self.callbacks["button_down"](event)

    def _on_dragged(self, event):
        """Handle drag - mark interaction and forward to callback."""
        if "on_interaction" in self.callbacks:
            self.callbacks["on_interaction"](event)
        self.callbacks["dragged"](event)

    def _on_button_up(self, event):
        """Handle button up - forward to callback."""
        self.callbacks["button_up"](event)
        
    def show_delayed_tooltip(self):
        """Show the tooltip after delay has passed"""
        self.tooltip.scheduled_id = None  # Clear the scheduled id
        if self.hover_item and self.hover_column:
            try:
                values = self.item(self.hover_item, 'values')
                if len(values) > 6 and values[6]:  # Make sure path exists
                    self.tooltip.show_tip(values[6], self.hover_x, self.hover_y)
            except Exception:
                pass  # Item may no longer exist

    def on_motion(self, event):
        """Show tooltip when hovering over the path column after a delay"""
        # Hide any existing tooltip and cancel scheduled
        self.tooltip.hide_tip()

        # Get the item and column under cursor
        item = self.identify_row(event.y)
        column = self.identify_column(event.x)

        if not item or not column:
            self.hover_item = None
            self.hover_column = None
            return

        # Get column index (columns are numbered #1, #2, etc.)
        try:
            column_idx = int(column[1:]) - 1
        except (ValueError, IndexError):
            return

        # Check if hovering over the Path column (index 6)
        if column_idx == 6:  # Path is the 7th column (index 6)
            values = self.item(item, 'values')
            if len(values) > 6 and values[6]:  # Make sure path exists
                # Store current position for delayed tooltip
                self.hover_item = item
                self.hover_column = column
                self.hover_x = event.x_root
                self.hover_y = event.y_root

                # Schedule tooltip to appear after 400ms
                self.tooltip.scheduled_id = self.after(400, self.show_delayed_tooltip)
        else:
            self.hover_item = None
            self.hover_column = None


class SearchFrame(Frame):
    def __init__(self, parent, search_callback, close_callback, next_callback=None, prev_callback=None):
        super().__init__(parent, bg="#F0F0F0", relief="ridge", borderwidth=2)
        self.parent = parent
        self.search_callback = search_callback
        self.close_callback = close_callback
        self.next_callback = next_callback
        self.prev_callback = prev_callback
        
        # Create a frame with a search field and buttons
        self.search_var = StringVar()
        self.number_var = StringVar()
        
        # Flag to prevent recursion when clearing fields
        self._clearing_field = False
        
        def update_search(*args):
            if not self._clearing_field:
                self.search_callback(self.search_var.get(), self.number_var.get())
        
        def on_search_change(*args):
            if self._clearing_field:
                return
            # Clear number search when regular search changes (only if typing, not deleting)
            search_value = self.search_var.get()
            if search_value:
                self._clearing_field = True
                self.number_var.set("")
                self._clearing_field = False
            update_search()
        
        def on_number_change(*args):
            if self._clearing_field:
                return
            # Clear regular search when number search changes (only if typing, not deleting)
            number_value = self.number_var.get()
            if number_value:
                self._clearing_field = True
                self.search_var.set("")
                self._clearing_field = False
            update_search()
        
        self.search_var.trace_add("write", on_search_change)
        self.number_var.trace_add("write", on_number_change)
        
        # Add padding around the entire frame
        bg_color = "#F0F0F0"
        fg_color = "#505050"
        entry_bg = "#FFFFFF"
        entry_highlight = "#0078D7"
        entry_border = "#E0E0E0"
        
        inner_frame = Frame(self, bg=bg_color)
        inner_frame.pack(fill="both", expand=True, padx=10, pady=8)
        
        # Number search label (bigger font)
        number_label = Label(
            inner_frame, 
            text="#", 
            font=("Segoe UI", 15, "normal"), 
            bg=bg_color,
            fg=fg_color
        )
        number_label.pack(side="left", padx=(0, 4))
        
        # Number search entry with modern styling (smaller width)
        self.number_entry = Entry(
            inner_frame, 
            textvariable=self.number_var, 
            width=8, 
            font=("Segoe UI", 11),
            relief="flat",
            borderwidth=0,
            highlightthickness=2,
            highlightbackground=entry_border,
            highlightcolor=entry_highlight,
            bg=entry_bg,
            insertbackground=entry_highlight
        )
        self.number_entry.pack(side="left", padx=(0, 8), ipady=5)
        
        # Search label with modern styling (moved after number field)
        search_icon = Label(
            inner_frame, 
            text="Search", 
            font=("Segoe UI", 13, "normal"), 
            bg=bg_color,
            fg=fg_color
        )
        search_icon.pack(side="left", padx=(0, 8))
        
        # Search entry with modern styling
        self.search_entry = Entry(
            inner_frame, 
            textvariable=self.search_var, 
            width=35, 
            font=("Segoe UI", 11),
            relief="flat",
            borderwidth=0,
            highlightthickness=2,
            highlightbackground=entry_border,
            highlightcolor=entry_highlight,
            bg=entry_bg,
            insertbackground=entry_highlight
        )
        self.search_entry.pack(side="left", padx=5, ipady=5)
        self.search_entry.focus_set()
        
        # Button style configuration
        style = ttk.Style()
        style.configure("Search.TButton", padding=5)
        
        # Previous button with better icon and styling
        if prev_callback:
            prev_button = ttk.Button(
                inner_frame, 
                text="△", 
                width=3, 
                style="Search.TButton",
                command=prev_callback
            )
            prev_button.pack(side="left", padx=2)
        
        # Next button with better icon and styling
        if next_callback:
            next_button = ttk.Button(
                inner_frame, 
                text="▽", 
                width=3,
                style="Search.TButton",
                command=next_callback
            )
            next_button.pack(side="left", padx=2)
        
        # Close button with better icon and styling
        close_button = ttk.Button(
            inner_frame, 
            text="✕", 
            width=3,
            style="Search.TButton",
            command=self.close_callback
        )
        close_button.pack(side="left", padx=(8, 0))
        
        # Bind keys
        self.search_entry.bind("<Escape>", lambda event: self.close_callback())
        self.search_entry.bind("<Return>", lambda event: self.next_callback() if self.next_callback else None)
        self.search_entry.bind("<Shift-Return>", lambda event: self.prev_callback() if self.prev_callback else None)
        self.search_entry.bind("<F3>", lambda event: self.next_callback() if self.next_callback else None)
        self.search_entry.bind("<Shift-F3>", lambda event: self.prev_callback() if self.prev_callback else None)
        
    def get_search_text(self):
        return self.search_var.get()
    
    def get_search_number(self):
        return self.number_var.get()