import logging
from datetime import datetime
import re
import subprocess
import platform
from typing import List, Optional

def parse_time_string(time_str: str):
    """Parse a comma separated string of hours and hour ranges.

    Args:
        time_str: String like ``"9, 13-15, 20"``.

    Returns:
        List of dicts in the form ``{"hour": int}`` sorted by hour.
    """
    times_list = []
    if not time_str:
        return times_list

    for part in time_str.split(','):
        part = part.strip()
        if not part:
            continue

        range_match = re.match(r'^(\d{1,2})-(\d{1,2})$', part)
        if range_match:
            try:
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                if 0 <= start <= 23 and 0 <= end <= 23 and start <= end:
                    for hour in range(start, end + 1):
                        time_obj = {"hour": hour}
                        if time_obj not in times_list:
                            times_list.append(time_obj)
                else:
                    logging.warning(f"Invalid hour range: {part}")
            except ValueError:
                logging.warning(f"Invalid number in range: {part}")
        else:
            try:
                hour = int(part)
                if 0 <= hour <= 23:
                    time_obj = {"hour": hour}
                    if time_obj not in times_list:
                        times_list.append(time_obj)
                else:
                    logging.warning(f"Invalid hour: {part}")
            except ValueError:
                logging.warning(f"Invalid time format: {part}")

    times_list.sort(key=lambda x: x['hour'])
    return times_list

# Example utility function (though logging handles formatting now)
# def format_timestamp(dt_object=None):
#     """Formats a datetime object into the desired string format."""
#     if dt_object is None:
#         dt_object = datetime.now()
#     try:
#         # Format: Jan 05 2025 03:45:48 PM
#         return dt_object.strftime('%b %d %Y %I:%M:%S %p')
#     except Exception as e:
#         logging.error(f"Error formatting timestamp: {e}")
#         return str(dt_object) # Fallback to default string representation

# Add other potential utility functions here if needed later.
# For example, functions to validate input, parse specific data formats, etc.

def configure_hidden_subprocess():
    """Configure subprocess.Popen to hide windows on Windows.

    On Windows, monkey-patch subprocess.Popen to add hidden-window flags
    unless the caller already provided startupinfo or creationflags.
    This ensures all subprocess calls (including pydub/ffmpeg) don't flash CMD windows.
    """
    if platform.system() != "Windows":
        return

    try:
        original_popen = subprocess.Popen

        class HiddenPopen(original_popen):
            def __init__(self, *args, **kwargs):
                # Only add hidden-window flags if not already provided by caller
                if 'startupinfo' not in kwargs:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    kwargs['startupinfo'] = startupinfo

                if 'creationflags' not in kwargs:
                    kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

                super().__init__(*args, **kwargs)

        # Replace subprocess.Popen with our hidden version
        subprocess.Popen = HiddenPopen

    except Exception as e:
        logging.warning(f"Failed to configure hidden subprocess: {e}")


def run_hidden(cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a command with hidden window and discarded output.

    Wrapper around subprocess.run that:
    - Uses creationflags to hide window on Windows
    - Discards stdout/stderr to DEVNULL
    - Uses shell=False for security

    Args:
        cmd: Command as list of strings
        cwd: Optional working directory

    Returns:
        CompletedProcess instance
    """
    kwargs = {
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
        'shell': False,
        'check': False,
    }

    if platform.system() == "Windows":
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    if cwd:
        kwargs['cwd'] = cwd

    return subprocess.run(cmd, **kwargs)


if __name__ == "__main__":
    print("This is a utility module, not meant to be run directly.")
    # now = datetime.now()
    # print(f"Current time formatted: {format_timestamp(now)}")
