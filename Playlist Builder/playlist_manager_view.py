
import tkinter as tk
from tkinter import ttk
from utils import APP_NAME, DEFAULT_COLUMNS, format_duration
from playlist_tab import PlaylistTab
import logging
logger = logging.getLogger(__name__)    


# --- View ---
class PlaylistManagerView(tk.Frame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.master = master
        self.controller = controller
        
        if master:
            master.title(APP_NAME)
            master.geometry("1600x900") # Default size

        # UI elements - initialized by setup_ui
        self.notebook = None
        self.status_var = tk.StringVar()
        self.status_bar = None # Will be created by setup_ui
        
        # Prelisten player elements
        self.prelisten_frame = None
        self.play_pause_button = None
        self.stop_button = None
        self.progress_label = None
        self.prelisten_label = None
        self.hide_player_button = None
        self.progress_var = tk.DoubleVar()
        self.progress_scale = None
        self.volume_var = tk.DoubleVar(value=0.8)
        self.volume_scale = None
        
        self.load_profile_menu = None # For dynamic menu updates

        # Setup UI (creates widgets and assigns them to self)
        self.setup_menu_bar(controller) 
        self.setup_ui()

        # Protocol Handlers and Global Binds
        if master:
            self.master.protocol("WM_DELETE_WINDOW", self.controller.quit_app)
            # Ctrl+S is handled by menu accelerator and global binding in setup_menu_bar
            # If direct binding needed here:
            # self.master.bind_all('<Control-s>', self.controller._on_ctrl_s_global)
            # self.master.bind_all('<Control-S>', self.controller._on_ctrl_s_global)
        
        self.pack(side="top", fill="both", expand=True)


    def get_current_tab_widget(self) -> 'PlaylistTab | None':
        try:
            selected_tab_id = self.notebook.select()
            if selected_tab_id:
                widget = self.nametowidget(selected_tab_id)
                if isinstance(widget, PlaylistTab):
                    return widget
        except tk.TclError: # No tabs exist or selected
            pass
        return None

    def set_status(self, message):
        self.status_var.set(message)
        # print(message) # Optional: print to console for debugging

    def update_prelisten_display(self, track_data, is_playing_this_track=False):
        if track_data:
            title = track_data.get('title', 'N/A')
            artist = track_data.get('artist', 'Unknown Artist')
            duration_str = format_duration(track_data.get('duration'))
            self.prelisten_label.config(text=f"{artist} - {title}")
            if not is_playing_this_track: # Only reset progress if not already playing this track
                self.progress_label.config(text=f"00:00 / {duration_str}")
                self.progress_var.set(0)
        else:
            self.prelisten_label.config(text="No track selected.")
            self.progress_label.config(text="00:00 / 00:00")
            self.progress_var.set(0)
            
    def show_prelisten_player_frame(self):
        # Ensure prelisten_frame is part of the main_pane if not already
        # This logic is a bit tricky with PanedWindow add.
        # Assuming setup_ui creates it but it might be removed/re-added or just packed.
        # For simplicity, we use pack here. If using PanedWindow, ensure it's added correctly.
        if not self.prelisten_frame.winfo_ismapped():
            self.prelisten_frame.pack(fill="x", side="bottom", padx=5, pady=(0, 5), before=self.status_bar)
            # The hide button needs to be packed here if prelisten_frame is shown
            if self.hide_player_button: # Check if it exists
                 self.hide_player_button.pack(side="right", padx=(5,0), pady=(0,0), in_=self.prelisten_frame.winfo_children()[0]) # Pack inside first child (player_controls_frame)

    def hide_prelisten_player_frame(self):
        self.prelisten_frame.pack_forget()

    def update_play_pause_button(self, is_playing, is_paused):
        if is_playing and not is_paused:
            self.play_pause_button.config(text="❚❚ Pause")
        else:
            self.play_pause_button.config(text="▶ Play")

    def update_playback_progress_display(self, elapsed_time, total_duration):
        if total_duration > 0:
            self.progress_var.set(int((elapsed_time / total_duration) * 100))
            self.progress_label.config(text=f"{format_duration(elapsed_time)} / {format_duration(total_duration)}")
        else:
            self.progress_var.set(0)
            self.progress_label.config(text="00:00 / --:--")

    def add_tab_to_notebook(self, tab_widget, title):
        self.notebook.add(tab_widget, text=title)
        self.notebook.select(tab_widget)
        # tab_widget.update_tab_title() # PlaylistTab should manage its own title based on dirty state

    def remove_tab_from_notebook(self, tab_id_or_widget):
        self.notebook.forget(tab_id_or_widget)

    def get_all_tab_widgets(self):
        tabs = []
        if self.notebook:
            for tab_id in self.notebook.tabs():
                try:
                    widget = self.nametowidget(tab_id)
                    if isinstance(widget, PlaylistTab):
                        tabs.append(widget)
                except tk.TclError:
                    continue
        return tabs

    def update_column_settings_in_all_tabs(self, new_columns):
        logger.info(f"View: Applying column settings to all tabs: {new_columns}")
        for tab_widget in self.get_all_tab_widgets():
            tab_widget.update_columns(new_columns)
    
    def update_column_widths_in_all_tabs(self, new_widths):
        logger.info(f"View: Applying column widths to all tabs: {new_widths}")
        for tab_widget in self.get_all_tab_widgets():
            for col, width in new_widths.items():
                try:
                    tab_widget.tree.column(col, width=width)
                except Exception: # Column might not be visible
                    pass


    def update_dynamic_profile_menu(self, profiles_dict):
        self.load_profile_menu.delete(0, tk.END)
        if not profiles_dict:
            self.load_profile_menu.add_command(label="(No profiles saved)", state="disabled")
        else:
            for name in sorted(profiles_dict.keys()):
                # Use a lambda with default argument to capture current 'name'
                self.load_profile_menu.add_command(label=name, command=lambda n=name: self.controller.load_profile(n))
            self.load_profile_menu.add_separator()
            self.load_profile_menu.add_command(label="Delete Profile...", command=self.controller.delete_profile_via_dialog)

        
    # --- Integrated ui_setup functions ---
    def setup_menu_bar(self, controller):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Playlist", command=controller.add_new_tab_command, accelerator="Ctrl+N")
        self.master.bind_all("<Control-n>", lambda e: controller.add_new_tab_command())
        self.master.bind_all("<Control-N>", lambda e: controller.add_new_tab_command())

        file_menu.add_command(label="Open Playlist(s)...", command=controller.open_playlists, accelerator="Ctrl+O")
        self.master.bind_all("<Control-o>", lambda e: controller.open_playlists())
        self.master.bind_all("<Control-O>", lambda e: controller.open_playlists())
        
        file_menu.add_command(label="Save Playlist", command=controller.save_current_playlist, accelerator="Ctrl+S")
        # Ctrl+S is globally bound in View's __init__
        file_menu.add_command(label="Save Playlist As...", command=lambda: controller.save_current_playlist(save_as=True), accelerator="Ctrl+Shift+S")
        self.master.bind_all("<Control-Shift-s>", lambda e: controller.save_current_playlist(save_as=True))
        self.master.bind_all("<Control-Shift-S>", lambda e: controller.save_current_playlist(save_as=True))

        file_menu.add_command(label="Close Tab", command=controller.close_current_tab, accelerator="Ctrl+W")
        self.master.bind_all("<Control-w>", lambda e: controller.close_current_tab())
        self.master.bind_all("<Control-W>", lambda e: controller.close_current_tab())
        
        file_menu.add_separator()
        file_menu.add_command(label="Settings...", command=controller.open_settings_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=controller.quit_app)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Copy", command=controller.copy_selected, accelerator="Ctrl+C")
        edit_menu.add_command(label="Cut", command=controller.cut_selected, accelerator="Ctrl+X")
        edit_menu.add_command(label="Paste", command=controller.paste_tracks, accelerator="Ctrl+V")
        edit_menu.add_command(label="Remove Selected", command=controller.remove_selected_from_current, accelerator="Delete")
        edit_menu.add_separator()
        edit_menu.add_command(label="Customize Columns...", command=controller.customize_columns)
        edit_menu.add_command(label="Refresh View", command=controller.refresh_current_tab_view, accelerator="F5")
        self.master.bind_all("<F5>", lambda e: controller.refresh_current_tab_view())
        
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # View Menu (placeholder for now, can be expanded)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Filter Bar", command=controller.toggle_filter_bar_for_current_tab)
        # ... more view options ...
        menubar.add_cascade(label="View", menu=view_menu)

        # Profile Menu
        profile_menu = tk.Menu(menubar, tearoff=0)
        profile_menu.add_command(label="Save Current Profile...", command=controller.save_profile)
        self.load_profile_menu = tk.Menu(profile_menu, tearoff=0) # Store for dynamic updates
        profile_menu.add_cascade(label="Load Profile", menu=self.load_profile_menu)
        # Initial population of load_profile_menu happens in controller after model/settings load
        menubar.add_cascade(label="Profiles", menu=profile_menu)


    def setup_ui(self):
        view = self
        # Main layout: Notebook for tabs, then prelisten player, then status bar
        main_pane = ttk.PanedWindow(view, orient=tk.VERTICAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Notebook for playlist tabs
        view.notebook = ttk.Notebook(main_pane)
        view.notebook.enable_traversal() # For Ctrl+Tab, etc.
        view.notebook.bind("<<NotebookTabChanged>>", view.controller.on_tab_change)
        # Right-click context menu for tabs
        view.notebook.bind("<Button-3>", view.controller.on_tab_right_click_context)
        # Drag and drop for tabs
        view.notebook.bind("<ButtonPress-1>", view.controller.on_tab_press_for_drag)
        view.notebook.bind("<B1-Motion>", view.controller.on_tab_drag)
        view.notebook.bind("<ButtonRelease-1>", view.controller.on_tab_release_for_drag)

        main_pane.add(view.notebook, weight=10) # Give most space to notebook

        # --- Pre-listen Player Frame (initially hidden) ---
        view.prelisten_frame = ttk.Frame(main_pane, padding="5")
        # main_pane.add(view.prelisten_frame) # Added by controller when shown

        # Player controls
        player_controls_frame = ttk.Frame(view.prelisten_frame)
        player_controls_frame.pack(fill="x", expand=True)

        view.play_pause_button = ttk.Button(player_controls_frame, text="▶ Play", command=view.controller.toggle_play_pause)
        view.play_pause_button.pack(side="left", padx=(0,5))

        view.stop_button = ttk.Button(player_controls_frame, text="■ Stop", command=view.controller.stop_playback)
        view.stop_button.pack(side="left", padx=(0,10))

        view.prelisten_label = ttk.Label(player_controls_frame, text="No track selected.", width=40, anchor="w")
        view.prelisten_label.pack(side="left", fill="x", expand=False, padx=(0,10)) # Don't expand too much

        # Progress bar and label
        progress_frame = ttk.Frame(player_controls_frame)
        progress_frame.pack(side="left", fill="x", expand=True)

        view.progress_var = tk.DoubleVar() # For scale value (0-100)
        view.progress_scale = ttk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=view.progress_var, command=view.controller.on_scrub_progress)
        view.progress_scale.pack(side="left", fill="x", expand=True, padx=(0,5))
        view.progress_scale.bind("<ButtonRelease-1>", view.controller.on_scrub_release)

        view.progress_label = ttk.Label(progress_frame, text="00:00 / 00:00", width=12) # Fixed width for time
        view.progress_label.pack(side="left")

        # Volume control
        volume_frame = ttk.Frame(player_controls_frame)
        volume_frame.pack(side="left", padx=(10,0))
        ttk.Label(volume_frame, text="Vol:").pack(side="left")
        view.volume_var = tk.DoubleVar(value=0.8) # Default volume 80%
        view.volume_scale = ttk.Scale(volume_frame, from_=0, to=1, orient=tk.HORIZONTAL, variable=view.volume_var, command=view.controller.on_volume_change)
        view.volume_scale.set(view.controller.model.current_settings.get('volume', 0.8)) # Load saved volume
        view.volume_var.set(view.controller.model.current_settings.get('volume', 0.8))

        view.volume_scale.pack(side="left")


        # Hide player button (part of prelisten_frame, but packed separately for alignment)
        view.hide_player_button = ttk.Button(view.prelisten_frame, text="X", command=view.controller.hide_prelisten_player, width=3)
        # Packing is done in show_prelisten_player

        # Status Bar
        view.status_bar = ttk.Label(view, textvariable=view.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=2)
        view.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        view.status_var.set("Ready.")

