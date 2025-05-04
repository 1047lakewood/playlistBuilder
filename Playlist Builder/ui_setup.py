import logging
import tkinter as tk
import tkinter.font as tkfont
import tkinter.ttk as ttk

def setup_menu_bar(app):
    logging.info("setup_menu_bar called. Stub implementation.")
    # TODO: Implement menu setup logic
    # --- Restore Menu Bar (after font/theme setup to ensure it appears) ---
    app.main_menu = tk.Menu(app.master)
    app.master.config(menu=app.main_menu)

    # File Menu
    app.file_menu = tk.Menu(app.main_menu, tearoff=0)
    app.main_menu.add_cascade(label="File", menu=app.file_menu)
    app.file_menu.add_command(label="New Playlist Tab", command=app.add_new_tab)
    app.file_menu.add_command(label="Open Playlist(s)...", command=app.open_playlists)
    app.file_menu.add_separator()
    app.file_menu.add_command(label="Save Current Playlist", command=app.save_current_playlist)
    app.file_menu.add_command(label="Save Current Playlist As...", command=lambda: app.save_current_playlist(save_as=True))
    app.file_menu.add_separator()
    app.file_menu.add_command(label="Save Profile...", command=app.save_profile)
    app.load_profile_menu = tk.Menu(app.main_menu, tearoff=0)  # Dynamic menu
    app.file_menu.add_cascade(label="Load Profile", menu=app.load_profile_menu)
    app.update_load_profile_menu()
    app.file_menu.add_separator()
    app.file_menu.add_command(label="Close Current Tab", command=app.close_current_tab)
    app.file_menu.add_separator()
    app.file_menu.add_command(label="Exit", command=app.quit_app)

    # Edit Menu
    app.edit_menu = tk.Menu(app.main_menu, tearoff=0)
    app.main_menu.add_cascade(label="Edit", menu=app.edit_menu)
    app.edit_menu.add_command(label="Copy Selected", command=app.copy_selected)
    app.edit_menu.add_command(label="Cut Selected", command=app.cut_selected)
    app.edit_menu.add_command(label="Paste Tracks", command=app.paste_tracks)
    app.edit_menu.add_separator()
    app.edit_menu.add_command(label="Remove Selected", command=app.remove_selected_from_current)

    # View Menu
    app.view_menu = tk.Menu(app.main_menu, tearoff=0)
    app.main_menu.add_cascade(label="View", menu=app.view_menu)
    app.view_menu.add_command(label="Customize Columns...", command=app.customize_columns)
    app.view_menu.add_command(label="Refresh Current Playlist View", command=app.refresh_current_tab_view)
    app.view_menu.add_separator()
    app.view_menu.add_command(label="Show Filter Bar", command=app.toggle_filter_bar)

    # Settings Menu
    app.settings_menu = tk.Menu(app.main_menu, tearoff=0)
    app.main_menu.add_cascade(label="Settings", menu=app.settings_menu)
    app.settings_menu.add_command(label="Change Artist Directory...", command=app.open_settings_dialog)
