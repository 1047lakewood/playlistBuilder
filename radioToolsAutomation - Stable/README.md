radioToolsAutomation



 


Overview
radioToolsAutomation is a Python-based desktop application for automating Radio Data System (RDS) messaging and audio intro loading in a radio broadcasting setup. Built with Tkinter for the GUI, it supports message scheduling, artist-based filtering (whitelists/blacklists), lecture detection, and tools for managing missing artist intros and simple M3U8 playlists.

Key components:

AutoRDS Handler: Cycles through configurable messages, replaces placeholders ({artist}, {title}), applies schedules/filters, and sends to RDS encoder.
Intro Loader Handler: Monitors now-playing XML, copies/concatenates MP3 intros, logs missing artists, runs schedules.
Lecture Detector: Classifies tracks as lectures via rules (e.g., artist starts with 'R'), whitelists (non-lectures), blacklists (lectures).
Configuration Manager: JSON-based storage for messages, lists, presets; handles loading/saving/backups.
GUI: Main window with logs/current messages; modals for config, missing artists, options, playlist editor.
The app runs as a background process with a GUI for monitoring/config. Tested on Windows (PowerShell 7.5.1).

Features
RDS Messaging:
Add/edit/delete messages with enable/disable.
Scheduling by days/hours; placeholders for dynamic content.
Filters: Enabled status, placeholders availability, lecture detection.
Rotation with durations; default fallback message.
Intro Management:
XML monitoring for current/next artists.
Random intro selection; concatenation with silence.
Logging missing intros (focus on 'R' starting artists).
Scheduled URL triggers.
Artist Filtering:
Whitelist: Never treat as lecture.
Blacklist: Always treat as lecture.
Rule: Artists starting with 'R' are lectures (unless whitelisted).
Playlist Editor:
Preset-based M3U8 editing (add/remove files).
Browse addition; save to file.
Ad Services:
Combine scheduled ads into one MP3 and send to a schedule URL.
Instant ad option for immediate playback via a separate URL.
Debug/Testing:
XML "touch" to force checks.
Bug reproduction scripts; integration tests.
Installation
Prerequisites:
Python 3.8+ (tested on 3.12.3).
Windows OS.
Dependencies: Install via pip install -r requirements.txt (create if needed; includes tkinter, ttkthemes, pydub, xml.etree.ElementTree, etc.).
Core: tkinter, ttkthemes.
Audio: pydub (requires FFmpeg installed).
Other: logging, threading, queue, os, datetime, socket, urllib, shutil, random, re, subprocess, platform.
Clone Repository:
text

Collapse

Wrap
git clone https://github.com/your-repo/radioToolsAutomation.git
cd radioToolsAutomation
Setup:
Ensure paths (e.g., XML: G:\To_RDS\nowplaying.xml, MP3s: G:\Shiurim\introsCleanedUp) exist/match your setup.
Run: python main_app.py or via batch: START RDS AND INTRO.bat.
Usage
Launch: Run main_app.py or batch file. GUI shows logs, current RDS messages.
Configure Messages: "Configure Messages" → Add/edit/delete; set enable, duration, schedules.
Missing Artists: "Show Missing Artists" → View/delete log entries.
Options: "Options" → Edit whitelists/blacklists; debug XML touch.
Playlist Editor: "Mini Playlist Editor" → Select preset, add/remove files, save M3U8.
Background handlers start automatically; monitor via logs.

Configuration
messages.json: Messages array with Text, Enabled, Message Time, Scheduled (Enabled, Days, Times).
Whitelist/Blacklist: In JSON; edit via Options UI.
Presets: In JSON; manage via Playlist Editor.
Bug Fixes & History
First-Click Bug (Fixed Jul 2025): Scheduled hours cleared on first select in config. Moved UI state after vars.
CMD Windows (Fixed): Hidden pydub subprocesses on Windows.
See BUG_REPRODUCTION_COMPLETE_REPORT.md for details.

Development
Structure: See project tree; handlers in threads, UI modals.
Testing: Run reproduce_bug.py (should fail post-fix); other tests for audio/RDS.
Logging: Per-handler queues to GUI; levels configurable.
License
MIT License (assumed; add LICENSE file).

Contact
For issues: Open GitHub issue or contact maintainer.

Last Updated: July 13, 2025
