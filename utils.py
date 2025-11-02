def format_duration(seconds):
    if seconds is None or seconds == 0:
        return "--:--"
    
    # Convert seconds to float if it's a string
    try:
        seconds = float(seconds)
    except (ValueError, TypeError):
        return "--:--"  # Return placeholder if conversion fails
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    else:
        return f"{minutes}:{secs:02}"

def format_play_time(seconds, type="local"):
    if seconds is None or seconds < 0:
        return ""

    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    day_index = int((seconds // 86400) % 7)
    day = days[day_index]

    seconds %= 86400
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    am_pm = "AM" if hours < 12 else "PM"
    hour_12 = hours % 12 or 12  # show 12 instead of 0
    if hour_12 < 10:
        hour_12 = f"0{hour_12}"
    if type == "api_raw":
        return f"{hour_12}:{minutes:02}:{secs:02} {am_pm}"
    return f"{day} {hour_12}:{minutes:02}:{secs:02} {am_pm}"


def open_file_location(file_path):
    """
    Opens the location of a file in File Explorer.
    If the file doesn't exist, tries to open its parent directory.
    
    Args:
        file_path (str): Path to the file or directory to open
    """
    import os
    import subprocess
    
    if not file_path:
        return
        
    if os.path.exists(file_path):
        if os.path.isfile(file_path):
            # If it's a file, open its directory and select the file
            subprocess.run(["explorer", "/select,", os.path.normpath(file_path)])
        else:
            # If it's a directory, open it directly
            subprocess.run(["explorer", os.path.normpath(file_path)])
    else:
        # If the file doesn't exist, try to open its parent directory
        parent_dir = os.path.dirname(file_path)
        if os.path.exists(parent_dir):
            subprocess.run(["explorer", os.path.normpath(parent_dir)])