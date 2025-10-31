# --- START OF FILE autoRDS.py ---

RDS_IP = "50.208.125.83"

import socket
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import logging.handlers # Keep handlers for rotation
import os
import sys

# --- Configuration ---
RDS_PORT = 10001
# RDS_IP = "not gonna tell you"
MESSAGE_JSON = "messages.json"
NOW_PLAYING_XML = r"G:\To_RDS\nowplaying.xml"
DEFAULT_MESSAGE = "732.901.7777 to SUPPORT and hear this program!"
LOG_FILE_NAME = "RDS_Send.log" # Log filename
LOG_MAX_BYTES = 10 * 1024 # 10 KB size limit
LOG_BACKUP_COUNT = 1 # <-- Set to 0 to overwrite instead of creating backups

# --- Set up logging ---
# Get the user's Desktop directory path
if os.name == 'nt': # Windows
    desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
elif os.name == 'posix': # macOS, Linux
    desktop_path = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
else:
    # Fallback to script directory
    desktop_path = os.path.dirname(os.path.abspath(__file__))

log_file_path = os.path.join(desktop_path, LOG_FILE_NAME)

# --- Configure Rotating File Logging ---
# Format: Only include the message itself for send/receive clarity
log_formatter = logging.Formatter('%(asctime)s - %(message)s')

# Create the rotating file handler
# With backupCount=0, it will overwrite the file when maxBytes is reached
rotate_handler = logging.handlers.RotatingFileHandler(
    log_file_path,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT, # Set to 0
    encoding='utf-8'
)
rotate_handler.setFormatter(log_formatter)

# Get the root logger and add ONLY the file handler
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove existing handlers
if logger.hasHandlers():
    logger.handlers.clear()

logger.addHandler(rotate_handler)

# --- Add StreamHandler to output logs to console (stderr) ---
console_handler = logging.StreamHandler(sys.stderr) # Use stderr for logs
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)
# --- End StreamHandler addition ---


# --- Functions (Keep previous versions - no logging inside these) ---
def load_messages():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    messages_path = os.path.join(script_dir, MESSAGE_JSON)
    try:
        with open(messages_path, "r") as file:
            return json.load(file)["Messages"]
    except Exception:
        return []

def load_now_playing():
    try:
        tree = ET.parse(NOW_PLAYING_XML)
        root = tree.getroot()
        current_track = root.find("TRACK")
        if current_track is not None:
            return {
                "artist": current_track.get("ARTIST", ""),
                "title": current_track.findtext("TITLE", ""),
            }
        else:
             return {"artist": "", "title": ""}
    except Exception:
        return {"artist": "", "title": ""}

def should_display_message(message, now_playing):
    if not message.get("Enabled", True): return False
    message_text = message.get("Text", "")
    artist_name = now_playing.get("artist", "")
    if "{artist}" in message_text and not artist_name: return False
    schedule_info = message.get("Scheduled", {})
    if schedule_info.get("Enabled", False):
        now = datetime.now()
        current_day_abbr = now.strftime("%a")
        current_hour = now.hour
        day_mapping = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday", "Sun": "Sunday"}
        full_day_name = day_mapping.get(current_day_abbr)
        scheduled_days = schedule_info.get("Days", [])
        if scheduled_days and full_day_name not in scheduled_days: return False
        scheduled_times = schedule_info.get("Times", [])
        if scheduled_times:
            hour_match = False
            for time_obj in scheduled_times:
                if isinstance(time_obj, dict) and "hour" in time_obj:
                     try:
                         if int(time_obj.get("hour")) == current_hour:
                             hour_match = True
                             break
                     except (ValueError, TypeError): continue
            if not hour_match: return False
    if "{title}" in message_text and not now_playing.get("title"): return False
    return True

def format_message_text(text, now_playing):
    artist = now_playing.get("artist", "")
    title = now_playing.get("title", "")
    replacements = {"{artist}": artist.upper() if artist else "", "{title}": title if title else ""}
    formatted_text = text
    for placeholder, value in replacements.items():
        formatted_text = formatted_text.replace(placeholder, value)
    return formatted_text

# --- send_command function (Logs SEND/RECV) ---
def send_command(command):
    response = f"Error: Not Sent"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((RDS_IP, RDS_PORT))
            logging.info(f"SEND: {command}") # Log send
            s.sendall((command + '\r\n').encode('utf-8'))
            response_bytes = s.recv(1024)
            response = response_bytes.decode('utf-8', errors='ignore').strip()
            logging.info(f"RECV: {response}") # Log receive
            return response
    except socket.timeout:
        response = "Error: Timeout"
        logging.error(f"SEND Error: Timeout for command: {command}")
        logging.info(f"RECV: {response}")
        return response
    except ConnectionRefusedError:
         response = "Error: Connection Refused"
         logging.error(f"SEND Error: Connection Refused for command: {command}")
         logging.info(f"RECV: {response}")
         return response
    except Exception as e:
        response = f"Error: {type(e).__name__}"
        logging.error(f"SEND Error: {e} for command: {command}")
        logging.info(f"RECV: {response}")
        return response

# --- send_message_to_rds function (Uses send_command) ---
def send_message_to_rds(text):
    sanitized_text = text.replace('\r', ' ').replace('\n', ' ')
    max_len = 64
    if len(sanitized_text) > max_len:
        sanitized_text = sanitized_text[:max_len]
    response = send_command(f"DPSTEXT={sanitized_text}")
    # No extra logging needed here, send_command handles it
    time.sleep(0.2)

# --- Main Loop ---
def main():
    message_index = 0
    last_message_time = 0
    current_message_duration = 10
    last_sent_text = None

    while True:
        try:
            current_time = time.time()
            messages = load_messages()
            now_playing = load_now_playing()
            valid_messages = [m for m in messages if should_display_message(m, now_playing)]

            display_text = None
            selected_duration = 10

            if not valid_messages:
                if current_time - last_message_time >= current_message_duration:
                    if last_sent_text != DEFAULT_MESSAGE:
                       display_text = DEFAULT_MESSAGE
                       selected_duration = 10
            else:
                if current_time - last_message_time >= current_message_duration:
                    current_valid_message = valid_messages[message_index % len(valid_messages)]
                    formatted_text = format_message_text(current_valid_message["Text"], now_playing)
                    if formatted_text != last_sent_text:
                        display_text = formatted_text
                        selected_duration = current_valid_message.get("Message Time", 10)
                        message_index = (message_index + 1) % len(valid_messages)
                    else:
                        last_message_time = current_time
                        current_message_duration = selected_duration

            if display_text is not None:
                send_message_to_rds(display_text) # Logging happens inside send_command
                last_sent_text = display_text
                last_message_time = current_time
                current_message_duration = selected_duration

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nExiting AutoRDS...")
            break
        except Exception as e:
            err_msg = f"FATAL ERROR in main loop: {e}"
            # Log exception to the file
            logging.exception(err_msg)
            # Also print basic error to console
            print(err_msg, file=sys.stderr)
            print("Attempting to continue after delay...", file=sys.stderr)
            time.sleep(15)

if __name__ == "__main__":
    main()

# --- END OF FILE autoRDS.py ---
