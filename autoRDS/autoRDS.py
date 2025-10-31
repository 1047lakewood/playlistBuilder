# --- START OF FILE autoRDS.py ---

RDS_IP = "50.208.125.83"

import socket
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
# import logging.handlers # No longer needed
import os
import sys

# --- Configuration ---
RDS_PORT = 10001
# RDS_IP = "not gonna tell you" # Keep your original IP if needed
MESSAGE_JSON = "messages.json"
NOW_PLAYING_XML = r"G:\To_RDS\nowplaying.xml"
DEFAULT_MESSAGE = "732.901.7777 to SUPPORT and hear this program!"

# --- Artist Filtering Configuration ---
# Add artist names EXACTLY as they appear in the XML (case-insensitive match)
# Use sets for efficient lookups.
ARTIST_WHITELIST = {"REO Speedwagon", "Radiohead"} # Artists to allow even if not starting with 'R'
ARTIST_BLACKLIST = {"Rihanna", "Rick Astley"}      # Artists to block even if starting with 'R' or whitelisted

# --- Set up Console Logging ---
# Format: Simple format showing timestamp and message (focused on SEND/RECV)
log_formatter = logging.Formatter('%(asctime)s - %(message)s') # Simplified format

# Get the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO) # Keep INFO level for SEND/RECV

# Remove existing handlers (if any, good practice)
if logger.hasHandlers():
    logger.handlers.clear()

# Add StreamHandler to output logs to console (stderr)
console_handler = logging.StreamHandler(sys.stderr) # Use stderr for logs
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)
# --- End Logging Setup ---


