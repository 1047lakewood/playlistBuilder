import os
import time
import xml.etree.ElementTree as ET
import shutil
import logging
import urllib.request
from datetime import datetime, timedelta
import random
from pydub import AudioSegment
import sys
import setproctitle

setproctitle.setproctitle("Intro Loader")
# Setup logging ONLY to console with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s', # Added timestamp format back
    datefmt='%Y-%m-%d %H:%M:%S',      # Explicit date format
    stream=sys.stdout                 # Explicitly set stream to standard output
)

# File paths
XML_FILE_PATH = r"G:\To_RDS\nowplaying.xml"
MP3_DIRECTORY = r"G:\Shiurim\introsCleanedUp"
LOG_DIRECTORY = r"G:\Misc\Dev\Current Artist Intro Loader"
CURRENT_ARTIST_FILE = os.path.join(MP3_DIRECTORY, "currentArtist.mp3")
ACTUAL_CURRENT_ARTIST_FILE = os.path.join(MP3_DIRECTORY, "actualCurrentArtist.mp3")
BLANK_MP3_FILE = os.path.join(MP3_DIRECTORY, "blank.mp3")
SILENT_MP3_FILE = os.path.join(MP3_DIRECTORY, "near_silent.mp3")
MISSING_ARTIST_LOG = os.path.join(LOG_DIRECTORY, "missing_artists.log")

# Schedule URL
SCHEDULE_URL = "http://192.168.3.12:9000/?pass=bmas220&action=schedule&type=run&id=TBACFNBGJKOMETDYSQYR"

# Tracking when to run the schedule next
next_schedule_run = None

