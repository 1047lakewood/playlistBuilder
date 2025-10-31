import json
from datetime import datetime
import os
import sys

def diagnose_scheduler():
    print("RDS Message Scheduler Diagnostic Tool")
    print("-" * 50)
    
    # Get current date and time
    now = datetime.now()
    current_day = now.strftime("%a")  # Abbreviated day name (Sun, Mon, etc.)
    current_hour = now.hour
    
    print(f"Current date/time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current day: {current_day}")
    print(f"Current hour: {current_hour}")
    print("-" * 50)
    
    # Path to messages.json
    messages_file = "messages.json"
    
    # Check if file exists
    if not os.path.exists(messages_file):
        print(f"ERROR: {messages_file} not found in current directory!")
        print(f"Current working directory: {os.getcwd()}")
        files_in_dir = os.listdir(".")
        print(f"Files in current directory: {files_in_dir}")
        return
    
    # Check file size and modification time
    file_size = os.path.getsize(messages_file)
    file_mtime = datetime.fromtimestamp(os.path.getmtime(messages_file))
    
    print(f"Found {messages_file}: {file_size} bytes")
    print(f"Last modified: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # Read and parse messages
    try:
        with open(messages_file, "r") as file:
            data = json.load(file)
            messages = data.get("Messages", [])
    except Exception as e:
        print(f"ERROR: Failed to parse {messages_file}: {str(e)}")
        return
    
    print(f"Successfully parsed {len(messages)} messages from file")
    print("-" * 50)
    
    # Check each message
    active_messages = []
    
    for i, msg in enumerate(messages):
        print(f"Message #{i+1}: '{msg.get('Text', 'NO TEXT')}'")
        enabled = msg.get("Enabled", False)
        scheduled = msg.get("Scheduled", {}).get("Enabled", False)
        days = msg.get("Scheduled", {}).get("Days", [])
        times = msg.get("Scheduled", {}).get("Times", [])
        duration = msg.get("Message Time", 10)
        
        print(f"  Enabled: {enabled}")
        print(f"  Duration: {duration} seconds")
        print(f"  Scheduling enabled: {scheduled}")
        
        if scheduled:
            print(f"  Scheduled days: {', '.join(days) if days else 'None'}")
            print(f"  Scheduled hours: {', '.join(map(str, times)) if times else 'None'}")
        
        # Check if this message should be active now
        should_be_active = False
        schedule_status = "N/A"
        
        if not enabled:
            schedule_status = "Message is disabled"
        elif not scheduled:
            # Not scheduled means always on when enabled
            should_be_active = True
            schedule_status = "Always active (no scheduling)"
        else:
            # Check if current day and time match schedule
            day_match = current_day in days
            time_match = current_hour in times
            
            if day_match and time_match:
                should_be_active = True
                schedule_status = f"Schedule matches current day ({current_day}) and hour ({current_hour})"
            elif not day_match:
                schedule_status = f"Current day ({current_day}) not in scheduled days {days}"
            elif not time_match:
                schedule_status = f"Current hour ({current_hour}) not in scheduled hours {times}"
        
        print(f"  Status: {schedule_status}")
        print(f"  Should be active now: {should_be_active}")
        
        if should_be_active:
            active_messages.append(msg["Text"])
        
        print("-" * 50)
    
    # Summary
    print("\nSUMMARY:")
    print(f"Total messages: {len(messages)}")
    print(f"Messages that should be active now: {len(active_messages)}")
    
    if active_messages:
        print("\nActive messages:")
        for i, msg in enumerate(active_messages):
            print(f"{i+1}. {msg}")
    else:
        print("\nNo messages should be active at this time based on your configuration.")
    
    # Check if "Only SUN" message should be active
    sun_message = next((msg for msg in messages if msg.get("Text") == "Only SUN"), None)
    if sun_message:
        print("\nDetailed check for 'Only SUN' message:")
        enabled = sun_message.get("Enabled", False)
        scheduled = sun_message.get("Scheduled", {}).get("Enabled", False)
        days = sun_message.get("Scheduled", {}).get("Days", [])
        times = sun_message.get("Scheduled", {}).get("Times", [])
        
        print(f"- Enabled: {enabled}")
        print(f"- Scheduling enabled: {scheduled}")
        print(f"- Scheduled days: {days}")
        print(f"- Scheduled hours: {times}")
        print(f"- Current day is 'Sun': {current_day == 'Sun'}")
        print(f"- Current hour {current_hour} in scheduled times: {current_hour in times}")
        
        if current_day == "Sun" and current_hour in times and enabled and scheduled:
            print("✓ 'Only SUN' message SHOULD be active now")
        else:
            reasons = []
            if not enabled:
                reasons.append("Message is not enabled")
            if not scheduled:
                reasons.append("Scheduling is not enabled")
            if current_day != "Sun":
                reasons.append(f"Current day is {current_day}, not Sun")
            if current_hour not in times:
                reasons.append(f"Current hour {current_hour} is not in scheduled hours {times}")
            
            print(f"✗ 'Only SUN' message should NOT be active because: {'; '.join(reasons)}")
    
    # Provide suggestions
    print("\nPOSSIBLE ISSUES:")
    print("1. The scheduler process might not be running")
    print("2. The scheduler might be reading a different messages.json file")
    print("3. There might be a time zone difference affecting the scheduler")
    print("4. The scheduler process might have a bug in its scheduling logic")
    print("5. The scheduler might not be properly reloading the messages file")

if __name__ == "__main__":
    diagnose_scheduler()