# --- Functions ---
def load_messages():
    """Loads messages from the JSON configuration file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    messages_path = os.path.join(script_dir, MESSAGE_JSON)
    try:
        with open(messages_path, "r", encoding='utf-8') as file:
            return json.load(file)["Messages"]
    except FileNotFoundError:
        # Log critical errors only if needed, but user wants minimal logging
        # print(f"Error: Message file not found at {messages_path}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        # print(f"Error: Could not decode JSON from {messages_path}", file=sys.stderr)
        return []
    except Exception as e:
        # print(f"Error loading messages: {e}", file=sys.stderr)
        return []

def load_now_playing():
    """Loads now playing information from the XML file."""
    try:
        if not os.path.exists(NOW_PLAYING_XML):
             # print(f"Warning: Now playing XML not found: {NOW_PLAYING_XML}", file=sys.stderr)
             return {"artist": "", "title": ""}

        tree = ET.parse(NOW_PLAYING_XML)
        root = tree.getroot()
        current_track = root.find("TRACK")
        if current_track is not None:
            artist = current_track.get("ARTIST", "").strip()
            title = current_track.findtext("TITLE", "").strip()
            return {"artist": artist, "title": title}
        else:
             return {"artist": "", "title": ""}
    except ET.ParseError:
        # print(f"Error parsing XML file: {NOW_PLAYING_XML}", file=sys.stderr)
        return {"artist": "", "title": ""}
    except Exception as e:
        # print(f"Error loading now playing data: {e}", file=sys.stderr)
        return {"artist": "", "title": ""}

def should_display_message(message, now_playing):
    """
    Determines if a message should be displayed based on Enabled status,
    Artist filtering (R rule, Whitelist, Blacklist), Placeholders, and Schedule.
    (Internal logic, no logging)
    """
    if not message.get("Enabled", True):
        return False

    message_text = message.get("Text", "")
    artist_name = now_playing.get("artist", "")
    artist_name_upper = artist_name.upper()

    # Artist Filtering Logic
    if artist_name:
        if artist_name_upper in {name.upper() for name in ARTIST_BLACKLIST}:
            return False # Blacklisted

        is_whitelisted = artist_name_upper in {name.upper() for name in ARTIST_WHITELIST}
        if not is_whitelisted:
            if not artist_name_upper.startswith('R'):
                return False # Fails 'R' rule and not whitelisted

    # Placeholder Checks
    if "{artist}" in message_text and not artist_name:
        return False
    if "{title}" in message_text and not now_playing.get("title"):
        return False

    # Scheduling Checks
    schedule_info = message.get("Scheduled", {})
    if schedule_info.get("Enabled", False):
        now = datetime.now()
        current_day_abbr = now.strftime("%a")
        current_hour = now.hour
        day_mapping = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
                       "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday",
                       "Sun": "Sunday"}
        full_day_name = day_mapping.get(current_day_abbr)

        scheduled_days = schedule_info.get("Days", [])
        if scheduled_days and full_day_name not in scheduled_days:
            return False

        scheduled_times = schedule_info.get("Times", [])
        if scheduled_times:
            hour_match = False
            for time_obj in scheduled_times:
                if isinstance(time_obj, dict) and "hour" in time_obj:
                    try:
                        if int(time_obj.get("hour")) == current_hour:
                            hour_match = True
                            break
                    except (ValueError, TypeError):
                        continue
            if not hour_match:
                return False

    return True # Passed all checks

def format_message_text(text, now_playing):
    """Replaces placeholders in the message text. (No logging)"""
    artist = now_playing.get("artist", "")
    title = now_playing.get("title", "")
    replacements = {
        "{artist}": artist.upper() if artist else "",
        "{title}": title if title else ""
        }
    formatted_text = text
    for placeholder, value in replacements.items():
        formatted_text = formatted_text.replace(placeholder, value)
    return formatted_text.strip()

# --- send_command function (Logs ONLY SEND/RECV) ---
def send_command(command):
    """Sends a command to the RDS encoder and logs SEND and RECV."""
    response = f"Error: Not Sent" # Default error response
    logging.info(f"SEND: {command}") # Log command being sent
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10) # Connection/read timeout
            s.connect((RDS_IP, RDS_PORT))
            s.sendall((command + '\r\n').encode('utf-8')) # Ensure CRLF line ending

            # Read response
            response_bytes = s.recv(1024)
            response = response_bytes.decode('utf-8', errors='ignore').strip()
            # Log successful receive - This is the primary RECV log
            logging.info(f"RECV: {response}")

    except socket.timeout:
        response = "Error: Timeout"
        # Log the generated error response as if it was received
        logging.error(f"RECV Error: Timeout after sending command: {command}") # Keep error context
        logging.info(f"RECV: {response}") # Log the error string as the effective response
    except ConnectionRefusedError:
         response = "Error: Connection Refused"
         logging.error(f"SEND Error: Connection Refused for command: {command}") # Keep error context
         logging.info(f"RECV: {response}") # Log the error string as the effective response
    except OSError as e: # Catch socket errors more broadly
        response = f"Error: Socket Error ({e.strerror})"
        logging.error(f"SEND/RECV Error: {e} for command: {command}") # Keep error context
        logging.info(f"RECV: {response}") # Log the error string as the effective response
    except Exception as e:
        response = f"Error: {type(e).__name__}"
        logging.error(f"SEND/RECV Error: Unexpected exception {e} for command: {command}") # Keep error context
        logging.info(f"RECV: {response}") # Log the error string as the effective response

    return response # Return the response or error string

# --- send_message_to_rds function (Uses send_command) ---
def send_message_to_rds(text):
    """Formats and sends the text message to the RDS encoder. (No logging here)"""
    if not text:
        # print("Warning: Attempted to send an empty message to RDS. Skipping.", file=sys.stderr)
        return

    sanitized_text = text.replace('\r', ' ').replace('\n', ' ').strip()
    max_len = 64
    if len(sanitized_text) > max_len:
        # print(f"Warning: Message truncated to {max_len} chars: '{sanitized_text[:max_len]}'", file=sys.stderr)
        sanitized_text = sanitized_text[:max_len]
    elif len(sanitized_text) == 0:
        # print("Warning: Message became empty after sanitization. Sending default message instead.", file=sys.stderr)
        sanitized_text = DEFAULT_MESSAGE[:max_len]

    # Send the command - logging happens within send_command
    send_command(f"DPSTEXT={sanitized_text}")
    time.sleep(0.2) # Small delay between commands if needed

# --- Main Loop ---
def main():
    message_index = 0
    last_message_time = 0
    current_message_duration = 10
    last_sent_text = None

    logging.info("--- AutoRDS Script Started ---") # Log startup

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

                    if formatted_text and formatted_text != last_sent_text:
                        display_text = formatted_text
                        selected_duration = current_valid_message.get("Message Time", 10)
                        message_index = (message_index + 1)
                    elif not formatted_text:
                         last_message_time = current_time # Reset timer even if skipped
                         current_message_duration = 1 # Wait briefly before trying next
                    else:
                        # Text is the same, reset timer, keep duration
                        last_message_time = current_time
                        current_message_duration = selected_duration

            if display_text is not None:
                # Sending happens here, logging is inside send_command
                send_message_to_rds(display_text)
                last_sent_text = display_text
                last_message_time = current_time
                current_message_duration = selected_duration

            time.sleep(1)

        except KeyboardInterrupt:
            logging.info("--- KeyboardInterrupt detected. Exiting AutoRDS... ---") # Log shutdown
            print("\nExiting AutoRDS...", file=sys.stderr)
            break
        except Exception as e:
            # Log fatal exceptions to help diagnose crashes
            logging.exception("--- FATAL ERROR in main loop ---")
            print(f"FATAL ERROR in main loop: {e}", file=sys.stderr)
            print("Attempting to continue after 15 second delay...", file=sys.stderr)
            time.sleep(15)

if __name__ == "__main__":
    main()

# --- END OF FILE autoRDS.py ---