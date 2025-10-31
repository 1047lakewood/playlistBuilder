import os
import logging
import urllib.request
from datetime import datetime

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    PYDUB_AVAILABLE = False

# Logger will be set in __init__ based on station_id

class AdInserterService:
    """Combine enabled/scheduled ads into a single MP3 and trigger insertion."""

    def __init__(self, config_manager, station_id):
        """
        Initialize the AdInserterService.

        Args:
            config_manager: ConfigManager instance
            station_id: Station identifier (e.g., 'station_1047' or 'station_887')
        """
        self.config_manager = config_manager
        self.station_id = station_id

        # Set up logger based on station_id
        logger_name = f'AdService_{station_id.split("_")[1]}'  # e.g., 'AdService_1047'
        self.logger = logging.getLogger(logger_name)
        self.insertion_url = self.config_manager.get_station_setting(
            station_id,
            "settings.ad_inserter.insertion_url",
            "http://localhost:8000/insert",
        )
        self.instant_url = self.config_manager.get_station_setting(
            station_id,
            "settings.ad_inserter.instant_url",
            "http://localhost:8000/play",
        )
        self.output_mp3 = self.config_manager.get_station_setting(
            station_id,
            "settings.ad_inserter.output_mp3",
            r"G:\\Ads\\newAd.mp3",
        )

        # Initialize ad play logger
        try:
            from ad_play_logger import AdPlayLogger
            self.ad_logger = AdPlayLogger(config_manager, station_id)
        except ImportError:
            self.logger.error("AdPlayLogger not available - ad play tracking disabled")
            self.ad_logger = None

    def run(self):
        """Combine ads and call the scheduled insertion URL."""
        if self._combine_ads():
            return self._call_url(self.insertion_url)
        return False

    def run_instant(self):
        """Combine ads and call the instant-play URL."""
        if self._combine_ads():
            return self._call_url(self.instant_url)
        return False

    def _combine_ads(self):
        ads = self.config_manager.get_station_ads(self.station_id) or []
        valid_files = []
        now = datetime.now()
        for ad in ads:
            ad_name = ad.get("Name", "Unknown")
            
            if not ad.get("Enabled", True):
                self.logger.debug(f"Ad '{ad_name}' excluded: not enabled")
                continue
            if not self._is_scheduled(ad, now):
                self.logger.debug(f"Ad '{ad_name}' excluded: not scheduled for current time")
                continue
            mp3 = ad.get("MP3File")
            if not mp3 or not os.path.exists(mp3):
                self.logger.warning(f"Ad '{ad_name}' excluded: MP3 not found: {mp3}")
                continue
            
            self.logger.info(f"Ad '{ad_name}' included in roll")
            valid_files.append(mp3)

        if not valid_files:
            self.logger.warning("No valid ads to combine.")
            return False

        # Log the ads that will be played
        played_ad_names = [ad.get("Name", "Unknown") for ad in ads
                          if ad.get("Enabled", True) and self._is_scheduled(ad, now)]
        self._log_ad_plays(played_ad_names)

        os.makedirs(os.path.dirname(self.output_mp3), exist_ok=True)
        return self._concatenate_mp3_files(valid_files, self.output_mp3)

    def _is_scheduled(self, ad, now):
        ad_name = ad.get("Name", "Unknown")
        
        # If not scheduled, always play (when enabled)
        if not ad.get("Scheduled", False):
            self.logger.debug(f"Ad '{ad_name}': unscheduled, allowing at any time")
            return True
        
        # Check day schedule
        day_name = now.strftime("%A")
        days = ad.get("Days", [])
        if days and day_name not in days:
            self.logger.debug(f"Ad '{ad_name}': scheduled but not for {day_name} (only {days})")
            return False
        
        # Check hour schedule - prioritize Hours (list of ints) over legacy Times (list of dicts)
        hours = ad.get("Hours", [])
        
        if hours:
            # New format: Hours is a list of integers [0, 1, 2, ..., 23]
            if now.hour in hours:
                self.logger.debug(f"Ad '{ad_name}': scheduled and current hour {now.hour} is in Hours list")
                return True
            else:
                self.logger.debug(f"Ad '{ad_name}': scheduled but hour {now.hour} not in Hours list {hours}")
                return False
        
        # Fallback to legacy Times format for backward compatibility
        times = ad.get("Times", [])
        if times:
            hour_match = False
            for t in times:
                if isinstance(t, dict) and "hour" in t:
                    try:
                        if int(t.get("hour")) == now.hour:
                            hour_match = True
                            break
                    except (ValueError, TypeError):
                        continue
            if hour_match:
                self.logger.debug(f"Ad '{ad_name}': scheduled and current hour {now.hour} matches Times (legacy)")
                return True
            else:
                self.logger.debug(f"Ad '{ad_name}': scheduled but hour {now.hour} not in Times list")
                return False
        
        # If scheduled but no hours/times specified, allow at any time
        self.logger.debug(f"Ad '{ad_name}': scheduled with no specific hours, allowing")
        return True

    def _concatenate_mp3_files(self, files, output_path):
        self.logger.debug(f"Concatenating {len(files)} files to {output_path}")
        if not PYDUB_AVAILABLE:
            self.logger.error("pydub not available - cannot concatenate MP3 files")
            return False
        try:
            combined = AudioSegment.empty()
            for fp in files:
                if not os.path.exists(fp):
                    self.logger.error(f"File not found: {fp}")
                    return False
                combined += AudioSegment.from_mp3(fp)
            combined.export(output_path, format="mp3")
            return True
        except Exception as e:  # pragma: no cover - runtime safety
            self.logger.exception(f"Error concatenating ads: {e}")
            return False

    def _call_url(self, url):
        self.logger.info(f"Calling ad service URL: {url}")
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                self.logger.info(f"Ad service response: {resp.status}")
            return True
        except Exception as e:  # pragma: no cover - runtime safety
            self.logger.error(f"Failed to call ad service URL: {e}")
            return False

    def _log_ad_plays(self, ad_names):
        """
        Log that the specified ads have been played.

        Args:
            ad_names: List of ad names that were played
        """
        if not self.ad_logger or not ad_names:
            return

        try:
            results = self.ad_logger.record_multiple_ad_plays(ad_names)
            successful = sum(results.values())
            total = len(results)

            if successful > 0:
                self.logger.info(f"Successfully logged {successful}/{total} ad plays")
                for ad_name, success in results.items():
                    if success:
                        self.logger.debug(f"Ad '{ad_name}' play logged successfully")
                    else:
                        self.logger.warning(f"Failed to log play for ad '{ad_name}'")
            else:
                self.logger.warning("No ad plays were successfully logged")

        except Exception as e:
            self.logger.error(f"Error logging ad plays: {e}")
