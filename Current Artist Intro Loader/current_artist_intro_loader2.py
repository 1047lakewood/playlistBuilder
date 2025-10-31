import os
import time
import xml.etree.ElementTree as ET
import shutil
import logging
import urllib.request
from datetime import datetime, timedelta
import random
from pydub import AudioSegment  # Add pydub for MP3 concatenation


# Setup logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# File paths
XML_FILE_PATH = r"G:\To_RDS\nowplaying.xml"  # XML file path
MP3_DIRECTORY = r"G:\Shiurim\introsCleanedUp"
LOG_DIRECTORY = r"G:\Misc\Dev\Current Artist Intro Loader"
CURRENT_ARTIST_FILE = os.path.join(MP3_DIRECTORY, "currentArtist.mp3")
ACTUAL_CURRENT_ARTIST_FILE = os.path.join(MP3_DIRECTORY, "actualCurrentArtist.mp3")
BLANK_MP3_FILE = os.path.join(MP3_DIRECTORY, "blank.mp3")  # Path to a blank MP3 file
SILENT_MP3_FILE = os.path.join(MP3_DIRECTORY, "near_silent.mp3")  # Path to a silent MP3 file
MISSING_ARTIST_LOG = os.path.join(LOG_DIRECTORY, "missing_artists.log")  # New log file for missing artists

# Schedule URL
SCHEDULE_URL = "http://192.168.3.12:9000/?pass=bmas220&action=schedule&type=run&id=TBACFNBGJKOMETDYSQYR"

# Tracking when to run the schedule next
next_schedule_run = None

