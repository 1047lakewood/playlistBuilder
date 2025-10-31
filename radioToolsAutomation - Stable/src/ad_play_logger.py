import json
import logging
import os
from datetime import datetime
import threading

# Logger will be set in __init__ based on station_id

class AdPlayLogger:
    """Handles tracking and logging of ad play counts."""

    def __init__(self, config_manager, station_id):
        """
        Initialize the AdPlayLogger.

        Args:
            config_manager: ConfigManager instance to access and update ad configurations
            station_id: Station identifier (e.g., 'station_1047' or 'station_887')
        """
        self.config_manager = config_manager
        self.station_id = station_id

        # Thread safety lock
        self._lock = threading.RLock()

        # Set up logger based on station_id
        logger_name = f'AdPlayLogger_{station_id.split("_")[1]}'  # e.g., 'AdPlayLogger_1047'
        self.logger = logging.getLogger(logger_name)

        # Station-specific statistics file
        station_number = station_id.split("_")[1]  # e.g., '1047' or '887'
        self.ad_stats_file = f"ad_play_statistics_{station_number}.json"

    def record_ad_play(self, ad_name):
        """
        Record that an ad has been played.

        Args:
            ad_name: Name of the ad that was played

        Returns:
            bool: True if successfully recorded, False otherwise
        """
        try:
            # Get current ads configuration
            ads = self.config_manager.get_station_ads(self.station_id)
            if not ads:
                self.logger.warning("No ads found in configuration")
                return False

            # Find the ad by name and update its play count
            ad_found = False
            for ad in ads:
                if ad.get("Name") == ad_name:
                    ad_found = True
                    # Increment play count
                    current_count = ad.get("PlayCount", 0)
                    ad["PlayCount"] = current_count + 1

                    # Update last played timestamp
                    ad["LastPlayed"] = datetime.now().isoformat()

                    self.logger.info(f"Recorded play for ad '{ad_name}': count now {ad['PlayCount']}")
                    break

            if not ad_found:
                self.logger.warning(f"Ad '{ad_name}' not found in configuration")
                return False

            # Save updated configuration
            self.config_manager.set_station_ads(self.station_id, ads)
            self.config_manager.save_config()

            # Also save detailed statistics
            self._save_detailed_stats(ad_name)

            return True

        except Exception as e:
            self.logger.error(f"Error recording ad play for '{ad_name}': {e}")
            return False

    def record_multiple_ad_plays(self, ad_names):
        """
        Record multiple ad plays at once.

        Args:
            ad_names: List of ad names that were played

        Returns:
            Dict mapping ad names to success status
        """
        results = {}
        for ad_name in ad_names:
            results[ad_name] = self.record_ad_play(ad_name)
        return results

    def get_ad_statistics(self):
        """
        Get comprehensive ad play statistics.

        Returns:
            Dict containing ad statistics
        """
        try:
            ads = self.config_manager.get_station_ads(self.station_id)
            stats = {
                "total_ads": len(ads),
                "enabled_ads": sum(1 for ad in ads if ad.get("Enabled", False)),
                "total_plays": sum(ad.get("PlayCount", 0) for ad in ads),
                "ads_with_plays": sum(1 for ad in ads if ad.get("PlayCount", 0) > 0),
                "ad_details": []
            }

            for ad in ads:
                ad_detail = {
                    "name": ad.get("Name", "Unknown"),
                    "enabled": ad.get("Enabled", False),
                    "play_count": ad.get("PlayCount", 0),
                    "last_played": ad.get("LastPlayed"),
                    "mp3_file": ad.get("MP3File", ""),
                    "scheduled": ad.get("Scheduled", False)
                }
                stats["ad_details"].append(ad_detail)

            # Sort by play count (most played first)
            stats["ad_details"].sort(key=lambda x: x["play_count"], reverse=True)

            return stats

        except Exception as e:
            self.logger.error(f"Error getting ad statistics: {e}")
            return {"error": str(e)}

    def reset_all_play_counts(self):
        """
        Reset all ad play counts to zero.

        Returns:
            bool: True if successfully reset, False otherwise
        """
        try:
            ads = self.config_manager.get_station_ads(self.station_id)
            for ad in ads:
                ad["PlayCount"] = 0
                ad["LastPlayed"] = None

            self.config_manager.set_station_ads(self.station_id, ads)
            self.config_manager.save_config()

            self.logger.info("Reset all ad play counts")
            return True

        except Exception as e:
            self.logger.error(f"Error resetting play counts: {e}")
            return False

    def get_most_played_ads(self, limit=10):
        """
        Get the most played ads.

        Args:
            limit: Maximum number of ads to return

        Returns:
            List of ad dictionaries sorted by play count
        """
        stats = self.get_ad_statistics()
        return stats.get("ad_details", [])[:limit]

    def _save_detailed_stats(self, ad_name: str):
        """
        Save detailed play statistics to a separate file for analysis.

        Args:
            ad_name: Name of the ad that was played
        """
        with self._lock:
            try:
                stats_data = {}

                # Load existing stats if file exists
                if os.path.exists(self.ad_stats_file):
                    try:
                        with open(self.ad_stats_file, 'r', encoding='utf-8') as f:
                            stats_data = json.load(f)
                    except json.JSONDecodeError:
                        self.logger.warning("Could not load existing ad statistics file")

                # Ensure structure exists
                if "daily_plays" not in stats_data:
                    stats_data["daily_plays"] = {}
                if "ad_totals" not in stats_data:
                    stats_data["ad_totals"] = {}

                # Update daily stats
                today = datetime.now().strftime("%Y-%m-%d")
                if today not in stats_data["daily_plays"]:
                    stats_data["daily_plays"][today] = {}

                stats_data["daily_plays"][today][ad_name] = \
                    stats_data["daily_plays"][today].get(ad_name, 0) + 1

                # Update total stats
                stats_data["ad_totals"][ad_name] = \
                    stats_data["ad_totals"].get(ad_name, 0) + 1

                # Save updated stats
                with open(self.ad_stats_file, 'w', encoding='utf-8') as f:
                    json.dump(stats_data, f, indent=2, ensure_ascii=False)

            except Exception as e:
                self.logger.error(f"Error saving detailed ad statistics: {e}")

    def get_detailed_stats(self, start_date=None, end_date=None):
        """
        Get detailed play statistics from the stats file, optionally filtered by date range.

        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)

        Returns:
            Dict containing detailed statistics
        """
        try:
            if not os.path.exists(self.ad_stats_file):
                return {"error": "No statistics file found"}

            with open(self.ad_stats_file, 'r', encoding='utf-8') as f:
                all_stats = json.load(f)

            # If no date filtering requested, return all stats
            if not start_date and not end_date:
                return all_stats

            # Filter daily plays by date range
            filtered_stats = {
                "daily_plays": {},
                "ad_totals": all_stats.get("ad_totals", {})
            }

            daily_plays = all_stats.get("daily_plays", {})

            for date_str, ad_plays in daily_plays.items():
                # Check if this date falls within the range
                if self._is_date_in_range(date_str, start_date, end_date):
                    filtered_stats["daily_plays"][date_str] = ad_plays

            return filtered_stats

        except Exception as e:
            self.logger.error(f"Error loading detailed statistics: {e}")
            return {"error": str(e)}

    def get_ad_statistics_filtered(self, start_date=None, end_date=None):
        """
        Get ad play statistics filtered by date range.

        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)

        Returns:
            Dict containing filtered ad statistics
        """
        try:
            # Get filtered detailed stats
            detailed_stats = self.get_detailed_stats(start_date, end_date)

            if "error" in detailed_stats:
                return detailed_stats

            # Calculate statistics from filtered data
            daily_plays = detailed_stats.get("daily_plays", {})
            ad_totals = detailed_stats.get("ad_totals", {})

            # Get current ads for structure
            ads = self.config_manager.get_station_ads(self.station_id)

            # Build ad details with filtered play counts
            ad_details = []
            total_plays = 0
            ads_with_plays = 0

            for ad in ads:
                ad_name = ad.get("Name", "Unknown")
                # Use detailed stats count as the authoritative source
                # Detailed stats track all plays since the system was implemented
                detailed_count = ad_totals.get(ad_name, 0)

                # For date-filtered stats, use detailed stats only
                # For unfiltered stats, also use detailed stats (they're more accurate)
                total_count = detailed_count

                if total_count > 0:
                    ads_with_plays += 1
                    total_plays += total_count

                ad_detail = {
                    "name": ad_name,
                    "enabled": ad.get("Enabled", False),
                    "play_count": total_count,
                    "last_played": ad.get("LastPlayed"),
                    "mp3_file": ad.get("MP3File", ""),
                    "scheduled": ad.get("Scheduled", False)
                }
                ad_details.append(ad_detail)

            # Sort by play count (most played first)
            ad_details.sort(key=lambda x: x["play_count"], reverse=True)

            stats = {
                "total_ads": len(ads),
                "enabled_ads": sum(1 for ad in ads if ad.get("Enabled", False)),
                "total_plays": total_plays,
                "ads_with_plays": ads_with_plays,
                "ad_details": ad_details,
                "date_filter": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "days_filtered": len(daily_plays)
                }
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error getting filtered ad statistics: {e}")
            return {"error": str(e)}

    def _is_date_in_range(self, date_str, start_date, end_date):
        """
        Check if a date string falls within the specified range.

        Args:
            date_str: Date string in YYYY-MM-DD format
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)

        Returns:
            bool: True if date is in range, False otherwise
        """
        try:
            # Parse the date from daily_plays
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Check start date
            if start_date:
                start_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                if date_obj < start_obj:
                    return False

            # Check end date
            if end_date:
                end_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                if date_obj > end_obj:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking date range for {date_str}: {e}")
            return False

    def get_date_range_summary(self, start_date, end_date):
        """
        Get a summary of ad plays within a specific date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dict containing date range summary
        """
        try:
            filtered_stats = self.get_ad_statistics_filtered(start_date, end_date)

            if "error" in filtered_stats:
                return filtered_stats

            # Calculate additional metrics
            daily_plays = self.get_detailed_stats(start_date, end_date).get("daily_plays", {})
            total_days = len(daily_plays)

            summary = {
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_days": total_days
                },
                "ad_performance": filtered_stats,
                "daily_breakdown": {}
            }

            # Calculate daily breakdown
            for date_str, ad_plays in daily_plays.items():
                daily_total = sum(ad_plays.values())
                summary["daily_breakdown"][date_str] = {
                    "total_plays": daily_total,
                    "ad_breakdown": ad_plays
                }

            return summary

        except Exception as e:
            self.logger.error(f"Error getting date range summary: {e}")
            return {"error": str(e)}
