import xml.etree.ElementTree as ET
import logging
import os
from config_manager import ConfigManager

class LectureDetector:
    """Detects whether tracks are lectures based on artist names and configurable rules.
    
    This class analyzes XML track data to determine if the current playing track
    or the next upcoming track should be classified as a lecture.
    
    Methods:
        - is_current_track_lecture(): Check if the currently playing track is a lecture
        - is_next_track_lecture(): Check if the next upcoming track is a lecture
        - get_current_track_info(): Get artist and title of current track
        - get_current_track_duration(): Get duration of current track
        - get_next_track_duration(): Get duration of next track
    """

    def __init__(self, xml_path, config_manager=None, station_id=None, blacklist=None, whitelist=None):
        """Initialize the LectureDetector.
        
        Args:
            xml_path (str): Path to the XML file containing track information
            config_manager (ConfigManager, optional): Configuration manager for blacklist/whitelist
            station_id (str, optional): Station identifier for station-specific config (not currently used, whitelist/blacklist are shared)
            blacklist (list, optional): List of artists to always classify as lectures
            whitelist (list, optional): List of artists to never classify as lectures
        """
        self.xml_path = xml_path
        self.config_manager = config_manager
        self.station_id = station_id  # Store for future use, but whitelist/blacklist are shared
        
        # Initialize blacklist and whitelist (case-insensitive) - these are shared across stations
        if config_manager:
            self.blacklist = set(x.lower() for x in config_manager.get_shared_blacklist())
            self.whitelist = set(x.lower() for x in config_manager.get_shared_whitelist())
        else:
            self.blacklist = set(x.lower() for x in blacklist) if blacklist else set()
            self.whitelist = set(x.lower() for x in whitelist) if whitelist else set()

    def is_current_track_lecture(self):
        """Check if the currently playing track is a lecture.
        
        Returns:
            bool: True if current track is a lecture, False otherwise
        """
        return self._is_track_lecture(['TRACK'])

    def is_next_track_lecture(self):
        """Check if the next upcoming track is a lecture.
        
        Returns:
            bool: True if next track is a lecture, False otherwise
        """
        return self._is_track_lecture(['NEXTTRACK', 'TRACK'])

    def _is_track_lecture(self, xml_path):
        """Internal method to check if a track at the given XML path is a lecture.

        Args:
            xml_path (list): List of XML tags to navigate to the track

        Returns:
            bool: True if track is a lecture, False otherwise
        """
        try:
            if not os.path.exists(self.xml_path):
                logging.warning(f"XML file not found: {self.xml_path}")
                return False

            # Force file system refresh - try multiple approaches
            try:
                # Approach 1: Touch the file to update modification time
                current_time = os.path.getmtime(self.xml_path)
                os.utime(self.xml_path, (current_time, current_time))
            except:
                pass

            # Parse with explicit encoding to avoid caching issues
            with open(self.xml_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the content directly instead of using ET.parse() which might cache
            root = ET.fromstring(content)
            artist = self._get_track_artist(root, xml_path)
            return self._is_artist_lecture(artist)

        except ET.ParseError as e:
            logging.error(f"Error parsing XML file ({self.xml_path}): {e}")
            return False
        except Exception as e:
            logging.exception(f"Error while checking for lecture: {e}")
            return False

    def _is_artist_lecture(self, artist):
        """Determine if an artist should be classified as a lecture.
        
        Args:
            artist (str): The artist name to check
            
        Returns:
            bool: True if artist represents a lecture, False otherwise
        """
        if not artist:  # Empty artist name
            return False
        
        artist_lower = artist.lower()
            
        # Whitelist takes precedence - never classify as lecture
        if artist_lower in self.whitelist:
            return False
            
        # Check for lecture indicators
        if artist_lower.startswith('r'):  # Radio show/lecture indicator (case-insensitive)
            return True
            
        # Blacklist - always classify as lecture
        if artist_lower in self.blacklist:
            return True
            
        return False

    def _get_track_artist(self, xml_root, path_list):
        """Extract artist name from XML by following the specified path.
        
        Args:
            xml_root: The root XML element
            path_list (list): List of tag names to navigate (e.g. ['TRACK'] or ['NEXTTRACK', 'TRACK'])
            
        Returns:
            str: The artist name (stripped) or empty string if not found
        """
        current_element = xml_root
        
        # Navigate through the XML path
        for tag in path_list:
            current_element = current_element.find(tag)
            if current_element is None:
                return ""
        
        # Extract and return the artist attribute
        artist = current_element.get("ARTIST", "")
        return artist.strip()

    def update_lists(self):
        """Updates the blacklist and whitelist from the config manager."""
        if self.config_manager:
            self.blacklist = set(x.lower() for x in self.config_manager.get_shared_blacklist())
            self.whitelist = set(x.lower() for x in self.config_manager.get_shared_whitelist())

    def force_refresh(self):
        """Force refresh the XML file reading to avoid caching issues."""
        try:
            # Force file system to update
            if os.path.exists(self.xml_path):
                current_time = os.path.getmtime(self.xml_path)
                os.utime(self.xml_path, (current_time, current_time))
                logging.debug(f"Forced refresh of XML file: {self.xml_path}")
        except Exception as e:
            logging.warning(f"Could not force refresh XML file: {e}")

    def get_current_track_info(self):
        """Returns the current track information from the XML file."""
        try:
            if not os.path.exists(self.xml_path):
                return {"artist": "", "title": ""}

            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            current_track = root.find("TRACK")
            if current_track is not None:
                artist = current_track.get("ARTIST", "").strip()
                title = current_track.findtext("TITLE", "").strip()
                return {"artist": artist, "title": title}
            
            return {"artist": "", "title": ""}

        except ET.ParseError as e:
            logging.error(f"Error parsing XML file ({self.xml_path}): {e}")
            return {"artist": "", "title": ""}
        except Exception as e:
            logging.exception(f"Error getting current track info: {e}")
            return {"artist": "", "title": ""}

    def get_current_track_duration(self):
        """Returns the duration of the current track from the XML file.
        
        Returns:
            str: The duration as a string (e.g., '3:45') or empty string if not found
        """
        return self._get_track_duration(['TRACK'])

    def get_next_track_duration(self):
        """Returns the duration of the next track from the XML file.
        
        Returns:
            str: The duration as a string (e.g., '3:45') or empty string if not found
        """
        return self._get_track_duration(['NEXTTRACK', 'TRACK'])

    def _get_track_duration(self, xml_path):
        """Internal method to extract duration from a track at the given XML path.
        
        Args:
            xml_path (list): List of XML tags to navigate to the track
            
        Returns:
            str: The duration (stripped) or empty string if not found
        """
        try:
            if not os.path.exists(self.xml_path):
                logging.warning(f"XML file not found: {self.xml_path}")
                return ""

            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            current_element = root
            
            # Navigate through the XML path
            for tag in xml_path:
                current_element = current_element.find(tag)
                if current_element is None:
                    return ""
            
            # Extract and return the duration attribute
            duration = current_element.get("DURATION", "").strip()
            return duration

        except ET.ParseError as e:
            logging.error(f"Error parsing XML file ({self.xml_path}): {e}")
            return ""
        except Exception as e:
            logging.exception(f"Error getting track duration: {e}")
            return ""

# Example usage
if __name__ == "__main__":
    # Using ConfigManager (recommended)
    config_manager = ConfigManager()
    detector = LectureDetector(
        xml_path=r"G:\To_RDS\nowplaying.xml",
        config_manager=config_manager
    )
    
    print("🎵 LECTURE DETECTOR - Track Analysis")
    print("=" * 50)
    
    # Get current track info for display
    track_info = detector.get_current_track_info()
    print(f"Current track: {track_info['artist']} - {track_info['title']}")
    print(f"Current duration: {detector.get_current_track_duration()}")
    print()
    
    # Check if CURRENT track is a lecture
    print("📻 CURRENT TRACK Analysis:")
    if detector.is_current_track_lecture():
        print("✅ Currently playing track is a LECTURE")
    else:
        print("❌ Currently playing track is NOT a lecture")
    
    # Check if NEXT track is a lecture
    print("\n⏭️  NEXT TRACK Analysis:")
    if detector.is_next_track_lecture():
        print("✅ Next upcoming track is a LECTURE")
    else:
        print("❌ Next upcoming track is NOT a lecture")
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    print(f"Current track is lecture: {detector.is_current_track_lecture()}")
    print(f"Next track is lecture:    {detector.is_next_track_lecture()}")
    print(f"Current track duration:   {detector.get_current_track_duration()}")
    print(f"Next track duration:      {detector.get_next_track_duration()}")
    
    # Alternative: Create detector with manual blacklist/whitelist
    print("\n💡 Alternative usage with manual lists:")
    detector_manual = LectureDetector(
        xml_path=r"G:\To_RDS\nowplaying.xml",
        blacklist=["Rock Band", "DJ Mix"],
        whitelist=["Classical", "Jazz"]
    )
    print(f"Manual detector - Current track: {detector_manual.is_current_track_lecture()}")
    print(f"Manual detector - Next track:    {detector_manual.is_next_track_lecture()}")
    print(f"Manual detector - Current duration: {detector_manual.get_current_track_duration()}")
    print(f"Manual detector - Next duration:    {detector_manual.get_next_track_duration()}")