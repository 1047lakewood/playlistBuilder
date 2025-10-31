RDS_IP = "50.208.125.83"


import socket
import json
import time
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import setproctitle

setproctitle.setproctitle("SEND RDS")
# Configuration
RDS_PORT = 10001  # Update to correct port
MESSAGE_JSON = "messages.json"
NOW_PLAYING_XML = r"G:\To_RDS\nowplaying.xml"
DEFAULT_MESSAGE = "Welcome to our station!"
CHECK_INTERVAL = 60  # Seconds
PLAYLIST_URL = "http://192.168.3.12:9000/?pass=bmas220&action=getplaylist2"

message_index = 0  # Tracks the current message index

def load_messages():
    try:
        with open(MESSAGE_JSON, "r") as file:
            return json.load(file)["Messages"]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: {e}. Using empty message list.")
        return []

def load_now_playing():
    try:
        tree = ET.parse(NOW_PLAYING_XML)
        root = tree.getroot()
        current_track = root.find("TRACK")
        return {
            "artist": current_track.get("ARTIST", ""),
            "title": current_track.findtext("TITLE", ""),
        }
    except (FileNotFoundError, ET.ParseError) as e:
        print(f"Warning: {e}. Using empty now playing data.")
        return {"artist": "", "title": ""}

def get_next_r_artist():
    """Fetch the next artist starting with 'R' from the playlist."""
    try:
        response = requests.get(PLAYLIST_URL, timeout=10)
        if response.status_code == 200:
            # Parse the XML response
            root = ET.fromstring(response.content)
            # Find all tracks in the playlist
            tracks = root.findall(".//TRACK")
            
            # Look for the first artist starting with 'R'
            for track in tracks:
                artist = track.get("ARTIST", "")
                if artist.strip().upper().startswith("R"):
                    return artist
                    
        # Return empty string if no R artist found or request failed
        return ""
    except Exception as e:
        print(f"Error fetching playlist: {e}")
        return ""

def should_display_message(message, now_playing):
    if not message.get("Enabled", True):
        return False

    # Check schedule
    if message.get("Scheduled", {}).get("Enabled", False):
        # Get current day and time
        current_day = datetime.now().strftime("%a")  # Mon, Tue, Wed, etc.
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        current_time = current_hour * 60 + current_minute  # Convert to minutes for comparison

        # Check if current day is in scheduled days
        if current_day not in message["Scheduled"].get("Days", []):
            return False
            
        # Check if current time is in any of the scheduled time ranges
        in_scheduled_time = False
        for time_range in message["Scheduled"].get("Times", []):
            if isinstance(time_range, dict) and "start" in time_range and "end" in time_range:
                start_parts = time_range["start"].split(":")
                end_parts = time_range["end"].split(":")
                
                if len(start_parts) == 2 and len(end_parts) == 2:
                    start_time = int(start_parts[0]) * 60 + int(start_parts[1])
                    end_time = int(end_parts[0]) * 60 + int(end_parts[1])
                    
                    if start_time <= current_time <= end_time:
                        in_scheduled_time = True
                        break
                        
        if message["Scheduled"].get("Times") and not in_scheduled_time:
            return False

    # Ensure placeholders have valid values
    if "{artist}" in message.get("Text", "") and not now_playing.get("artist"):
        return False
        
    # Check for {upnext} placeholder
    if "{upnext}" in message.get("Text", "") and not get_next_r_artist():
        return False

    return True

def format_message_text(text, now_playing):
    replacements = {
        "{artist}": now_playing.get("artist", "").upper(),
        "{title}": now_playing.get("title", ""),
        "{upnext}": get_next_r_artist().upper(),
        "{time}": datetime.now().strftime("%I:%M %p"),
        "{date}": datetime.now().strftime("%d %b %Y"),
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text

def send_command(command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((RDS_IP, RDS_PORT))
            s.sendall((command + '\r\n').encode())
            response = s.recv(1024).decode().strip()
            return response
    except (socket.timeout, ConnectionRefusedError) as e:
        return f"Error: {e}"

def send_message_to_rds(text):
    """Sends a message to the RDS encoder."""
    response = send_command(f"TEXT={text}")
    print(f"[{datetime.now()}] Sent: {text}")
    print(f"Response: {response}")

def main():
    global message_index
    print(f"Starting Enhanced AutoRDS... Connecting to {RDS_IP}:{RDS_PORT}")
    
    while True:
        try:
            messages = load_messages()
            now_playing = load_now_playing()
            valid_messages = [m for m in messages if should_display_message(m, now_playing)]

            if valid_messages:
                # Get the message to display based on Message Time if provided
                current_time = datetime.now()
                message_to_show = None
                
                for idx, message in enumerate(valid_messages):
                    message_time = message.get("Message Time", 0)
                    if message_time > 0:
                        # If we're exactly at a message's time slot
                        if current_time.minute % message_time == 0 and current_time.second < 10:
                            message_to_show = message
                            message_index = idx
                            break
                
                # If no message is scheduled for this exact time, use rotation
                if not message_to_show:
                    message_to_show = valid_messages[message_index % len(valid_messages)]
                    message_index += 1  # Move to the next message
                
                message_text = format_message_text(message_to_show["Text"], now_playing)
                send_message_to_rds(message_text)
            else:
                send_message_to_rds(DEFAULT_MESSAGE)

            time.sleep(CHECK_INTERVAL)  # Repeat after interval

        except KeyboardInterrupt:
            print("\nExiting Enhanced AutoRDS...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()