def setup_ui(app):
    # --- UI Elements ---
    # Set modern, slightly larger font for the app
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(size=12, family="Segoe UI")
    app.option_add("*Font", default_font)
    app.option_add("*TCombobox*Listbox.font", default_font)
    app.option_add("*Treeview*Font", default_font)
    # Use a separate font object for headings/tabs
    heading_font = default_font.copy()
    heading_font.configure(weight="bold")
    app.option_add("*Treeview*Heading.Font", heading_font)
    app.option_add("*Menu.Font", default_font)
    # Make the top bar menu font larger
    menu_font = default_font.copy()
    menu_font.configure(size=12, family="Segoe UI")
    app.option_add("*Menu.Font", menu_font)
    app.option_add("*Button.Font", default_font)
    app.option_add("*Label.Font", default_font)
    app.option_add("*Entry.Font", default_font)
    app.option_add("*TEntry.Font", default_font)
    app.option_add("*TNotebook.Tab.Font", heading_font)


    # Modern theme
    style = ttk.Style(app)
    style.theme_use("clam")
    # SMALL font/padding for normal (unselected) tabs
    normal_tab_font = heading_font.copy()
    normal_tab_font.configure(size=9)
    #make the tabs look smaller with less padding
    style.configure("TNotebook.Tab", padding=[5, 2], font=normal_tab_font, background="#e0e0eb", foreground="#222")

    # LARGE font/padding for SELECTED tab (should look like previous unselected tabs)
    selected_tab_font = heading_font.copy()
    selected_tab_font.configure(size=16, weight="bold")


    style.map("TNotebook.Tab",
                background=[("selected", "#f0f0f7"), ("!selected", "#e0e0eb")],
                foreground=[("selected", "#222"), ("!selected", "#222")],
                font=[("selected", selected_tab_font), ("!selected", normal_tab_font)])
    style.configure("TNotebook", background="#f0f0f7")
    style.configure("Treeview", rowheight=28, font=default_font, fieldbackground="#fff", background="#fff", height=22)
    style.configure("Treeview.Heading", font=heading_font, background="#e0e0eb", foreground="#222")
    style.configure("TLabel", font=default_font)
    style.configure("TButton", font=default_font)
    style.configure("TEntry", font=default_font)
    style.map("TButton", background=[("active", "#e0e0eb")])


    # --- Main Area ---
    app.notebook = ttk.Notebook(app)
    app.notebook.enable_traversal()
    app.notebook.bind("<ButtonPress-1>", app._on_tab_press)
    app.notebook.bind("<B1-Motion>", app._on_tab_drag)
    app.notebook.bind("<ButtonRelease-1>", app._on_tab_release)
    app._dragged_tab_index = None
    app._dragged_tab_id = None
    app.notebook.pack(expand=True, fill="both", side="top", padx=5, pady=5)
    app.notebook.bind("<<NotebookTabChanged>>", app.on_tab_change)
    app.notebook.bind("<Button-3>", app._on_tab_right_click_context)


    # --- Pre-listen Controls ---
    app.prelisten_frame = ttk.Frame(app)
    app.prelisten_frame.pack_forget() # Hide by default

    app.play_pause_button = ttk.Button(app.prelisten_frame, text="▶ Play", command=app.toggle_play_pause, width=8)
    app.play_pause_button.pack(side="left", padx=(0,5))
    app.stop_button = ttk.Button(app.prelisten_frame, text="■ Stop", command=app.stop_playback, width=8)
    app.stop_button.pack(side="left", padx=(0,5))

    # Song title label
    app.prelisten_label = ttk.Label(app.prelisten_frame, text="No track selected.", anchor="w", width=40)
    app.prelisten_label.pack(side="top", anchor="w", padx=5, pady=(0,2), fill="x")

    # Scrubber/progress bar (styled for a modern look, easier to drag)
    app.progress_var = tk.DoubleVar(value=0)
    app.progress_scale = ttk.Scale(app.prelisten_frame, from_=0, to=100, orient="horizontal", variable=app.progress_var, command=app.on_scrub, length=250)
    app.progress_scale.pack(side="top", fill="x", expand=True, padx=(5, 40), pady=(0,2))
    app.progress_scale.bind("<ButtonRelease-1>", app.on_scrub_release)
    app.progress_scale.configure(takefocus=True)

    # Volume slider (no label)
    app.volume_var = tk.DoubleVar(value=1.0)
    app.volume_scale = ttk.Scale(app.prelisten_frame, from_=0, to=1, orient="horizontal", variable=app.volume_var, command=app.on_volume_change, length=80)
    app.volume_scale.pack(side="left", padx=(5, 5), pady=(5,0))

    app.progress_label = ttk.Label(app.prelisten_frame, text="00:00 / 00:00", width=15, anchor='e')
    app.progress_label.pack(side="left", padx=5)

    # X button to hide player (moved to end)
    app.hide_player_button = ttk.Button(app.prelisten_frame, text="✖", width=3, command=app.hide_prelisten_player)
    app.hide_player_button.pack(side="right", padx=(5,5), pady=(0,0))
    app.hide_player_button.pack_forget()  # Hide by default

    # --- Status Bar ---
    app.status_var = tk.StringVar()
    app.status_bar = ttk.Label(app, textvariable=app.status_var, relief=tk.SUNKEN, anchor=tk.W)
    app.status_bar.pack(side="bottom", fill=tk.X)
    app.set_status("Ready.")
