#!/usr/bin/env python3
"""
Debug script to test lecture detection with the provided XML data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import xml.etree.ElementTree as ET
import tempfile
from config_manager import ConfigManager
from lecture_detector import LectureDetector

# Create a temporary XML file with the user's data
xml_content = """<?xml version="1.0" encoding="utf-8"?>
<PLAYER name="RadioBOSS" version="7.1.1.4">
<TRACK ARTIST="Pirchei Agudat Israel" TITLE="07 - Elokim" ALBUM="Ani Ma'amin" YEAR="1980" GENRE="Jewish Music" COMMENT="" FILENAME="G:\\Music\\Approved 10 teives from C documents\\Approved 10 teives 5782 NIGGUNIM 5\\New pirchei\\Elokim yiadeinu pirchei.mp3" DURATION="02:34"  STARTED="2025-09-29 13:13:07" PLAYCOUNT="7" LASTPLAYED="2025-09-29 13:13:07" INTRO="0.00" OUTRO="0.00" LANGUAGE="" RATING="0" BPM="" TAGS="" PUBLISHER="" ALBUMARTIST="" COMPOSER="" COPYRIGHT="" TRACKNUMBER="7" F1="" F2="" F3="" F4="" F5="" CASTTITLE="Pirchei Agudat Israel - 07 - Elokim" LISTENERS="0" LYRICS="" />
<NEXTTRACK><TRACK ARTIST="" TITLE="Bentsion Sheinker Tiskabel" ALBUM="" YEAR="" GENRE="" COMMENT="" FILENAME="G:\\Music\\all 10 Teves music\\Bentsion Sheinker\\תתקבל.mp3" DURATION="02:25"  PLAYCOUNT="5" LASTPLAYED="2025-09-29 13:08:07" INTRO="0.00" OUTRO="0.00" LANGUAGE="" RATING="0" BPM="" TAGS="" PUBLISHER="" ALBUMARTIST="" COMPOSER="" COPYRIGHT="" TRACKNUMBER="" F1="" F2="" F3="" F4="" F5="" LYRICS="" CASTTITLE="Bentsion Sheinker Tiskabel" /></NEXTTRACK>
<PREVTRACK><TRACK ARTIST="Pirchei Agudat Israel" TITLE="07 - Elokim" ALBUM="Ani Ma'amin" YEAR="1980" GENRE="Jewish Music" COMMENT="" FILENAME="G:\\Music\\Approved 10 teives from C documents\\Approved 10 teives 5782 NIGGUNIM 5\\New pirchei\\Elokim yiadeinu pirchei.mp3" DURATION="02:34"  PLAYCOUNT="6" LASTPLAYED="2025-09-29 13:10:55" INTRO="0.00" OUTRO="0.00" LANGUAGE="" RATING="0" BPM="" TAGS="" PUBLISHER="" ALBUMARTIST="" COMPOSER="" COPYRIGHT="" TRACKNUMBER="7" F1="" F2="" F3="" F4="" F5="" LYRICS="" CASTTITLE="Pirchei Agudat Israel - 07 - Elokim" /></PREVTRACK>
</PLAYER>"""

# Create temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
    f.write(xml_content)
    temp_xml_path = f.name

try:
    # Test with ConfigManager
    config_manager = ConfigManager()
    detector = LectureDetector(temp_xml_path, config_manager)

    print("=== LECTURE DETECTION DEBUG ===")
    print(f"XML file: {temp_xml_path}")
    print()

    # Get current track info
    current_info = detector.get_current_track_info()
    print(f"Current track: '{current_info['artist']}' - '{current_info['title']}'")

    # Check if current track is lecture
    current_is_lecture = detector.is_current_track_lecture()
    print(f"Current track is lecture: {current_is_lecture}")
    print()

    # Get next track info manually
    try:
        tree = ET.parse(temp_xml_path)
        root = tree.getroot()
        next_track = root.find('NEXTTRACK/TRACK')
        if next_track is not None:
            next_artist = next_track.get('ARTIST', '').strip()
            next_title = next_track.get('TITLE', '').strip()
            print(f"Next track (raw): '{next_artist}' - '{next_title}'")
        else:
            print("Next track not found in XML")
    except Exception as e:
        print(f"Error parsing next track: {e}")

    # Check if next track is lecture
    next_is_lecture = detector.is_next_track_lecture()
    print(f"Next track is lecture: {next_is_lecture}")
    print()

    # Check blacklist and whitelist
    print("=== CONFIGURATION DEBUG ===")
    print(f"Blacklist: {detector.blacklist}")
    print(f"Whitelist: {detector.whitelist}")
    print()

    # Test the _is_artist_lecture method directly
    print("=== DIRECT ARTIST TEST ===")
    test_artist = ""  # Empty artist like in the XML
    direct_result = detector._is_artist_lecture(test_artist)
    print(f"Direct test with empty artist '': {direct_result}")
    print()

    # Test with "R" artist
    test_r_artist = "Radio Show"
    direct_r_result = detector._is_artist_lecture(test_r_artist)
    print(f"Direct test with 'R' artist '{test_r_artist}': {direct_r_result}")
    print()

    # Test blacklist matching specifically
    print("=== BLACKLIST MATCHING TEST ===")
    blacklist_artists = ["R' Michel Twersky", 'R. Michel Twerski']
    test_artists = [
        "Bentsion Sheinker Tiskabel",
        "bentsion sheinker tiskabel",
        "R' Michel Twersky",
        "r' michel twersky",
        "R. Michel Twerski",
        "r. michel twerski",
        "Pirchei Agudat Israel",
        ""
    ]

    for test_artist in test_artists:
        is_in_blacklist = test_artist.lower() in detector.blacklist
        would_be_lecture = detector._is_artist_lecture(test_artist)
        print(f"'{test_artist}': in_blacklist={is_in_blacklist}, is_lecture={would_be_lecture}")

finally:
    # Clean up temp file
    os.unlink(temp_xml_path)
