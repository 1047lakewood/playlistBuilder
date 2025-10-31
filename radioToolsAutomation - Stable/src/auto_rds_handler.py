import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import os
import threading
from lecture_detector import LectureDetector

# Logger will be set in __init__ based on station_id

# Assuming ConfigManager is in the same directory or PYTHONPATH is set
# from config_manager import ConfigManager # Import will be done in main_app

# --- Constants (Consider making these configurable later via ConfigManager) ---
# RDS_IP = "50.208.125.83" # From original script
# RDS_PORT = 10001         # From original script
# NOW_PLAYING_XML = r"G:\To_RDS\nowplaying.xml" # From original script
# DEFAULT_MESSAGE = "732.901.7777 to SUPPORT and hear this program!" # From original script
SOCKET_TIMEOUT = 10 # Seconds
COMMAND_DELAY = 0.2 # Seconds between RDS commands
LOOP_SLEEP = 1      # Seconds between main loop checks
ERROR_RETRY_DELAY = 15 # Seconds to wait after a major loop error
KEEPALIVE_INTERVAL = 60  # Seconds - resend same message to maintain RDS encoder state

class AutoRDSHandler:
    # Accept log_queue in init, though not directly used here (logger config handles it)
    def __init__(self, log_queue, config_manager, station_id):
        """
        Initializes the AutoRDS handler.

        Args:
            log_queue: Log queue for logging (passed but not directly used)
            config_manager: An instance of ConfigManager to access configuration.
            station_id: Station identifier (e.g., 'station_1047' or 'station_887')
        """
        self.config_manager = config_manager
        self.station_id = station_id
        self.running = False
        self.thread = None
        self.message_index = 0
        self.last_send_time = 0.0  # Monotonic time of last RDS send
        self.current_message_duration = 10 # Default duration
        self.last_sent_text = None

        # XML caching variables
        self._xml_cache = None
        self._xml_cache_time = 0
        self._xml_cache_mtime = 0

        # Set up logger based on station_id
        logger_name = f'AutoRDS_{station_id.split("_")[1]}'  # e.g., 'AutoRDS_1047'
        self.logger = logging.getLogger(logger_name)

        # Load configurable settings from config
        self.reload_configuration()

        # Initialize LectureDetector
        self.reload_lecture_detector()

    def reload_configuration(self):
        """Reload configuration settings from config manager."""
        self.rds_ip = self.config_manager.get_station_setting(self.station_id, "settings.rds.ip", "50.208.125.83")
        self.rds_port = self.config_manager.get_station_setting(self.station_id, "settings.rds.port", 10001)
        self.now_playing_xml = self.config_manager.get_station_setting(self.station_id, "settings.rds.now_playing_xml", r"G:\To_RDS\nowplaying.xml")
        self.default_message = self.config_manager.get_station_setting(self.station_id, "settings.rds.default_message", "732.901.7777 to SUPPORT and hear this program!")

    def reload_lecture_detector(self):
        """Reload the LectureDetector with current configuration."""
        self.lecture_detector = LectureDetector(
            xml_path=self.now_playing_xml,
            config_manager=self.config_manager
        )

    def _load_now_playing(self):
        """Loads now playing information from the XML file with caching."""
        current_time = time.time()

        try:
            if not os.path.exists(self.now_playing_xml):
                # Clear cache if file doesn't exist
                self._xml_cache = None
                self._xml_cache_time = 0
                self._xml_cache_mtime = 0
                return {"artist": "", "title": ""}

            # Check if we can use cached result (within 2 seconds and file not modified)
            try:
                current_mtime = os.path.getmtime(self.now_playing_xml)
                if (self._xml_cache is not None and
                    current_time - self._xml_cache_time < 2.0 and
                    current_mtime == self._xml_cache_mtime):
                    return self._xml_cache
            except OSError:
                # If we can't get mtime, don't use cache
                pass

            # Add a small delay before parsing, might help with file write completion issues
            time.sleep(0.1)
            tree = ET.parse(self.now_playing_xml)
            root = tree.getroot()
            current_track = root.find("TRACK")
            if current_track is not None:
                artist = current_track.get("ARTIST", "").strip()
                title = current_track.findtext("TITLE", "").strip()
                result = {"artist": artist, "title": title}
            else:
                result = {"artist": "", "title": ""}

            # Cache the result
            self._xml_cache = result
            self._xml_cache_time = current_time
            self._xml_cache_mtime = current_mtime
            return result

        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML file ({self.now_playing_xml}): {e}. Check if file is valid/complete.")
            # Clear cache on parse error
            self._xml_cache = None
            self._xml_cache_time = 0
            self._xml_cache_mtime = 0
            return {"artist": "", "title": ""}
        except FileNotFoundError:
             # This might happen if the file disappears between os.path.exists and ET.parse
             self.logger.warning(f"Now playing XML disappeared during read: {self.now_playing_xml}")
             # Clear cache
             self._xml_cache = None
             self._xml_cache_time = 0
             self._xml_cache_mtime = 0
             return {"artist": "", "title": ""}
        except Exception as e:
            self.logger.exception(f"Error loading now playing data: {e}")
            # Clear cache on error
            self._xml_cache = None
            self._xml_cache_time = 0
            self._xml_cache_mtime = 0
            return {"artist": "", "title": ""}

    def _should_display_message(self, message, now_playing):
        """
        Determines if a message should be displayed based on Enabled status,
        Lecture detection (using LectureDetector), Placeholders, and Schedule.
        """
        if not message.get("Enabled", True):
            return False

        message_text = message.get("Text", "")
        artist_name = now_playing.get("artist", "")
        artist_name_upper = artist_name.upper()

        # --- Lecture Detection Logic (using LectureDetector) ---
        # Update the lecture detector's lists in case config changed
        self.lecture_detector.update_lists()
        
        # Check if current track is a lecture
        is_current_lecture = self.lecture_detector.is_current_track_lecture()
        
        if artist_name:
            if is_current_lecture:
                # Current track is a lecture - messages with {artist} should be displayed
                self.logger.debug(f"Current track artist '{artist_name}' is a lecture. Message allowed.")
            else:
                # Current track is NOT a lecture - skip messages that use {artist}
                if "{artist}" in message_text:
                    self.logger.debug(f"Current track artist '{artist_name}' is NOT a lecture, and message '{message_text}' uses {{artist}}. Skipping message.")
                    return False # Skip this specific message
                else:
                    self.logger.debug(f"Current track artist '{artist_name}' is NOT a lecture, but message '{message_text}' doesn't use {{artist}}. Message allowed.")
        
        # If we reach here, the lecture filter (if applicable to this message) passed.
        # Continue with other checks.
        # --- End Lecture Detection ---

        # Placeholder Checks
        if "{artist}" in message_text and not artist_name:
            self.logger.debug(f"Message '{message_text}' requires artist, but none playing.")
            return False
        if "{title}" in message_text and not now_playing.get("title"):
            self.logger.debug(f"Message '{message_text}' requires title, but none playing.")
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
                self.logger.debug(f"Message '{message_text}' not scheduled for today ({full_day_name}).")
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
                            self.logger.warning(f"Invalid hour format in schedule time: {time_obj}")
                            continue # Skip invalid time object
                    else:
                         self.logger.warning(f"Unexpected format in schedule times list: {time_obj}")

                if not hour_match:
                    self.logger.debug(f"Message '{message_text}' not scheduled for this hour ({current_hour}).")
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
        self.logger.info(f"SEND: {command}") # Log command being sent
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(SOCKET_TIMEOUT)
                s.connect((self.rds_ip, self.rds_port))
                # Ensure CRLF line ending, UTF-8 encoded
                s.sendall((command + '\r\n').encode('utf-8'))

                # Read response
                response_bytes = s.recv(1024)
                response = response_bytes.decode('utf-8', errors='ignore').strip()
                # Log successful receive
                self.logger.info(f"RECV: {response}")

        except socket.timeout:
            response = "Error: Timeout"
            self.logger.error(f"RECV Error: Timeout after sending command: {command}")
            self.logger.info(f"RECV: {response}") # Log the error string as the effective response
        except ConnectionRefusedError:
            response = "Error: Connection Refused"
            self.logger.error(f"SEND Error: Connection Refused for command: {command}")
            self.logger.info(f"RECV: {response}")
        except OSError as e: # Catch other socket errors
            response = f"Error: Socket Error ({e.strerror})"
            self.logger.error(f"SEND/RECV Error: {e} for command: {command}")
            self.logger.info(f"RECV: {response}")
        except Exception as e:
            response = f"Error: {type(e).__name__}"
            self.logger.exception(f"SEND/RECV Error: Unexpected exception for command: {command}")
            self.logger.info(f"RECV: {response}")

        return response

    def _send_message_to_rds(self, text):
        """Formats and sends the text message to the RDS encoder."""
        if not text:
            self.logger.warning("Attempted to send an empty message to RDS. Skipping.")
            return

        # Sanitize and truncate
        sanitized_text = text.replace('\r', ' ').replace('\n', ' ').strip()
        max_len = 64
        if len(sanitized_text) > max_len:
            self.logger.warning(f"Message truncated to {max_len} chars: '{sanitized_text[:max_len]}'")
            sanitized_text = sanitized_text[:max_len]
        elif len(sanitized_text) == 0:
            self.logger.warning("Message became empty after sanitization. Sending default message instead.")
            sanitized_text = self.default_message[:max_len] # Ensure default is also truncated if needed

        # Send the command - logging happens within _send_command
        self._send_command(f"DPSTEXT={sanitized_text}")
        time.sleep(COMMAND_DELAY) # Small delay between commands

    def get_current_display_messages(self):
        """Returns a list of messages currently eligible for display."""
        try:
            messages = self.config_manager.get_station_messages(self.station_id)
            now_playing = self._load_now_playing()
            valid_messages = [m for m in messages if self._should_display_message(m, now_playing)]
            
            formatted_list = []
            for msg in valid_messages:
                 text = self._format_message_text(msg["Text"], now_playing)
                 if text: # Only include if formatting doesn't result in empty string
                     formatted_list.append(text)

            if not formatted_list and self.default_message:
                 return [self.default_message] # Return default if no valid messages

            return formatted_list
        except Exception as e:
            self.logger.exception(f"Error getting current display messages: {e}")
            return [f"Error: {e}"]


    def run(self):
        """The main loop for the AutoRDS logic."""
        self.running = True
        self.logger.info("--- AutoRDS Handler Started ---")
        self.logger.info(f"AutoRDS handler {self.station_id} is running in thread: {threading.current_thread().name}")

        try:
            while self.running:
                try:
                    now = time.monotonic()

                    # Reload messages and check now playing in each loop iteration
                    messages = self.config_manager.get_station_messages(self.station_id) # Get latest from config manager
                    now_playing = self._load_now_playing()

                    self.logger.debug(f"Found {len(messages)} messages and now playing: {now_playing}")

                    # Filter messages based on current conditions
                    valid_messages = [m for m in messages if self._should_display_message(m, now_playing)]

                    self.logger.debug(f"Found {len(valid_messages)} valid messages for station {self.station_id}")

                    display_text = None
                    selected_duration = 10 # Default duration

                    # Determine what to display - select message but don't advance index yet
                    if not valid_messages:
                        # No valid custom messages, use default message
                        display_text = self.default_message
                        selected_duration = 10 # Default duration for default message
                    else:
                        # There are valid custom messages, select the current one
                        if len(valid_messages) > 0:
                            current_valid_message = valid_messages[self.message_index % len(valid_messages)]
                            formatted_text = self._format_message_text(current_valid_message["Text"], now_playing)

                            if formatted_text:
                                display_text = formatted_text
                                selected_duration = current_valid_message.get("Message Time", 10)
                            else:
                                # Message evaluated to empty, skip it and try next
                                self.logger.debug(
                                    f"Formatted message resulted in empty string, skipping: {current_valid_message['Text']}"
                                )
                                self.message_index = (self.message_index + 1) % len(valid_messages)
                                # Don't set display_text, will fall back to default
                        
                    # Send the message if one was chosen
                    if display_text is not None:
                        # Check if rotation is due (message duration elapsed)
                        time_since_last_send = now - self.last_send_time
                        rotation_due = (time_since_last_send >= self.current_message_duration)
                        
                        # Check if keepalive is due (same message, 60s elapsed)
                        keepalive_due = (display_text == self.last_sent_text) and (time_since_last_send >= KEEPALIVE_INTERVAL)
                        
                        should_send = rotation_due or keepalive_due

                        self.logger.debug(f"Time since last send: {time_since_last_send:.1f}s, Rotation due: {rotation_due}, Keepalive due: {keepalive_due}, Should send: {should_send}")

                        if should_send:
                            send_type = "keepalive" if keepalive_due and not rotation_due else "rotation"
                            self.logger.info(f"Sending RDS message ({send_type}): '{display_text}' for {selected_duration}s")
                            try:
                                self._send_message_to_rds(display_text)
                                self.logger.info(f"Sent RDS message: {display_text}")
                            except Exception as e:
                                self.logger.error(f"Failed to send RDS message '{display_text}': {e}")
                            
                            self.last_sent_text = display_text
                            self.last_send_time = now
                            self.current_message_duration = selected_duration
                            
                            # Only advance message index on rotation sends
                            if rotation_due and valid_messages:
                                self.message_index = (self.message_index + 1) % len(valid_messages)
                                self.logger.debug(f"Advanced message index to {self.message_index}")
                            
                            self.logger.debug(f"Updated last_send_time to {self.last_send_time}")
                        else:
                            # Don't update timer - wait for the interval to pass
                            self.logger.debug(f"Not sending yet - only {time_since_last_send:.1f}s since last send (need {self.current_message_duration}s for rotation, {KEEPALIVE_INTERVAL}s for keepalive)")

                    # Wait before the next check
                    time.sleep(LOOP_SLEEP)

                except KeyboardInterrupt:
                    # This shouldn't happen if running in a thread managed by the GUI,
                    # but handle it just in case. The GUI's on_closing should handle shutdown.
                    self.logger.info("KeyboardInterrupt received in AutoRDS handler loop.")
                    self.running = False # Signal loop to stop
                except Exception as e:
                    # Log fatal exceptions to help diagnose crashes
                    self.logger.exception("--- FATAL ERROR in AutoRDS handler loop ---")
                    # Wait before potentially retrying
                    self.logger.info(f"Attempting to continue after {ERROR_RETRY_DELAY} second delay...")
                    time.sleep(ERROR_RETRY_DELAY)

        except Exception as e:
            # This catches any exceptions from the main try block
            self.logger.exception("--- CRITICAL ERROR in AutoRDS handler ---")
        finally:
            self.logger.info("--- AutoRDS Handler Stopped ---")

    def start(self):
        """Starts the handler in a separate thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True, name="AutoRDSThread") # Name thread
            self.thread.start()
            self.logger.info("AutoRDS handler thread started.")
        else:
            self.logger.warning("AutoRDS handler already running.")

    def stop(self):
        """Signals the handler thread to stop."""
        if self.running:
            self.logger.info("Stopping AutoRDS handler thread...")
            self.running = False
            # Optionally wait for thread to finish, but daemon=True should handle exit
            # if self.thread:
            #     self.thread.join(timeout=5) # Wait max 5 seconds
            #     if self.thread.is_alive():
            #         self.logger.warning("AutoRDS handler thread did not stop gracefully.")
            self.thread = None
        else:
            self.logger.info("AutoRDS handler already stopped.")

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