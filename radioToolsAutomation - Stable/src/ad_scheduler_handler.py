import time
import logging
import threading
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from lecture_detector import LectureDetector
from ad_inserter_service import AdInserterService

# Logger will be set in __init__ based on station_id

# Constants
LOOP_SLEEP = 60  # Check every minute
HOUR_CHECK_INTERVAL = 3600  # Check for hour boundaries every hour
TRACK_CHANGE_CHECK_INTERVAL = 5  # Check for track changes every 5 seconds
ERROR_RETRY_DELAY = 300  # 5 minutes after errors

class AdSchedulerHandler:
    """Intelligent ad scheduler that runs ads based on lecture detection and timing."""

    def __init__(self, log_queue, config_manager, station_id):
        """
        Initialize the AdScheduler handler.

        Args:
            log_queue: Log queue for logging
            config_manager: ConfigManager instance
            station_id: Station identifier (e.g., 'station_1047' or 'station_887')
        """
        # Set up logger based on station_id
        logger_name = f'AdScheduler_{station_id.split("_")[1]}'  # e.g., 'AdScheduler_1047'
        self.logger = logging.getLogger(logger_name)

        self.logger.info("AdSchedulerHandler __init__ called")
        self.config_manager = config_manager
        self.station_id = station_id
        self.running = False
        self.thread = None
        self.last_hour_checked = datetime.now().hour  # Track the last hour we checked
        self.last_track_check = time.time()  # Initialize to current time
        self.last_file_modification = 0  # Track file modification time
        self.last_seen_track = None  # Track the last seen track for change detection
        self.waiting_for_track_boundary = False
        self.pending_lecture_check = False
        self.logger.debug(f"AdSchedulerHandler initialized with running={self.running}")

        # Initialize components
        self.lecture_detector = None
        self.ad_service = None
        self.reload_components()

        self.logger.info("AdSchedulerHandler initialized successfully.")
        self.logger.debug(f"Initial state: running={self.running}, last_hour_checked={self.last_hour_checked}")

    def reload_configuration(self):
        """Reload configuration settings from config manager."""
        try:
            self.reload_components()
            self.logger.info(f"AdScheduler configuration reloaded for {self.station_id}")
        except Exception as e:
            self.logger.error(f"Failed to reload AdScheduler configuration: {e}")
            raise

    def reload_components(self):
        """Reload configuration-dependent components."""
        try:
            # Get XML path from config
            xml_path = self.config_manager.get_station_setting(self.station_id, "settings.intro_loader.now_playing_xml", r"G:\To_RDS\nowplaying.xml")
            self.logger.debug(f"Using XML path: {xml_path}")

            # Initialize lecture detector
            try:
                self.lecture_detector = LectureDetector(xml_path, self.config_manager, self.station_id)
                self.logger.debug("Lecture detector initialized successfully.")
            except Exception as e:
                self.logger.error(f"Failed to initialize lecture detector: {e}")
                self.lecture_detector = None

            # Initialize ad service
            try:
                self.logger.debug("Attempting to initialize AdInserterService...")
                self.ad_service = AdInserterService(self.config_manager, self.station_id)
                self.logger.debug("Ad service initialized successfully.")
            except ImportError as e:
                self.logger.error(f"Import error initializing ad service: {e}")
                self.logger.error("AdPlayLogger import failed - this may be expected if dependencies are missing")
                self.ad_service = None
            except Exception as e:
                self.logger.error(f"Failed to initialize ad service: {e}")
                self.logger.error(f"Error type: {type(e).__name__}")
                self.ad_service = None

            if self.lecture_detector and self.ad_service:
                self.logger.debug("AdScheduler components reloaded successfully.")
            else:
                self.logger.warning("Some AdScheduler components failed to initialize - handler may not function properly.")
        except Exception as e:
            self.logger.error(f"Error reloading AdScheduler components: {e}")
            self.logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            # Don't raise - allow handler to continue with partial functionality

    def run(self):
        """Main scheduler loop."""
        self.logger.info("AdScheduler handler run() method called!")
        self.running = True  # Set running state when run() starts
        self.logger.info(f"AdScheduler handler {self.station_id} started in thread: {threading.current_thread().name}")
        self.logger.info("AdScheduler handler started.")
        self.logger.debug("AdScheduler run() method executing in thread")
        
        # Log initial configuration
        ads = self.config_manager.get_station_ads(self.station_id) or []
        self.logger.info(f"AdScheduler for {self.station_id} found {len(ads)} ads in configuration")
        for ad in ads:
            self.logger.info(f"  Ad: {ad.get('Name')} - Enabled: {ad.get('Enabled')} - Scheduled: {ad.get('Scheduled')} - Days: {ad.get('Days')} - Hours: {len(ad.get('Hours', []))} hours")
        
        iteration_count = 0

        try:
            self.logger.debug(f"Starting main loop. Running state: {self.running}")
            while self.running:
                try:
                    iteration_count += 1
                    current_hour = datetime.now().hour

                    # Check if we've crossed into a new hour
                    if current_hour != self.last_hour_checked:
                        self.logger.info(f"New hour detected: {current_hour}:00 (was {self.last_hour_checked}:00)")
                        try:
                            self._perform_hourly_check()
                            self.last_hour_checked = current_hour
                            self.logger.info(f"Hourly check completed for hour {current_hour}")
                        except Exception as e:
                            self.logger.error(f"Error in hourly check: {e}")
                            # Update last_hour_checked to avoid immediate retry
                            self.last_hour_checked = current_hour

                    # Check for track changes (if we have components and are waiting for track boundary)
                    current_time = time.time()
                    time_since_track_check = current_time - self.last_track_check
                    if (time_since_track_check >= TRACK_CHANGE_CHECK_INTERVAL and
                        self.lecture_detector and self.ad_service and
                        (self.waiting_for_track_boundary or self.pending_lecture_check)):
                        self.logger.debug(f"Track change check triggered after {time_since_track_check:.1f}s")
                        try:
                            self._check_for_track_change()
                            self.last_track_check = current_time
                        except Exception as e:
                            self.logger.error(f"Error in track change check: {e}")
                            # Reset last_track_check to avoid immediate retry
                            self.last_track_check = current_time

                    # Calculate sleep time: minimum of time until next hour boundary or track check interval
                    seconds_until_next_hour = self._seconds_until_next_hour()
                    # Add a 2-second buffer to ensure we wake up after the hour boundary has been crossed
                    sleep_until_hour = max(0, seconds_until_next_hour + 2)

                    # Calculate time until next track check
                    time_until_track_check = max(0, TRACK_CHANGE_CHECK_INTERVAL - time_since_track_check)

                    # Sleep for the minimum of these times, but at least 1 second
                    sleep_time = min(sleep_until_hour, time_until_track_check, 60)  # Cap at 60 seconds as safety
                    sleep_time = max(sleep_time, 1)  # Minimum 1 second sleep

                    self.logger.debug(f"Sleeping for {sleep_time:.1f}s (next hour in {seconds_until_next_hour:.1f}s, next track check in {time_until_track_check:.1f}s)")
                    time.sleep(sleep_time)

                except Exception as e:
                    self.logger.error(f"Error in AdScheduler main loop iteration {iteration_count}: {e}")
                    self.logger.error(f"Error type: {type(e).__name__}")
                    self.logger.info(f"Retrying in {ERROR_RETRY_DELAY} seconds...")
                    time.sleep(ERROR_RETRY_DELAY)

        except KeyboardInterrupt:
            self.logger.info("AdScheduler handler interrupted.")
        except Exception as e:
            self.logger.error(f"Fatal error in AdScheduler handler: {e}")
        finally:
            self.logger.info(f"AdScheduler handler stopped after {iteration_count} iterations.")

    def _check_for_track_change(self):
        """Check if the current track has changed and perform lecture detection if needed."""
        try:
            if not self.lecture_detector:
                self.logger.warning("Lecture detector not available - skipping track change check.")
                return

            # Check file modification time first
            current_modification = os.path.getmtime(self.lecture_detector.xml_path) if os.path.exists(self.lecture_detector.xml_path) else 0
            file_changed = current_modification != self.last_file_modification

            self.logger.debug(f"File modification time: {current_modification}, last: {self.last_file_modification}, changed: {file_changed}")

            if file_changed:
                self.last_file_modification = current_modification
                self.logger.debug("XML file has been modified - forcing refresh and recheck.")

            # Force refresh the XML file to avoid caching issues
            self.lecture_detector.force_refresh()

            # Get current track info
            current_track_info = self.lecture_detector.get_current_track_info()
            current_track_id = f"{current_track_info.get('artist', '')} - {current_track_info.get('title', '')}"

            self.logger.debug(f"Current track ID: '{current_track_id}'")
            self.logger.debug(f"Last seen track ID: '{self.last_seen_track}'")

            # Check if track has changed (either file changed or track content changed)
            track_content_changed = current_track_id != self.last_seen_track
            if file_changed or track_content_changed:
                self.logger.info(f"Track changed from '{self.last_seen_track}' to '{current_track_id}'")
                self.last_seen_track = current_track_id

                # If we were waiting for a track boundary, check the new track
                if self.waiting_for_track_boundary or self.pending_lecture_check:
                    self.logger.info("Track boundary detected - re-evaluating with new track.")
                    # Don't reset waiting flag yet - let the check decide
                    
                    # Re-run lecture check which will:
                    # 1. Check safety margin (< 3 min? play now)
                    # 2. Check if new current track ends this hour
                    #    - If NO -> run instant immediately
                    #    - If YES -> check if next is lecture:
                    #        * If lecture -> schedule/instant appropriately
                    #        * If NOT lecture -> check time margin and possibly wait AGAIN
                    # This allows recursive waiting through multiple tracks
                    self._perform_lecture_check()
            else:
                self.logger.debug("Track has not changed.")

        except Exception as e:
            self.logger.error(f"Error in track change check: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")

    def _perform_lecture_check(self):
        """
        Perform lecture detection and scheduling logic.
        
        PRIORITY: Ads scheduled for this hour MUST play this hour.
        
        Logic:
        1. Check safety margin: If < 3 min left in hour → Play instantly NOW
        2. Check if current track ends in THIS hour:
           - If NO (ends next hour) → Play instantly
           - If YES (ends this hour):
             a. If next is lecture → Schedule or Instant based on timing
             b. If next is NOT lecture:
                - Check if we'll have safe time after current track ends
                - If YES → Wait for track change
                - If NO → Play instantly now (don't risk waiting)
        """
        try:
            self.logger.debug("Performing lecture check.")

            # Check if components are available
            if not self.lecture_detector:
                self.logger.warning("Lecture detector not available - skipping lecture check.")
                return

            if not self.ad_service:
                self.logger.warning("Ad service not available - skipping lecture check.")
                return

            # SAFETY CHECK: Do we have at least 3 minutes left in this hour?
            try:
                minutes_left = self._minutes_remaining_in_hour()
                self.logger.info(f"Minutes remaining in current hour: {minutes_left:.1f}")
                
                if minutes_left < 3:
                    self.logger.warning(f"Less than 3 minutes left in hour ({minutes_left:.1f}min) - running instant service immediately to ensure ad plays this hour.")
                    self._run_instant_service()
                    self.waiting_for_track_boundary = False
                    self.pending_lecture_check = False
                    return
            except Exception as e:
                self.logger.error(f"Error checking time remaining: {e}")
                # If we can't determine, err on side of caution and play now
                self.logger.warning("Cannot determine time remaining - running instant service to be safe.")
                self._run_instant_service()
                self.waiting_for_track_boundary = False
                self.pending_lecture_check = False
                return

            # Check if current track will end within this hour
            try:
                current_ends_this_hour = self._current_track_ends_this_hour()
                self.logger.info(f"Current track ends within this hour: {current_ends_this_hour}")
            except Exception as e:
                self.logger.error(f"Error checking current track timing: {e}")
                # On error, assume it ends in next hour and run instant
                current_ends_this_hour = False

            # If current track ends in NEXT hour, run instant immediately
            if not current_ends_this_hour:
                self.logger.info("Current track will end in next hour - running instant service immediately.")
                self._run_instant_service()
                self.waiting_for_track_boundary = False
                self.pending_lecture_check = False
                return

            # Current track ends this hour - check if next track is a lecture
            try:
                next_is_lecture = self._is_next_track_lecture()
                self.logger.debug(f"Next track is lecture: {next_is_lecture}")
            except Exception as e:
                self.logger.error(f"Error checking if next track is lecture: {e}")
                next_is_lecture = False

            if next_is_lecture:
                self.logger.debug("Next track is a lecture - evaluating timing.")

                # Check if it will start within current hour
                try:
                    will_start_within_hour = self._will_lecture_start_within_hour()
                    self.logger.debug(f"Lecture will start within hour: {will_start_within_hour}")
                except Exception as e:
                    self.logger.error(f"Error checking lecture timing: {e}")
                    will_start_within_hour = False

                if will_start_within_hour:
                    self.logger.info("Next lecture will start within current hour - running schedule service.")
                    self._run_schedule_service()
                    self.waiting_for_track_boundary = False
                    self.pending_lecture_check = False
                else:
                    self.logger.info("Next lecture will not start within current hour - running instant service.")
                    self._run_instant_service()
                    self.waiting_for_track_boundary = False
                    self.pending_lecture_check = False
            else:
                self.logger.info("Current track ends this hour but next is not a lecture.")
                
                # Check if we'll still have safe time after current track ends
                try:
                    minutes_after_track = self._minutes_remaining_after_current_track()
                    self.logger.info(f"Minutes remaining after current track ends: {minutes_after_track:.1f}")
                    
                    if minutes_after_track < 3:
                        self.logger.warning(f"Only {minutes_after_track:.1f} minutes left after track - too close! Running instant now.")
                        self._run_instant_service()
                        self.waiting_for_track_boundary = False
                        self.pending_lecture_check = False
                    else:
                        self.logger.info(f"Safe to wait ({minutes_after_track:.1f} min margin) - waiting for track change.")
                        self.waiting_for_track_boundary = True
                        self.pending_lecture_check = True
                except Exception as e:
                    self.logger.error(f"Error calculating remaining time after track: {e}")
                    # If we can't determine, play now to be safe
                    self.logger.warning("Cannot calculate time margin - running instant service to be safe.")
                    self._run_instant_service()
                    self.waiting_for_track_boundary = False
                    self.pending_lecture_check = False

        except Exception as e:
            self.logger.error(f"Error in lecture check: {e}")
            self.logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            # Fallback to instant service on errors - must play this hour!
            try:
                self.logger.warning("Error in lecture check - running instant service as fallback to ensure ad plays.")
                self._run_instant_service()
                self.waiting_for_track_boundary = False
                self.pending_lecture_check = False
            except Exception as e2:
                self.logger.error(f"Failed to run fallback instant service: {e2}")

    def _perform_hourly_check(self):
        """Perform the hourly ad scheduling check."""
        try:
            self.logger.debug("Performing hourly ad scheduling check.")
            self._perform_lecture_check()
        except Exception as e:
            self.logger.error(f"Error in hourly check: {e}")
            self.logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            # Fallback to instant service on errors
            try:
                self._run_instant_service()
            except Exception as e2:
                self.logger.error(f"Failed to run fallback instant service: {e2}")

    def _is_next_track_lecture(self):
        """Check if the next track is a lecture."""
        try:
            return self.lecture_detector.is_next_track_lecture()
        except Exception as e:
            self.logger.error(f"Error checking if next track is lecture: {e}")
            return False

    def _parse_duration_to_seconds(self, duration_str):
        """
        Parse duration string to seconds.
        Supports formats: "MM:SS" or "H:MM:SS"
        
        Args:
            duration_str: Duration string like "05:30" or "1:05:30"
            
        Returns:
            int: Duration in seconds, or None if parsing fails
        """
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:  # MM:SS format
                minutes, seconds = map(int, parts)
                duration_seconds = minutes * 60 + seconds
            elif len(parts) == 3:  # H:MM:SS format
                hours, minutes, seconds = map(int, parts)
                duration_seconds = hours * 3600 + minutes * 60 + seconds
            else:
                self.logger.error(f"Unexpected duration format: {duration_str}")
                return None
            
            self.logger.debug(f"Parsed duration '{duration_str}' to {duration_seconds} seconds")
            return duration_seconds
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Failed to parse duration '{duration_str}': {e}")
            return None

    def _minutes_remaining_in_hour(self):
        """
        Calculate how many minutes are left in the current hour.

        Returns:
            float: Minutes remaining until the end of the current hour
        """
        current_time = datetime.now()
        current_hour_end = current_time.replace(minute=59, second=59, microsecond=999999)
        seconds_remaining = (current_hour_end - current_time).total_seconds()
        minutes_remaining = seconds_remaining / 60.0
        return minutes_remaining

    def _seconds_until_next_hour(self):
        """
        Calculate how many seconds until the next hour boundary.

        Returns:
            float: Seconds until the next hour starts (00:00)
        """
        current_time = datetime.now()
        next_hour_start = (current_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        seconds_until_next_hour = (next_hour_start - current_time).total_seconds()
        return seconds_until_next_hour

    def _minutes_remaining_after_current_track(self):
        """
        Calculate how many minutes will be left in the hour after the current track ends.
        
        Returns:
            float: Minutes remaining in hour after current track ends
        """
        current_time = datetime.now()
        
        # Get current track duration
        current_duration = self.lecture_detector.get_current_track_duration()
        if not current_duration:
            self.logger.warning("Could not get current track duration")
            return 0
        
        # Parse duration
        duration_seconds = self._parse_duration_to_seconds(current_duration)
        if duration_seconds is None:
            return 0
        
        # Get track start time
        current_start_time = self._get_current_track_start_time()
        if not current_start_time:
            self.logger.warning("Could not get current track start time")
            return 0
        
        # Calculate when track will end
        track_end_time = current_start_time + timedelta(seconds=duration_seconds)
        
        # Calculate hour end
        current_hour_end = current_time.replace(minute=59, second=59, microsecond=999999)
        
        # Calculate remaining time
        seconds_after_track = (current_hour_end - track_end_time).total_seconds()
        minutes_after_track = seconds_after_track / 60.0
        
        return minutes_after_track

    def _current_track_ends_this_hour(self):
        """Check if the current track will end within the current hour."""
        try:
            current_time = datetime.now()
            self.logger.debug(f"Checking if current track ends this hour. Current time: {current_time}")

            # Get current track duration
            current_duration = self.lecture_detector.get_current_track_duration()
            self.logger.debug(f"Current track duration: {current_duration}")
            if not current_duration:
                self.logger.warning("Could not get current track duration.")
                return False

            # Parse duration
            duration_seconds = self._parse_duration_to_seconds(current_duration)
            if duration_seconds is None:
                return False

            # Calculate when current track will end
            current_start_time = self._get_current_track_start_time()
            self.logger.debug(f"Current track start time: {current_start_time}")
            if not current_start_time:
                self.logger.warning("Could not get current track start time.")
                return False

            track_end_time = current_start_time + timedelta(seconds=duration_seconds)
            self.logger.debug(f"Calculated track end time: {track_end_time}")

            # Check if end time is within current hour
            current_hour_end = current_time.replace(minute=59, second=59, microsecond=999999)
            self.logger.debug(f"Current hour ends at: {current_hour_end}")

            ends_this_hour = track_end_time <= current_hour_end
            self.logger.debug(f"Track ends at {track_end_time}, hour ends at {current_hour_end}")
            self.logger.debug(f"Ends this hour: {ends_this_hour}")

            return ends_this_hour

        except Exception as e:
            self.logger.error(f"Error checking if current track ends this hour: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            return False

    def _will_lecture_start_within_hour(self):
        """Check if the next lecture will start within the current hour."""
        try:
            current_time = datetime.now()
            self.logger.debug(f"Current time: {current_time}")

            # Get current track duration
            current_duration = self.lecture_detector.get_current_track_duration()
            self.logger.debug(f"Current track duration: {current_duration}")
            if not current_duration:
                self.logger.warning("Could not get current track duration.")
                return False

            # Parse duration
            duration_seconds = self._parse_duration_to_seconds(current_duration)
            if duration_seconds is None:
                return False

            # Calculate when current track will end
            current_start_time = self._get_current_track_start_time()
            self.logger.debug(f"Current track start time: {current_start_time}")
            if not current_start_time:
                self.logger.warning("Could not get current track start time.")
                return False

            track_end_time = current_start_time + timedelta(seconds=duration_seconds)
            self.logger.debug(f"Calculated track end time: {track_end_time}")

            # Check if end time is within current hour
            current_hour_end = (current_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            self.logger.debug(f"Current hour end: {current_hour_end}")

            within_hour = track_end_time <= current_hour_end
            self.logger.debug(f"Track ends at {track_end_time}, hour ends at {current_hour_end}")
            self.logger.debug(f"Within hour calculation: {track_end_time} <= {current_hour_end} = {within_hour}")

            return within_hour

        except Exception as e:
            self.logger.error(f"Error checking lecture timing: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            return False

    def _get_current_track_start_time(self):
        """Get the start time of the current track from XML."""
        try:
            self.logger.debug(f"Getting current track start time from XML: {self.lecture_detector.xml_path}")

            # Parse the XML to get the STARTED attribute from the TRACK element
            if not os.path.exists(self.lecture_detector.xml_path):
                self.logger.warning(f"XML file not found: {self.lecture_detector.xml_path}")
                return None

            tree = ET.parse(self.lecture_detector.xml_path)
            root = tree.getroot()

            # Find the TRACK element and get its STARTED attribute
            track_element = root.find('TRACK')
            if track_element is None:
                self.logger.warning("TRACK element not found in XML")
                return None

            started_str = track_element.get('STARTED')
            self.logger.debug(f"Found STARTED attribute: {started_str}")
            if not started_str:
                self.logger.warning("STARTED attribute not found in TRACK element")
                return None

            # Parse the datetime string (format: "2025-09-29 11:05:15")
            try:
                start_time = datetime.strptime(started_str, "%Y-%m-%d %H:%M:%S")
                self.logger.debug(f"Parsed start time: {start_time}")
                return start_time
            except ValueError as e:
                self.logger.error(f"Error parsing start time '{started_str}': {e}")
                return None

        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting current track start time: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            return None

    def _run_schedule_service(self):
        """Run the ad service in schedule mode."""
        try:
            if not self.ad_service:
                self.logger.warning("Ad service not available - cannot run schedule service.")
                return

            self.logger.info("Running ad service in schedule mode.")
            success = self.ad_service.run()
            if success:
                self.logger.info("Schedule service completed successfully.")
            else:
                self.logger.warning("Schedule service completed with errors.")
        except Exception as e:
            self.logger.error(f"Error running schedule service: {e}")

    def _run_instant_service(self):
        """Run the ad service in instant mode."""
        try:
            if not self.ad_service:
                self.logger.warning("Ad service not available - cannot run instant service.")
                return

            self.logger.info("Running ad service in instant mode.")
            success = self.ad_service.run_instant()
            if success:
                self.logger.info("Instant service completed successfully.")
            else:
                self.logger.warning("Instant service completed with errors.")
        except Exception as e:
            self.logger.error(f"Error running instant service: {e}")

    def stop(self):
        """Stop the scheduler."""
        self.logger.info("Stopping AdScheduler handler.")
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def start(self):
        """Start the scheduler in a thread."""
        self.logger.info(f"AdScheduler start() called. Current running state: {self.running}")
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True, name="AdSchedulerThread")
            self.logger.info("Starting AdScheduler thread...")
            self.thread.start()
            self.logger.info("AdScheduler handler thread started.")
            self.logger.debug(f"Thread started: {self.thread.is_alive()}")
            self.logger.debug(f"Thread name: {self.thread.name}")
        else:
            self.logger.warning("AdScheduler handler already running.")
