import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import os
import threading

# Get the specific logger for this handler
logger = logging.getLogger('AutoRDS')

# Assuming ConfigManager is in the same directory or PYTHONPATH is set
# from config_manager import ConfigManager # Import will be done in main_app

# --- Constants (Consider making these configurable later via ConfigManager) ---
RDS_IP = "50.208.125.83" # From original script
RDS_PORT = 10001         # From original script
NOW_PLAYING_XML = r"G:\To_RDS\nowplaying.xml" # From original script
DEFAULT_MESSAGE = "732.901.7777 to SUPPORT and hear this program!" # From original script
SOCKET_TIMEOUT = 10 # Seconds
COMMAND_DELAY = 0.2 # Seconds between RDS commands
LOOP_SLEEP = 1      # Seconds between main loop checks
ERROR_RETRY_DELAY = 15 # Seconds to wait after a major loop error

class AutoRDSHandler:
    # Accept log_queue in init, though not directly used here (logger config handles it)
    def __init__(self, config_manager, log_queue):
        """
        Initializes the AutoRDS handler.

        Args:
            config_manager: An instance of ConfigManager to access configuration.
        """
        self.config_manager = config_manager
        self.running = False
        self.thread = None
        self.message_index = 0
        self.last_message_time = 0
        self.current_message_duration = 10 # Default duration
        self.last_sent_text = None

    def _load_now_playing(self):
        """Loads now playing information from the XML file."""
        try:
            if not os.path.exists(NOW_PLAYING_XML):
                # Use the named logger
                # logger.warning(f"Now playing XML not found: {NOW_PLAYING_XML}")
                return {"artist": "", "title": ""}

            # Add a small delay before parsing, might help with file write completion issues
            time.sleep(0.1)
            tree = ET.parse(NOW_PLAYING_XML)
            root = tree.getroot()
            current_track = root.find("TRACK")
            if current_track is not None:
                artist = current_track.get("ARTIST", "").strip()
                title = current_track.findtext("TITLE", "").strip()
                return {"artist": artist, "title": title}
            else:
                return {"artist": "", "title": ""}
        except ET.ParseError as e:
            logger.error(f"Error parsing XML file ({NOW_PLAYING_XML}): {e}. Check if file is valid/complete.")
            return {"artist": "", "title": ""}
        except FileNotFoundError:
             # This might happen if the file disappears between os.path.exists and ET.parse
             logger.warning(f"Now playing XML disappeared during read: {NOW_PLAYING_XML}")
             return {"artist": "", "title": ""}
        except Exception as e:
            logger.exception(f"Error loading now playing data: {e}")
            return {"artist": "", "title": ""}

    def _should_display_message(self, message, now_playing):
        """
        Determines if a message should be displayed based on Enabled status,
        Artist filtering (R rule, Whitelist, Blacklist from config), Placeholders, and Schedule.
        """
        if not message.get("Enabled", True):
            return False

        message_text = message.get("Text", "")
        artist_name = now_playing.get("artist", "")
        artist_name_upper = artist_name.upper()

        # --- Artist Filtering Logic (using config) ---
        # Convert to sets for efficient lookup inside the check
        artist_whitelist = {name.upper() for name in self.config_manager.get_whitelist()}
        artist_blacklist = {name.upper() for name in self.config_manager.get_blacklist()}

        if artist_name:
            if artist_name_upper in artist_blacklist:
                logger.debug(f"Artist '{artist_name}' blacklisted.")
                return False # Blacklisted

            is_whitelisted = artist_name_upper in artist_whitelist
            passes_r_rule_or_whitelist = is_whitelisted or artist_name_upper.startswith('R')

            if not passes_r_rule_or_whitelist:
                # Artist fails 'R' rule AND is not whitelisted.
                # Check if the message *requires* the artist placeholder.
                if "{artist}" in message_text:
                    logger.debug(f"Artist '{artist_name}' fails R-rule/whitelist, and message '{message_text}' uses {{artist}}. Skipping message.")
                    return False # Skip this specific message
                else:
                    # Artist fails rule, but message doesn't need artist. Continue checks.
                    logger.debug(f"Artist '{artist_name}' fails R-rule/whitelist, but message '{message_text}' doesn't use {{artist}}. Continuing checks.")
            elif is_whitelisted:
                 logger.debug(f"Artist '{artist_name}' is whitelisted.")
            elif artist_name_upper.startswith('R'):
                 logger.debug(f"Artist '{artist_name}' starts with 'R'.")
            # If artist_name is empty, the R-rule/whitelist check is skipped implicitly.

        # If we reach here, the artist filter (if applicable to this message) passed.
        # Continue with other checks.
        # --- End Artist Filtering ---

        # Placeholder Checks
        if "{artist}" in message_text and not artist_name:
            logger.debug(f"Message '{message_text}' requires artist, but none playing.")
            return False
        if "{title}" in message_text and not now_playing.get("title"):
            logger.debug(f"Message '{message_text}' requires title, but none playing.")
            return False

        # Scheduling Checks
        schedule_info = message.get("Scheduled", {})
        if schedule_info.get("Enabled", False):
            now = datetime.now()
            current_day_abbr = now.strftime("%a") # e.g., "Sun", "Mon"
            current_hour = now.hour             # 0-23
            # Map abbreviation to full name used in config
            day_mapping = {"Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday",
                           "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday",
                           "Sat": "Saturday"}
            full_day_name = day_mapping.get(current_day_abbr)

            scheduled_days = schedule_info.get("Days", [])
            if scheduled_days and full_day_name not in scheduled_days:
                logger.debug(f"Message '{message_text}' not scheduled for today ({full_day_name}).")
                return False # Not scheduled for today

            scheduled_times = schedule_info.get("Times", []) # Expects list of {"hour": H}
            if scheduled_times:
                hour_match = False
                for time_obj in scheduled_times:
                    # Check if it's a dictionary and has the 'hour' key
                    if isinstance(time_obj, dict) and "hour" in time_obj:
                        try:
                            if int(time_obj.get("hour")) == current_hour:
                                hour_match = True
                                break
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid hour format in schedule time: {time_obj}")
                            continue # Skip invalid time object
                    else:
                         logger.warning(f"Unexpected format in schedule times list: {time_obj}")

                if not hour_match:
                    logger.debug(f"Message '{message_text}' not scheduled for this hour ({current_hour}).")
                    return False # Not scheduled for this hour

        return True # Passed all checks

    def _format_message_text(self, text, now_playing):
        """Replaces placeholders in the message text."""
        artist = now_playing.get("artist", "")
        title = now_playing.get("title", "")
        # Use uppercase for artist placeholder as per original script
        replacements = {
            "{artist}": artist.upper() if artist else "",
            "{title}": title if title else ""
        }
        formatted_text = text
        for placeholder, value in replacements.items():
            formatted_text = formatted_text.replace(placeholder, value)
        return formatted_text.strip()

    def _send_command(self, command):
        """Sends a command to the RDS encoder and logs SEND and RECV."""
        response = "Error: Not Sent" # Default error response
        logger.info(f"SEND: {command}") # Log command being sent
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(SOCKET_TIMEOUT)
                s.connect((RDS_IP, RDS_PORT))
                # Ensure CRLF line ending, UTF-8 encoded
                s.sendall((command + '\r\n').encode('utf-8'))

                # Read response
                response_bytes = s.recv(1024)
                response = response_bytes.decode('utf-8', errors='ignore').strip()
                # Log successful receive
                logger.info(f"RECV: {response}")

        except socket.timeout:
            response = "Error: Timeout"
            logger.error(f"RECV Error: Timeout after sending command: {command}")
            logger.info(f"RECV: {response}") # Log the error string as the effective response
        except ConnectionRefusedError:
            response = "Error: Connection Refused"
            logger.error(f"SEND Error: Connection Refused for command: {command}")
            logger.info(f"RECV: {response}")
        except OSError as e: # Catch other socket errors
            response = f"Error: Socket Error ({e.strerror})"
            logger.error(f"SEND/RECV Error: {e} for command: {command}")
            logger.info(f"RECV: {response}")
        except Exception as e:
            response = f"Error: {type(e).__name__}"
            logger.exception(f"SEND/RECV Error: Unexpected exception for command: {command}")
            logger.info(f"RECV: {response}")

        return response

    def _send_message_to_rds(self, text):
        """Formats and sends the text message to the RDS encoder."""
        if not text:
            logger.warning("Attempted to send an empty message to RDS. Skipping.")
            return

        # Sanitize and truncate
        sanitized_text = text.replace('\r', ' ').replace('\n', ' ').strip()
        max_len = 64
        if len(sanitized_text) > max_len:
            logger.warning(f"Message truncated to {max_len} chars: '{sanitized_text[:max_len]}'")
            sanitized_text = sanitized_text[:max_len]
        elif len(sanitized_text) == 0:
            logger.warning("Message became empty after sanitization. Sending default message instead.")
            sanitized_text = DEFAULT_MESSAGE[:max_len] # Ensure default is also truncated if needed

        # Send the command - logging happens within _send_command
        self._send_command(f"DPSTEXT={sanitized_text}")
        time.sleep(COMMAND_DELAY) # Small delay between commands

    def get_current_display_messages(self):
        """Returns a list of messages currently eligible for display."""
        try:
            messages = self.config_manager.get_messages()
            now_playing = self._load_now_playing()
            valid_messages = [m for m in messages if self._should_display_message(m, now_playing)]
            
            formatted_list = []
            for msg in valid_messages:
                 text = self._format_message_text(msg["Text"], now_playing)
                 if text: # Only include if formatting doesn't result in empty string
                     formatted_list.append(text)

            if not formatted_list and DEFAULT_MESSAGE:
                 return [DEFAULT_MESSAGE] # Return default if no valid messages

            return formatted_list
        except Exception as e:
            logger.exception(f"Error getting current display messages: {e}")
            return [f"Error: {e}"]


    def run(self):
        """The main loop for the AutoRDS logic."""
        self.running = True
        logger.info("--- AutoRDS Handler Started ---")

        while self.running:
            try:
                current_time = time.time()

                # Reload messages and check now playing in each loop iteration
                messages = self.config_manager.get_messages() # Get latest from config manager
                now_playing = self._load_now_playing()

                # Filter messages based on current conditions
                valid_messages = [m for m in messages if self._should_display_message(m, now_playing)]

                display_text = None
                selected_duration = 10 # Default duration

                # Determine what to display
                if not valid_messages:
                    # No valid custom messages, check if it's time for the default
                    if current_time - self.last_message_time >= self.current_message_duration:
                        if self.last_sent_text != DEFAULT_MESSAGE:
                            display_text = DEFAULT_MESSAGE
                            selected_duration = 10 # Default duration for default message
                        else:
                            # Default is already showing, just reset timer
                            self.last_message_time = current_time
                            self.current_message_duration = 10
                else:
                    # There are valid custom messages, check if it's time to rotate
                    if current_time - self.last_message_time >= self.current_message_duration:
                        # Cycle through valid messages
                        if len(valid_messages) > 0:
                             current_valid_message = valid_messages[self.message_index % len(valid_messages)]
                             formatted_text = self._format_message_text(current_valid_message["Text"], now_playing)

                             if formatted_text and formatted_text != self.last_sent_text:
                                 display_text = formatted_text
                                 selected_duration = current_valid_message.get("Message Time", 10)
                                 # Increment index ONLY when a new message is selected to be sent
                                 self.message_index = (self.message_index + 1)
                             elif not formatted_text:
                                 # Message evaluated to empty (e.g., placeholder missing), skip it
                                 logger.debug(f"Formatted message resulted in empty string, skipping: {current_valid_message['Text']}")
                                 # Reset timer but use short duration to try next message quickly
                                 self.last_message_time = current_time
                                 self.current_message_duration = 1 # Wait briefly before trying next
                             else:
                                 # Text is the same as last sent, reset timer, keep duration
                                 logger.debug(f"Message text '{formatted_text}' is same as last sent, resetting timer.")
                                 self.last_message_time = current_time
                                 self.current_message_duration = selected_duration # Keep last duration
                        else:
                             # Should not happen if valid_messages check is correct, but as fallback:
                             self.last_message_time = current_time
                             self.current_message_duration = 1 # Wait briefly

                # Send the message if one was chosen
                if display_text is not None:
                    logger.info(f"Selected message to display: '{display_text}' for {selected_duration}s")
                    self._send_message_to_rds(display_text)
                    self.last_sent_text = display_text
                    self.last_message_time = current_time
                    self.current_message_duration = selected_duration

                # Wait before the next check
                time.sleep(LOOP_SLEEP)

            except KeyboardInterrupt:
                # This shouldn't happen if running in a thread managed by the GUI,
                # but handle it just in case. The GUI's on_closing should handle shutdown.
                logger.info("KeyboardInterrupt received in AutoRDS handler loop.")
                self.running = False # Signal loop to stop
            except Exception as e:
                # Log fatal exceptions to help diagnose crashes
                logger.exception("--- FATAL ERROR in AutoRDS handler loop ---")
                # Wait before potentially retrying
                logger.info(f"Attempting to continue after {ERROR_RETRY_DELAY} second delay...")
                time.sleep(ERROR_RETRY_DELAY)

        logger.info("--- AutoRDS Handler Stopped ---")

    def start(self):
        """Starts the handler in a separate thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True, name="AutoRDSThread") # Name thread
            self.thread.start()
            logger.info("AutoRDS handler thread started.")
        else:
            logger.warning("AutoRDS handler already running.")

    def stop(self):
        """Signals the handler thread to stop."""
        if self.running:
            logger.info("Stopping AutoRDS handler thread...")
            self.running = False
            # Optionally wait for thread to finish, but daemon=True should handle exit
            # if self.thread:
            #     self.thread.join(timeout=5) # Wait max 5 seconds
            #     if self.thread.is_alive():
            #         logger.warning("AutoRDS handler thread did not stop gracefully.")
            self.thread = None
        else:
            logger.info("AutoRDS handler already stopped.")

# Example usage (for testing - requires a ConfigManager instance)
if __name__ == "__main__":
    # This basic test won't run without a mock ConfigManager
    # and proper logging setup like in main_app.py
    print("This script needs to be run as part of the main application.")
    # Example:
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    # class MockConfigManager:
    #     def get_messages(self): return [{"Text": "Test", "Enabled": True, "Message Time": 5}]
    #     def get_whitelist(self): return []
    #     def get_blacklist(self): return []
    # mock_config = MockConfigManager()
    # handler = AutoRDSHandler(mock_config)
    # handler.start()
    # try:
    #     while True: time.sleep(1)
    # except KeyboardInterrupt:
    #     handler.stop()
