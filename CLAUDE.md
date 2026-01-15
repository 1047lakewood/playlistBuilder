# Playlist Builder

A Tkinter-based desktop application for managing playlists, including both local M3U files and remote API-based playlists from radio stations.

## Project Structure

```
playlistBuilder/
├── main.py                      # Application entry point
├── playlist_builder_controller.py  # Main controller (MVC pattern)
├── controller_actions.py        # Business logic actions
├── tree_interaction_controller.py  # TreeView drag/drop/selection handling
├── playlist_tab.py              # PlaylistTabView - individual playlist tab UI
├── playlist_tab_subviews.py     # TreeView, context menu, search frame
├── playlist_notebook_view.py    # Notebook container for tabs
├── container_view.py            # Main container with "Currently Playing" bar
├── menu_bar.py                  # Application menu bar
├── settings_dialog.py           # Settings UI
├── models/
│   ├── playlist.py              # Playlist model (LOCAL or API type)
│   └── track.py                 # Track model
├── PlaylistService/
│   ├── playlist_service.py      # High-level playlist operations
│   ├── playlist_store.py        # Playlist storage management
│   ├── playlist_diff.py         # Diff algorithm for incremental updates
│   └── api_playlist_manager.py  # Remote playlist API handling
├── config.json                  # User configuration
└── settings.json                # Profile/session persistence
```

## Architecture

- **MVC Pattern**: Models hold data, Views display UI, Controller coordinates
- **No reactive binding**: UI updates are explicit via `reload_rows()` or `apply_diff()`
- **Dual playlist support**: Local M3U files and remote API playlists
- **Thread safety**: Background operations use `after()` to marshal to main thread

## Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `PlaylistBuilderController` | `playlist_builder_controller.py` | Main controller |
| `ControllerActions` | `controller_actions.py` | Menu/keyboard action handlers |
| `PlaylistTabView` | `playlist_tab.py` | Individual playlist tab |
| `ApiPlaylistManager` | `api_playlist_manager.py` | Single remote source connection |
| `RemotePlaylistRegistry` | `api_playlist_manager.py` | Manages all remote sources |
| `PlaylistDiff` | `playlist_diff.py` | Computes minimal changes between playlists |

## Remote Playlist Auto-Reload

Remote playlists can auto-refresh from the server:
- Background thread polls server at configurable interval
- `PlaylistDiff` computes minimal changes (insert/delete/update)
- UI updates incrementally without full rebuild
- Selection, scroll position, and currently-playing highlight are preserved
- Updates are deferred if user is actively interacting (clicking/dragging)

Configuration in Settings → Remote Sources → Auto-Reload Settings.

## Common Commands

```bash
# Run the application
python main.py

# Test imports
python -c "from playlist_builder_controller import PlaylistBuilderController"
```

## Claude Commands

When the user says:

### "update"
1. Increment the patch version in `playlist_builder_controller.py` in `show_about_dialog()` (line ~379: `Label(about_window, text="Version X.Y.Z")`)
2. Commit all staged/unstaged changes with a descriptive message summarizing the changes

### "deploy"
1. **Import config files** from stable/deployment directory to active/dev directory (sync config from deployed version)
2. **Run full deployment** to copy updated code to deployment directory
3. Deployment path is in `config.json` at `paths.deployment_dir`
4. Equivalent to: Settings → Migration → Import Config Files, then Full Deployment

## Configuration

`config.json` contains:
- `fonts`: Font family and size
- `treeview`: Row height settings
- `paths`: Playlists directory, intros directory
- `network.remote_sources`: Remote station configurations
- `network.auto_reload`: Auto-reload settings (enabled, interval_seconds)

## Notes

- Uses `tkinterdnd2` for drag-and-drop file support
- Uses `pygame` for audio preview functionality
- Remote API expects XML responses with `<Playlist><TRACK .../></Playlist>` format
