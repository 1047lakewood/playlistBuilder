#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lecture_detector import LectureDetector
from config_manager import ConfigManager
import queue

config = ConfigManager()

print("=== CHECKING DETECTOR XML PATHS ===")

# Create a fresh lecture detector with test file
detector = LectureDetector(r'G:\To_RDS\nowplaying_test.xml', config)
print(f"Lecture detector XML path: {detector.xml_path}")

current_info = detector.get_current_track_info()
print(f"Current track from detector: '{current_info['artist']}' - '{current_info['title']}'")
print(f"Next is lecture: {detector.is_next_track_lecture()}")

print()

# Check ad scheduler
log_queue = queue.Queue()
try:
    from ad_scheduler_handler import AdSchedulerHandler
    scheduler = AdSchedulerHandler(log_queue, config)
    detector_path = scheduler.lecture_detector.xml_path if scheduler.lecture_detector else "No detector"
    print(f"Ad scheduler detector XML path: {detector_path}")
except Exception as e:
    print(f"Could not create ad scheduler: {e}")

print()
print("=== CONFIGURATION CHECK ===")
rds_xml = config.get_setting('settings.rds.now_playing_xml', 'NOT_FOUND')
intro_xml = config.get_setting('settings.intro_loader.now_playing_xml', 'NOT_FOUND')
print(f"RDS XML setting: {rds_xml}")
print(f"Intro Loader XML setting: {intro_xml}")
