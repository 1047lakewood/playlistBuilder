#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lecture_detector import LectureDetector
from config_manager import ConfigManager

config = ConfigManager()
detector = LectureDetector(r'G:\To_RDS\nowplaying.xml', config)

print("=== CURRENT LECTURE DETECTION STATUS ===")
current_info = detector.get_current_track_info()
print(f"Current track: '{current_info['artist']}' - '{current_info['title']}'")
print(f"Current is lecture: {detector.is_current_track_lecture()}")

print(f"Next is lecture: {detector.is_next_track_lecture()}")

print()
print("Blacklist:", detector.blacklist)
print("Whitelist:", detector.whitelist)