def log_missing_artist(artist_name, filename, is_current=True):
    """Log missing artist to external log file. (No console output)"""
    try:
        os.makedirs(LOG_DIRECTORY, exist_ok=True)
        with open(MISSING_ARTIST_LOG, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            artist_type = "Current" if is_current else "Next"
            log_entry = None
            if is_current and artist_name and artist_name.startswith("R"):
                 log_entry = f"{timestamp} - {artist_type} Artist MP3 not found: '{artist_name}', Source FILENAME: '{filename}'\n"
            
            if log_entry:
                f.write(log_entry)
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error writing to missing artist log: {e}", file=sys.stderr)


def get_artists_from_xml():
    """Extract the current and next artists' names and filenames from the XML file. (No console output)"""
    try:
        # Add a small delay before parsing, might help with file write completion issues
        time.sleep(0.1)
        tree = ET.parse(XML_FILE_PATH)
        root = tree.getroot()

        current_track_elem = root.find("TRACK")
        current_artist = None
        current_filename = None
        if current_track_elem is not None:
            current_artist = current_track_elem.attrib.get("ARTIST", "").strip() or None
            current_filename = current_track_elem.attrib.get("FILENAME", "").strip() or None

        next_track_elem = root.find("NEXTTRACK/TRACK")
        next_artist = None
        next_filename = None
        if next_track_elem is not None:
            next_artist = next_track_elem.attrib.get("ARTIST", "").strip() or None
            next_filename = next_track_elem.attrib.get("FILENAME", "").strip() or None

        return (current_artist, current_filename), (next_artist, next_filename)
    except FileNotFoundError:
        # Don't print error here, handle upstream
        return (None, None), (None, None)
    except ET.ParseError as e:
        # Log XML parsing errors specifically
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error parsing XML ({XML_FILE_PATH}): {e}. Check if file is valid/complete.", file=sys.stderr)
        return (None, None), (None, None)
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error reading/parsing XML: {e}", file=sys.stderr) # Log critical errors to stderr
        return (None, None), (None, None)


def concatenate_mp3_files(files, output_path):
    """Concatenate multiple MP3 files into a single file. (No console output)"""
    try:
        if not files: return False
        for file_path in files:
            if not os.path.exists(file_path): return False

        combined = AudioSegment.empty()
        for file_path in files:
            # Add error handling for individual file loading
            try:
                sound = AudioSegment.from_mp3(file_path)
                combined += sound
            except Exception as e_load:
                 print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error loading MP3 for concatenation ({os.path.basename(file_path)}): {e_load}", file=sys.stderr)
                 return False # Fail concatenation if one file fails

        combined.export(output_path, format="mp3")
        return True
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error concatenating MP3 files to {os.path.basename(output_path)}: {e}", file=sys.stderr) # Log critical errors to stderr
        return False


def update_artist_files(current_artist_info, next_artist_info, context="Processing"):
    """Update the currentArtist.mp3 and actualCurrentArtist.mp3 files."""
    success = True
    current_artist, current_filename = current_artist_info
    next_artist, next_filename = next_artist_info
    current_artist_mp3_name = ""
    next_artist_mp3_name = ""

    # --- Handle actualCurrentArtist.mp3 (current artist) ---
    if current_artist:
        matching_files = [file for file in os.listdir(MP3_DIRECTORY)
                          if file.startswith(f"{current_artist}") and file.lower().endswith(".mp3")]
        if matching_files:
            chosen_file = random.choice(matching_files)
            current_artist_file_path = os.path.join(MP3_DIRECTORY, chosen_file)
            current_artist_mp3_name = chosen_file
        else:
            current_artist_mp3_name = f"{current_artist}.mp3"
            current_artist_file_path = os.path.join(MP3_DIRECTORY, current_artist_mp3_name)

        if os.path.exists(current_artist_file_path):
            logging.info(f"{context}: Found {current_artist_mp3_name}")
            try:
                shutil.copy2(current_artist_file_path, ACTUAL_CURRENT_ARTIST_FILE)
                logging.info(f"{context}: Copying {current_artist_mp3_name} to actualCurrentArtist.mp3")
            except Exception as e:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error copying {current_artist_mp3_name} to actualCurrentArtist.mp3: {e}", file=sys.stderr)
                success = False
        else:
            logging.info(f"{context}: Didn't find {current_artist_mp3_name}")
            log_missing_artist(current_artist, current_filename, is_current=True)
            if os.path.exists(BLANK_MP3_FILE):
                try:
                    shutil.copy2(BLANK_MP3_FILE, ACTUAL_CURRENT_ARTIST_FILE)
                    logging.info(f"{context}: Copying {os.path.basename(BLANK_MP3_FILE)} to actualCurrentArtist.mp3")
                except Exception as e:
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error copying blank MP3 to actualCurrentArtist.mp3: {e}", file=sys.stderr)
                    success = False
            else:
                try: open(ACTUAL_CURRENT_ARTIST_FILE, 'wb').close()
                except Exception as e: print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error creating empty actualCurrentArtist.mp3: {e}", file=sys.stderr); success = False
    else:
        log_missing_artist(current_artist, current_filename, is_current=True)
        if os.path.exists(BLANK_MP3_FILE):
            try:
                shutil.copy2(BLANK_MP3_FILE, ACTUAL_CURRENT_ARTIST_FILE)
                logging.info(f"{context}: Copying {os.path.basename(BLANK_MP3_FILE)} to actualCurrentArtist.mp3 (no current artist)")
            except Exception as e:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error copying blank MP3 to actualCurrentArtist.mp3: {e}", file=sys.stderr)
                success = False
        else:
            try: open(ACTUAL_CURRENT_ARTIST_FILE, 'wb').close()
            except Exception as e: print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error creating empty actualCurrentArtist.mp3: {e}", file=sys.stderr); success = False

    # --- Handle currentArtist.mp3 (next artist + silence) ---
    if next_artist:
        matching_files = [file for file in os.listdir(MP3_DIRECTORY)
                          if file.startswith(f"{next_artist}") and file.lower().endswith(".mp3")]
        if matching_files:
            chosen_file = random.choice(matching_files)
            next_artist_file_path = os.path.join(MP3_DIRECTORY, chosen_file)
            next_artist_mp3_name = chosen_file
        else:
            next_artist_mp3_name = f"{next_artist}.mp3"
            next_artist_file_path = os.path.join(MP3_DIRECTORY, next_artist_mp3_name)

        if os.path.exists(next_artist_file_path):
            logging.info(f"{context}: Found {next_artist_mp3_name}")
            if os.path.exists(SILENT_MP3_FILE):
                try:
                    concat_success = concatenate_mp3_files(
                        [SILENT_MP3_FILE, next_artist_file_path, SILENT_MP3_FILE],
                        CURRENT_ARTIST_FILE
                    )
                    if concat_success:
                         logging.info(f"{context}: Copying {os.path.basename(SILENT_MP3_FILE)} + {next_artist_mp3_name} + {os.path.basename(SILENT_MP3_FILE)} to currentArtist.mp3")
                    else:
                        # Log concat failure and attempt blank copy
                        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Concatenation failed for {next_artist_mp3_name}, attempting to copy blank.", file=sys.stderr)
                        if os.path.exists(BLANK_MP3_FILE):
                            shutil.copy2(BLANK_MP3_FILE, CURRENT_ARTIST_FILE)
                            logging.info(f"{context}: Copying {os.path.basename(BLANK_MP3_FILE)} to currentArtist.mp3 (concatenation fallback)")
                        else: open(CURRENT_ARTIST_FILE, 'wb').close()
                        success = False
                except Exception as e:
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error creating/copying concatenated MP3 for next artist: {e}", file=sys.stderr)
                    success = False
                    try: # Fallback blank copy on exception
                        if os.path.exists(BLANK_MP3_FILE):
                            shutil.copy2(BLANK_MP3_FILE, CURRENT_ARTIST_FILE)
                            logging.info(f"{context}: Copying {os.path.basename(BLANK_MP3_FILE)} to currentArtist.mp3 (error fallback)")
                        else: open(CURRENT_ARTIST_FILE, 'wb').close()
                    except: pass
            else:
                # Silent MP3 not found, copy artist directly
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Warning: Silent MP3 file not found: {SILENT_MP3_FILE}, copying artist directly", file=sys.stderr) # Optional warning
                try:
                    shutil.copy2(next_artist_file_path, CURRENT_ARTIST_FILE)
                    logging.info(f"{context}: Copying {next_artist_mp3_name} to currentArtist.mp3 (silent file missing)")
                except Exception as e:
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error copying next artist file directly: {e}", file=sys.stderr)
                    success = False
        else:
            logging.info(f"{context}: Didn't find {next_artist_mp3_name}")
            log_missing_artist(next_artist, next_filename, is_current=False)
            if os.path.exists(BLANK_MP3_FILE):
                try:
                    shutil.copy2(BLANK_MP3_FILE, CURRENT_ARTIST_FILE)
                    logging.info(f"{context}: Copying {os.path.basename(BLANK_MP3_FILE)} to currentArtist.mp3")
                except Exception as e:
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error copying blank MP3 to currentArtist.mp3: {e}", file=sys.stderr)
                    success = False
            else:
                try: open(CURRENT_ARTIST_FILE, 'wb').close()
                except Exception as e: print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error creating empty currentArtist.mp3: {e}", file=sys.stderr); success = False
    else:
        log_missing_artist(next_artist, next_filename, is_current=False)
        if os.path.exists(BLANK_MP3_FILE):
            try:
                shutil.copy2(BLANK_MP3_FILE, CURRENT_ARTIST_FILE)
                logging.info(f"{context}: Copying {os.path.basename(BLANK_MP3_FILE)} to currentArtist.mp3 (no next artist)")
            except Exception as e:
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error copying blank MP3 to currentArtist.mp3: {e}", file=sys.stderr)
                success = False
        else:
            try: open(CURRENT_ARTIST_FILE, 'wb').close()
            except Exception as e: print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error creating empty currentArtist.mp3: {e}", file=sys.stderr); success = False

    return success

def run_schedule():
    """Run the schedule URL."""
    logging.info(f"Running schedule URL: {SCHEDULE_URL}") # Log schedule run
    try:
        response = urllib.request.urlopen(SCHEDULE_URL, timeout=10) # Add timeout
        # logging.info(f"Schedule response status: {response.status}") # Optional: log status if needed
        response.close() # Ensure connection is closed
        return True
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error running schedule: {e}", file=sys.stderr) # Log critical errors to stderr
        return False

def perform_initial_check():
    """Runs the check and update logic once at startup."""
    logging.info("Performing initial check of XML file...")
    if not os.path.exists(XML_FILE_PATH):
        logging.warning(f"Initial check: XML file not found at {XML_FILE_PATH}")
        return

    current_artist_info, next_artist_info = get_artists_from_xml()
    # Handle case where XML parsing failed
    if current_artist_info == (None, None) and next_artist_info == (None, None):
         logging.error("Initial check: Failed to read artist info from XML. Skipping initial update.")
         return

    current_artist_name = current_artist_info[0] if current_artist_info[0] else 'None'
    next_artist_name = next_artist_info[0] if next_artist_info[0] else 'None'
    logging.info(f"Initial check: Current artist is {current_artist_name}, Next artist is {next_artist_name}")

    update_artist_files(current_artist_info, next_artist_info, context="Initial Update")
    logging.info("Initial check complete.")


def monitor_xml_file():
    """Monitor the XML file for changes and update artist files accordingly."""
    global next_schedule_run

    last_modified_time = 0
    last_known_current_artist = None
    last_known_next_artist = None

    if os.path.exists(XML_FILE_PATH):
        try:
            last_modified_time = os.path.getmtime(XML_FILE_PATH)
        except FileNotFoundError:
             last_modified_time = 0 # File might disappear between check and getmtime
        # Log initial mod time only if needed for debugging, removed for cleaner output
        # logging.info(f"Monitoring XML file. Initial modification time: {datetime.fromtimestamp(last_modified_time).strftime('%Y-%m-%d %H:%M:%S') if last_modified_time else 'N/A'}")
    else:
         logging.warning(f"XML file {XML_FILE_PATH} does not exist at monitoring start.")


    # Check required files silently at start, warn if missing
    if not os.path.exists(BLANK_MP3_FILE):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Warning: Blank MP3 file {BLANK_MP3_FILE} does not exist. Functionality may be impaired.", file=sys.stderr)
    if not os.path.exists(SILENT_MP3_FILE):
         print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Warning: Silent MP3 file {SILENT_MP3_FILE} does not exist. Concatenation will fail.", file=sys.stderr)


    while True:
        try:
            current_time = datetime.now()

            xml_exists = os.path.exists(XML_FILE_PATH)
            if not xml_exists:
                # Log only once if file disappears
                if last_modified_time != -1: # Use -1 to signify we've logged the disappearance
                     logging.warning(f"XML file {XML_FILE_PATH} not found. Waiting for it to appear...")
                     last_modified_time = -1
                time.sleep(5)
                continue
            # Reset last_modified_time if file reappears after being missing
            if last_modified_time == -1:
                 logging.info(f"XML file {XML_FILE_PATH} found again. Resuming monitoring.")
                 try:
                     last_modified_time = os.path.getmtime(XML_FILE_PATH)
                 except FileNotFoundError:
                     last_modified_time = 0 # Reset if it vanishes again immediately
                 continue


            try:
                current_modified_time = os.path.getmtime(XML_FILE_PATH)
            except FileNotFoundError:
                 # File disappeared between exists check and getmtime
                 if last_modified_time != -1:
                     logging.warning(f"XML file {XML_FILE_PATH} disappeared during check. Waiting...")
                     last_modified_time = -1
                 time.sleep(1) # Short sleep before next loop iteration
                 continue


            if current_modified_time > last_modified_time:
                # Optional: Add a small delay *after* detecting change but *before* reading
                # time.sleep(0.2)
                # Re-check mod time after potential delay
                # try:
                #    current_modified_time = os.path.getmtime(XML_FILE_PATH)
                #    if current_modified_time <= last_modified_time:
                #        continue # Skip if mod time didn't actually change after delay
                # except FileNotFoundError:
                #    continue # File disappeared during check

                # Get artists first
                current_artist_info, next_artist_info = get_artists_from_xml()

                 # Only process if the content actually changed or XML parsing succeeded
                if (current_artist_info, next_artist_info) != ( (None, None), (None, None) ) and \
                   (current_artist_info[0] != last_known_current_artist or next_artist_info[0] != last_known_next_artist):

                    current_artist_name = current_artist_info[0] if current_artist_info[0] else 'None'
                    next_artist_name = next_artist_info[0] if next_artist_info[0] else 'None'

                    logging.info(f"XML file changed, current artist is {current_artist_name}, next artist is {next_artist_name}")

                    last_modified_time = current_modified_time
                    last_known_current_artist = current_artist_info[0]
                    last_known_next_artist = next_artist_info[0]
                    # waitcouple seconds to insure intro plays before being changed
                    time.sleep(10)
                    # Perform the update
                    update_artist_files(current_artist_info, next_artist_info, context="Processing Update")

                    # Set schedule to run 15 minutes from now
                    next_schedule_run = datetime.now() + timedelta(minutes=15)
                    logging.info(f"Schedule set to run next at: {next_schedule_run.strftime('%Y-%m-%d %H:%M:%S')}") # Log next run time
                elif (current_artist_info, next_artist_info) == ( (None, None), (None, None) ):
                     # XML modified but parsing failed or file was empty/invalid
                     logging.warning("XML file modified, but failed to read artist info. Check XML content.")
                     last_modified_time = current_modified_time # Update time to prevent re-processing bad file immediately
                else:
                     # File modification detected, but artist data hasn't changed. Update timestamp.
                     # logging.debug("XML file modified, but artist data unchanged.") # Optional debug log
                     last_modified_time = current_modified_time


            # Check if it's time to run the schedule
            if next_schedule_run and current_time >= next_schedule_run:
                # Log before running
                # logging.info("Scheduled time reached.") # Optional log
                run_schedule()
                next_schedule_run = None # Reset schedule

            time.sleep(2) # Check interval

        except Exception as e:
            # Log unexpected errors in the main loop
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error in monitor loop: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr) # Print stack trace for debugging
            time.sleep(10) # Wait longer after an unexpected error

if __name__ == "__main__":
    if not os.path.exists(MP3_DIRECTORY):
        # Use logging for consistency, even for fatal startup errors
        logging.error(f"MP3 directory does not exist: {MP3_DIRECTORY}")
        exit(1)

    logging.info("=" * 50)
    logging.info("Starting Artist Intro Loader script...")
    # Log missing artist file location at startup
    logging.info(f"Missing artists will be logged to: {MISSING_ARTIST_LOG}")
    logging.info(f"Monitoring XML file: {XML_FILE_PATH}")
    logging.info(f"Using MP3 directory: {MP3_DIRECTORY}")
    logging.info("=" * 50)

    # Perform initial check/update
    perform_initial_check()

    # Start monitoring loop
    logging.info("Starting XML monitor loop...")
    print("Press Ctrl+C to stop") # Keep print for direct user feedback

    try:
        monitor_xml_file()
    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user.")
    except Exception as e:
        logging.error(f"Fatal error occurred: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        exit(1)