#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_manager import ConfigManager

config = ConfigManager()

print("Before fix:")
rds_xml = config.get_setting('settings.rds.now_playing_xml', 'NOT_FOUND')
intro_xml = config.get_setting('settings.intro_loader.now_playing_xml', 'NOT_FOUND')
print(f"  RDS XML: {rds_xml}")
print(f"  Intro XML: {intro_xml}")

# Update Intro Loader to use test file (same as RDS)
test_xml_path = r'G:\To_RDS\nowplaying_test.xml'
config.update_setting('settings.intro_loader.now_playing_xml', test_xml_path)
config.save_config()

print("After fix:")
intro_xml = config.get_setting('settings.intro_loader.now_playing_xml', 'NOT_FOUND')
print(f"  Intro XML: {intro_xml}")
print(f"  Both using test file: {intro_xml == test_xml_path}")
