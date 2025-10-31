#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import os
from datetime import datetime

xml_path = r'G:\To_RDS\nowplaying_test.xml'
print(f'Checking XML file: {xml_path}')
print(f'File exists: {os.path.exists(xml_path)}')

if os.path.exists(xml_path):
    # Read and display the XML content
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print('=== XML CONTENT ===')
        print(content)

    # Parse and analyze
    tree = ET.parse(xml_path)
    root = tree.getroot()

    print()
    print('=== TRACK ANALYSIS ===')

    # Current track
    track = root.find('TRACK')
    if track is not None:
        artist = track.get('ARTIST', '')
        title = track.get('TITLE', '')
        print(f'Current: "{artist}" - "{title}"')
        print(f'  Artist starts with R: {artist.lower().startswith("r") if artist else False}')

    # Next track
    next_track = root.find('NEXTTRACK/TRACK')
    if next_track is not None:
        next_artist = next_track.get('ARTIST', '')
        next_title = next_track.get('TITLE', '')
        print(f'Next: "{next_artist}" - "{next_title}"')
        print(f'  Next artist starts with R: {next_artist.lower().startswith("r") if next_artist else False}')
        print(f'  Next artist is empty: {not next_artist.strip()}')
    else:
        print('Next track not found in XML')

    # Check file modification time
    mod_time = os.path.getmtime(xml_path)
    print(f'File last modified: {datetime.fromtimestamp(mod_time)}')
else:
    print('XML file not found!')
