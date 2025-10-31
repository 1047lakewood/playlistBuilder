#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_manager import ConfigManager

config = ConfigManager()
blacklist = config.get_blacklist()
whitelist = config.get_whitelist()

print('Current Blacklist:', blacklist)
print('Current Whitelist:', whitelist)

# Check if Benzion Shenker should be added to blacklist
test_artist = 'Benzion Shenker'
print(f'Testing "{test_artist}":')
print(f'  Starts with R: {test_artist.lower().startswith("r")}')
print(f'  In blacklist: {test_artist.lower() in [x.lower() for x in blacklist]}')
print(f'  In whitelist: {test_artist.lower() in [x.lower() for x in whitelist]}')

# Check what would make it a lecture
print(f'Would be lecture if:')
print(f'  - Artist starts with R: {test_artist.lower().startswith("r")}')
print(f'  - Artist in blacklist: {test_artist.lower() in [x.lower() for x in blacklist]}')

# Show current logic result
from lecture_detector import LectureDetector
detector = LectureDetector(r'G:\To_RDS\nowplaying.xml', config)
is_lecture = detector.is_next_track_lecture()
print(f'Actual result - Next track is lecture: {is_lecture}')
