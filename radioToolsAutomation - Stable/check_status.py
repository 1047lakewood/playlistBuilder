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
print(f"Blacklist: {detector.blacklist}")
print(f"Whitelist: {detector.whitelist}")

# Test the track change detection logic
test_cases = [
    ('Rav Ezer Shwalbe', 'Current track (starts with R)'),
    ('Avremi Roth', 'Next track (does not start with R)'),
    ('', 'Empty artist'),
    ('Radio Show', 'Generic radio show'),
]

print()
print("=== TEST CASES ===")
for artist, description in test_cases:
    is_lecture = detector._is_artist_lecture(artist)
    starts_with_r = artist.lower().startswith('r') if artist else False
    in_blacklist = artist.lower() in detector.blacklist if artist else False
    print(f"{description}: '{artist}' -> is_lecture={is_lecture} (starts_with_r={starts_with_r}, in_blacklist={in_blacklist})")