def log_missing_artist(artist_name, filename, is_current=True):
    """Log missing artist to external log file."""
    try:
        with open(MISSING_ARTIST_LOG, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            artist_type = "Current" if is_current else "Next"
            if is_current and artist_name[0] == "R":
                f.write(f"{artist_type} Artist not found: '{artist_name}', FILENAME: '{filename}'\n")
                logging.info(f"Logged missing {artist_type.lower()} artist '{artist_name}' with filename '{filename}' to log file")
    except Exception as e:
        logging.error(f"Error writing to missing artist log: {e}")

def get_artists_from_xml():
    """Extract the current and next artists' names and filenames from the XML file."""
    try:
        tree = ET.parse(XML_FILE_PATH)
        root = tree.getroot()
        
        # Get the current artist and filename
        current_track_elem = root.find("TRACK")
        current_artist = None
        current_filename = None
        if current_track_elem is not None:
            if "ARTIST" in current_track_elem.attrib:
                current_artist = current_track_elem.attrib["ARTIST"].strip()
                logging.info(f"Found current artist: {current_artist}")
            else:
                logging.warning("Current track artist not found in XML")
                
            if "FILENAME" in current_track_elem.attrib:
                current_filename = current_track_elem.attrib["FILENAME"].strip()
                logging.info(f"Found current filename: {current_filename}")
            else:
                logging.warning("Current track filename not found in XML")
        else:
            logging.warning("Current track element not found in XML")
        
        # Get the next artist and filename
        next_track_elem = root.find("NEXTTRACK/TRACK")
        next_artist = None
        next_filename = None
        if next_track_elem is not None:
            if "ARTIST" in next_track_elem.attrib:
                next_artist = next_track_elem.attrib["ARTIST"].strip()
                logging.info(f"Found next artist: {next_artist}")
            else:
                logging.warning("Next track artist not found in XML")
                
            if "FILENAME" in next_track_elem.attrib:
                next_filename = next_track_elem.attrib["FILENAME"].strip()
                logging.info(f"Found next filename: {next_filename}")
            else:
                logging.warning("Next track filename not found in XML")
        else:
            logging.warning("Next track element not found in XML")
            
        return (current_artist, current_filename), (next_artist, next_filename)
    except Exception as e:
        logging.error(f"Error parsing XML: {e}")
        return (None, None), (None, None)

def concatenate_mp3_files(files, output_path):
    """Concatenate multiple MP3 files into a single file."""
    try:
        if not files:
            logging.error("No files provided for concatenation")
            return False
            
        # Check if all files exist
        for file_path in files:
            if not os.path.exists(file_path):
                logging.error(f"File for concatenation not found: {file_path}")
                return False
                
        combined = AudioSegment.empty()
        for file_path in files:
            sound = AudioSegment.from_mp3(file_path)
            combined += sound
            
        combined.export(output_path, format="mp3")
        logging.info(f"Successfully concatenated {len(files)} MP3 files to {output_path}")
        return True
    except Exception as e:
        logging.error(f"Error concatenating MP3 files: {e}")
        return False

def update_artist_files(current_artist_info, next_artist_info):
    """Update the currentArtist.mp3 and actualCurrentArtist.mp3 files."""
    success = True
    current_artist, current_filename = current_artist_info
    next_artist, next_filename = next_artist_info
    current_artist_file_no_path = ""
    # Handle actualCurrentArtist.mp3 (current artist) - keep this unchanged
    if current_artist:
        # Get all MP3 files in the directory that start with current_artist
        matching_files = [file for file in os.listdir(MP3_DIRECTORY) 
                        if file.startswith(f"{current_artist}") and file.lower().endswith(".mp3")]

        # If there are matching files, choose one randomly
        if matching_files:
            random_file = random.choice(matching_files)
            current_artist_file = os.path.join(MP3_DIRECTORY, random_file)
            current_artist_file_no_path = random_file
        else:
            # Fallback to the default if no matching files
            current_artist_file = os.path.join(MP3_DIRECTORY, f"{current_artist}.mp3")
            current_artist_file_no_path =  f"{current_artist}.mp3"

        if os.path.exists(current_artist_file):
            try:
                shutil.copy2(current_artist_file, ACTUAL_CURRENT_ARTIST_FILE)
                logging.info(f"Successfully copied {current_artist_file_no_path} to actualCurrentArtist.mp3")
            except Exception as e:
                logging.error(f"Error copying current artist file: {e}")
                success = False
        else:
            logging.warning(f"Current artist file not found: {current_artist_file}")
            # Log missing artist to external file
            log_missing_artist(current_artist, current_filename, is_current=True)
            
            # Since current artist file doesn't exist, use blank.mp3 instead
            if os.path.exists(BLANK_MP3_FILE):
                try:
                    shutil.copy2(BLANK_MP3_FILE, ACTUAL_CURRENT_ARTIST_FILE)
                    logging.info(f"Current artist file '{current_artist}.mp3' not found, using blank.mp3 for actualCurrentArtist.mp3 instead")
                except Exception as e:
                    logging.error(f"Error copying blank MP3 file to actualCurrentArtist.mp3 when artist file not found: {e}")
                    success = False
            else:
                logging.warning(f"Blank MP3 file not found: {BLANK_MP3_FILE}")
                # Fall back to creating an empty file if blank.mp3 doesn't exist
                try:
                    open(ACTUAL_CURRENT_ARTIST_FILE, 'wb').close()
                    logging.info("Created empty actualCurrentArtist.mp3 as both artist file and blank.mp3 not found")
                except Exception as e:
                    logging.error(f"Error creating empty actualCurrentArtist.mp3: {e}")
                    success = False
    else:
        logging.warning("No current artist found in XML, using blank.mp3 for actualCurrentArtist.mp3")
        if current_filename:
            log_missing_artist("None", current_filename, is_current=True)
        
        # Copy blank MP3 file to actualCurrentArtist.mp3 if current_artist is None
        if os.path.exists(BLANK_MP3_FILE):
            try:
                shutil.copy2(BLANK_MP3_FILE, ACTUAL_CURRENT_ARTIST_FILE)
                logging.info("Successfully copied blank.mp3 to actualCurrentArtist.mp3 as no current artist found")
            except Exception as e:
                logging.error(f"Error copying blank MP3 file to actualCurrentArtist.mp3: {e}")
                success = False
        else:
            logging.warning(f"Blank MP3 file not found: {BLANK_MP3_FILE}")
            # Fall back to creating an empty file if blank.mp3 doesn't exist
            try:
                open(ACTUAL_CURRENT_ARTIST_FILE, 'wb').close()
                logging.info("Created empty actualCurrentArtist.mp3 as blank.mp3 not found")
            except Exception as e:
                logging.error(f"Error creating empty actualCurrentArtist.mp3: {e}")
                success = False
    
    # Handle currentArtist.mp3 (next artist) - add silent.mp3 before and after
    if next_artist:
        # Get all MP3 files in the directory that start with next_artist
        matching_files = [file for file in os.listdir(MP3_DIRECTORY) 
                        if file.startswith(f"{next_artist}") and file.lower().endswith(".mp3")]

        # If there are matching files, choose one randomly
        if matching_files:
            random_file = random.choice(matching_files)
            next_artist_file = os.path.join(MP3_DIRECTORY, random_file)
        else:
            # Fallback to the default if no matching files
            next_artist_file = os.path.join(MP3_DIRECTORY, f"{next_artist}.mp3")

        if os.path.exists(next_artist_file):
            # Check if silent.mp3 exists
            if os.path.exists(SILENT_MP3_FILE):
                try:
                    # Create concatenated MP3 with silent.mp3 before and after
                    concatenate_mp3_files(
                        [SILENT_MP3_FILE, next_artist_file, SILENT_MP3_FILE], 
                        CURRENT_ARTIST_FILE
                    )
                    logging.info(f"Created concatenated MP3 (silent + {next_artist} + silent) for currentArtist.mp3")
                except Exception as e:
                    logging.error(f"Error creating concatenated MP3 file: {e}")
                    # Fallback to just copying the next artist file if concatenation fails
                    try:
                        shutil.copy2(next_artist_file, CURRENT_ARTIST_FILE)
                        logging.info(f"Fallback: Copied {next_artist}.mp3 to currentArtist.mp3 after concatenation failed")
                    except Exception as e2:
                        logging.error(f"Error in fallback copy: {e2}")
                        success = False
            else:
                logging.warning(f"Silent MP3 file not found: {SILENT_MP3_FILE}, using just the artist file")
                try:
                    shutil.copy2(next_artist_file, CURRENT_ARTIST_FILE)
                    logging.info(f"Copied {next_artist}.mp3 to currentArtist.mp3 (silent.mp3 not found)")
                except Exception as e:
                    logging.error(f"Error copying next artist file: {e}")
                    success = False
        else:
            logging.warning(f"Next artist file not found: {next_artist_file}")
            # Log missing artist to external file
            log_missing_artist(next_artist, next_filename, is_current=False)
            
            # Copy blank MP3 file instead of creating an empty file
            if os.path.exists(BLANK_MP3_FILE):
                try:
                        shutil.copy2(BLANK_MP3_FILE, CURRENT_ARTIST_FILE)
                        logging.info("Copied blank.mp3 to currentArtist.mp3")
                except Exception as e:
                    logging.error(f"Error handling blank MP3 file: {e}")
                    success = False
            else:
                logging.warning(f"Blank MP3 file not found: {BLANK_MP3_FILE}")
                # Fall back to creating an empty file if blank.mp3 doesn't exist
                try:
                    open(CURRENT_ARTIST_FILE, 'wb').close()
                    logging.info("Created empty currentArtist.mp3 as blank.mp3 not found")
                except Exception as e:
                    logging.error(f"Error creating empty currentArtist.mp3: {e}")
                    success = False
    else:
        # Handle no next artist case
        if next_filename:
            log_missing_artist("None", next_filename, is_current=False)
            
        if os.path.exists(BLANK_MP3_FILE):
            try:
                
                shutil.copy2(BLANK_MP3_FILE, CURRENT_ARTIST_FILE)
                logging.info("Copied blank.mp3 to currentArtist.mp3 as no next artist found ")
            except Exception as e:
                logging.error(f"Error handling no next artist case: {e}")
                success = False
        else:
            logging.warning(f"Blank MP3 file not found: {BLANK_MP3_FILE}")
            # Fall back to creating an empty file if blank.mp3 doesn't exist
            try:
                open(CURRENT_ARTIST_FILE, 'wb').close()
                logging.info("Created empty currentArtist.mp3 as blank.mp3 not found")
            except Exception as e:
                logging.error(f"Error creating empty currentArtist.mp3: {e}")
                success = False
            
    return success

def run_schedule():
    """Run the schedule URL."""
    try:
        logging.info(f"Running schedule URL: {SCHEDULE_URL}")
        response = urllib.request.urlopen(SCHEDULE_URL)
        logging.info(f"Schedule response: {response.status}")
        return True
    except Exception as e:
        logging.error(f"Error running schedule: {e}")
        return False

def monitor_xml_file():
    """Monitor the XML file for changes and update artist files accordingly."""
    global next_schedule_run
    
    last_modified_time = 0
    if os.path.exists(XML_FILE_PATH):
        last_modified_time = os.path.getmtime(XML_FILE_PATH)
        logging.info(f"XML file exists, last modified at {datetime.fromtimestamp(last_modified_time).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logging.warning(f"XML file {XML_FILE_PATH} does not exist at startup")
    
    logging.info("Starting XML monitor")
    logging.info(f"Using MP3 directory: {MP3_DIRECTORY}")
    logging.info(f"Using blank MP3 file: {BLANK_MP3_FILE}")
    logging.info(f"Using silent MP3 file: {SILENT_MP3_FILE}")
    logging.info(f"Missing artist log file: {MISSING_ARTIST_LOG}")
    
    # Check if required files exist at startup
    if not os.path.exists(BLANK_MP3_FILE):
        logging.warning(f"Blank MP3 file {BLANK_MP3_FILE} does not exist at startup, this may cause issues")
    if not os.path.exists(SILENT_MP3_FILE):
        logging.warning(f"Silent MP3 file {SILENT_MP3_FILE} does not exist at startup, this may cause issues")
    
    while True:
        try:
            current_time = datetime.now()
            
            # Check if XML file exists
            if not os.path.exists(XML_FILE_PATH):
                logging.warning("XML file not found. Waiting...")
                time.sleep(5)
                continue
                
            # Check if XML file has been modified
            current_modified_time = os.path.getmtime(XML_FILE_PATH)
            
            if current_modified_time > last_modified_time:
                logging.info(f"XML file modified at {datetime.fromtimestamp(current_modified_time).strftime('%Y-%m-%d %H:%M:%S')}, updating artist files")
                last_modified_time = current_modified_time
                
                # Get artists and update files
                current_artist_info, next_artist_info = get_artists_from_xml()
                logging.info(f"current artist: {current_artist_info[0]}, next artist: {next_artist_info[0]}")
                logging.info(f"current filename: {current_artist_info[1]}, next filename: {next_artist_info[1]}")
                logging.info(f"Waiting 10 seconds")
                time.sleep(10)  # Wait a bit to ensure XML is fully updated
                
                success = update_artist_files(current_artist_info, next_artist_info)
                
                if success:
                    logging.info("Successfully updated all artist files")
                else:
                    logging.warning("One or more errors occurred while updating artist files")
                
                # Set schedule to run 15 minutes from now
                next_schedule_run = current_time + timedelta(minutes=15)
                logging.info(f"Schedule will run at: {next_schedule_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check if it's time to run the schedule
            if next_schedule_run and current_time >= next_schedule_run:
                logging.info("15 minutes have passed since last XML change, running schedule")
                run_schedule()
                next_schedule_run = None  # Reset the schedule time after running
            
            # Wait before checking again
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"Error in monitor loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Make sure the directory exists
    if not os.path.exists(MP3_DIRECTORY):
        logging.error(f"MP3 directory does not exist: {MP3_DIRECTORY}")
        print(f"Error: MP3 directory does not exist: {MP3_DIRECTORY}")
        exit(1)
    
    # Log startup information
    logging.info("=" * 50)
    logging.info(f"Starting XML monitoring script - version 1.3")
    logging.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"XML file path: {XML_FILE_PATH}")
    logging.info(f"MP3 directory: {MP3_DIRECTORY}")
    logging.info(f"Current artist file: {CURRENT_ARTIST_FILE}")
    logging.info(f"Actual current artist file: {ACTUAL_CURRENT_ARTIST_FILE}")
    logging.info(f"Blank MP3 file: {BLANK_MP3_FILE}")
    logging.info(f"Silent MP3 file: {SILENT_MP3_FILE}")
    logging.info(f"Missing artist log file: {MISSING_ARTIST_LOG}")
    logging.info(f"Schedule URL: {SCHEDULE_URL}")
    logging.info("=" * 50)
        
    # Start monitoring
    print(f"Starting to monitor {XML_FILE_PATH}")
    print(f"Logs will be output to console")
    print(f"Missing artists will be logged to {MISSING_ARTIST_LOG}")
    print("Press Ctrl+C to stop")
    
    try:
        monitor_xml_file()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        logging.info("Monitoring stopped by user")
    except Exception as e:
        error_msg = f"Fatal error occurred: {e}"
        print(f"Error: {error_msg}")
        logging.error(error_msg)
        exit(1)