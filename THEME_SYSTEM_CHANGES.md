# Theme System Implementation

## Overview
The color settings system has been completely reimplemented to use a theme-based architecture with predefined color palettes and optional per-color overrides.

## Key Changes

### 1. New Theme Manager (`theme_manager.py`)
- Centralized theme management with 5 built-in themes:
  - **Light** (default) - Clean light theme
  - **Dark** - Dark theme for reduced eye strain
  - **Blue** - Cool blue tones
  - **Warm** - Warm orange/tan tones
  - **High Contrast** - Black and white for accessibility
  
- Features:
  - Theme selection with automatic color loading
  - Per-color override system for customization
  - Callback system for notifying widgets of theme changes
  - Automatic migration from old color config format
  - 24 customizable color keys covering all UI elements

### 2. Updated Settings Dialog (`settings_dialog.py`)
The Colors tab has been completely redesigned:
- **Theme Selection Section**:
  - Dropdown to select from 5 predefined themes
  - Preview button to see changes before saving
  - Descriptive help text
  
- **Color Overrides Section**:
  - Scrollable list of all 24 color properties
  - Each row has:
    - Label with descriptive name
    - Text entry for hex color code
    - Color preview square
    - Color picker button (...)
    - Reset button (↺) to revert to theme default
  - Organized by category (Notebook/Tabs, Treeview, Search, etc.)

### 3. Font Configuration Updates (`font_config.py`)
- Now imports and uses `theme_manager` for all color values
- Replaced hardcoded colors with `theme_manager.get_color()` calls
- Automatically reloads theme when styles are reconfigured

### 4. Widget Updates
All widgets that previously hardcoded colors now use theme colors:

#### `playlist_tab_subviews.py`
- Treeview row colors (even/odd, missing, search highlights, playing track)
- Search frame colors (background, foreground, entry fields)
- Added `refresh_theme_colors()` method to update colors dynamically

#### `container_view.py`
- Currently playing bar (background, foreground, hover state)

#### `prelisten_view.py`
- Prelisten view background
- Control frame background

### 5. Application Initialization (`main.py`)
- Added theme manager initialization at startup
- Themes are loaded before configuring TTK styles

## Color Keys Available

### Notebook/Tabs
- `notebook_bg` - Background of the notebook widget
- `tab_bg` - Background of inactive tabs
- `tab_fg` - Text color of inactive tabs
- `selected_tab_bg` - Background of selected tab
- `selected_tab_fg` - Text color of selected tab
- `active_tab_bg` - Background of active (hover) tab
- `active_tab_fg` - Text color of active (hover) tab

### Treeview
- `treeview_even` - Even row background
- `treeview_odd` - Odd row background
- `treeview_missing` - Color for missing files
- `treeview_search_match` - Background for search matches
- `treeview_search_current` - Background for current search result
- `treeview_playing` - Background for currently playing track

### Search Frame
- `search_frame_bg` - Search frame background
- `search_frame_fg` - Search frame text color
- `search_entry_bg` - Search entry background
- `search_entry_highlight` - Search entry highlight/cursor color
- `search_entry_border` - Search entry border color

### Prelisten
- `prelisten_bg` - Prelisten view background
- `prelisten_control_bg` - Prelisten control bar background

### Currently Playing
- `currently_playing_bg` - Currently playing bar background
- `currently_playing_fg` - Currently playing bar text color
- `currently_playing_hover` - Currently playing bar hover text color

## Migration

### Automatic Migration
The system automatically migrates old `config.json` files:
- Old format with `"colors": {...}` section
- Converted to new `"theme": {"name": "Light", "overrides": {...}}` format
- Preserves existing color customizations as overrides on Light theme

### Manual Migration
Users can also:
1. Open Settings → Colors
2. Select a new theme from the dropdown
3. Click "Preview" to see changes
4. Click "Apply" or "OK" to save

## Developer Usage

### Getting Colors in New Code
```python
import theme_manager

# Get a color with fallback default
bg_color = theme_manager.get_color("notebook_bg", "#f5f5f5")
```

### Adding New Color Keys
1. Add to all theme dictionaries in `theme_manager.py` (THEMES dict)
2. Add to color_settings list in `settings_dialog.py` `_build_colors_editor()`
3. Use in widgets via `theme_manager.get_color()`

### Refreshing Colors on Theme Change
```python
# Option 1: Register a callback
theme_manager.register_theme_change_callback(my_refresh_function)

# Option 2: Call from settings dialog's on_apply callback
# (already wired up in main controller)
```

## Testing
- Theme manager tested with automated test script
- All 5 themes load correctly
- Migration from old format works
- Color overrides persist correctly
- Preview functionality works in settings dialog
- Dynamic color refresh confirmed working (colors update immediately on Apply/OK)

## How Color Refresh Works
When the user clicks Apply or OK in the Settings dialog:
1. Settings are saved to `config.json`
2. Theme manager reloads the theme
3. `font_config.configure_ttk_styles()` updates all ttk widget styles
4. Controller's `refresh_theme_colors()` method is called
5. This method recursively calls `refresh_theme_colors()` on:
   - ContainerView (currently playing bar)
   - PlaylistNotebookView (which calls it on all tabs)
   - Each PlaylistTabView (which calls it on treeviews)
   - PrelistenView (if active)
6. SearchFrames get new colors automatically when recreated

## Files Modified
1. `theme_manager.py` (new file) - Core theme management system
2. `settings_dialog.py` (major refactor of Colors tab) - New theme UI
3. `font_config.py` (use theme colors) - TTK styles from theme
4. `main.py` (initialize theme manager) - App startup
5. `playlist_tab_subviews.py` (use theme colors + refresh method) - Treeview colors
6. `container_view.py` (use theme colors + refresh method) - Currently playing bar
7. `prelisten_view.py` (use theme colors + refresh method) - Prelisten colors
8. `playlist_notebook_view.py` (added refresh method) - Propagates refresh to tabs
9. `playlist_tab.py` (added refresh method) - Tab-level refresh
10. `playlist_builder_controller.py` (added refresh callback) - Coordinates refresh

## Benefits
- Consistent theming across all UI elements
- Easy switching between complete color schemes
- Fine-grained customization still available via overrides
- Automatic migration from old config format
- Better accessibility with High Contrast theme
- Reduced eye strain with Dark theme
- Cleaner code with centralized color management

