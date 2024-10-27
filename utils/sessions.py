import os
import json
from datetime import datetime

# Directory where session files are stored
SESSION_DIR = "data/sessions/"
TIME_GAP_THRESHOLD = 30 * 60 * 1000  # 30 minutes in milliseconds

def load_all_events():
    all_events = []
    for filename in os.listdir(SESSION_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(SESSION_DIR, filename), "r") as file:
                data = json.load(file)
                all_events.extend(data["events"])
    all_events.sort(key=lambda x: x["timestamp"])
    return all_events

events = load_all_events()
print(f"Loaded {len(events)} events.")

def segment_sessions(events):
    sessions = []
    current_session = []
    for i, event in enumerate(events):
        if current_session and event['timestamp'] - current_session[-1]['timestamp'] > TIME_GAP_THRESHOLD:
            sessions.append(current_session)
            current_session = []
        current_session.append(event)
    if current_session:
        sessions.append(current_session)
    return sessions

segmented_sessions = segment_sessions(events)
print(f"Detected {len(segmented_sessions)} sessions.")

# Updated Analysis Functions
def analyze_typing_events(events):
    typing_events = [event for event in events if event['data'].get('source') == 5]
    
    # Track each unique text state along with timestamp
    unique_texts = []
    for event in typing_events:
        text = event['data'].get('text', "")
        timestamp = event['timestamp']
        if not unique_texts or unique_texts[-1][0] != text:
            unique_texts.append((text, timestamp))

    timestamps = [event['timestamp'] for event in typing_events]
    typing_durations = [(t2 - t1) for t1, t2 in zip(timestamps, timestamps[1:])]
    average_speed = sum(typing_durations) / len(typing_durations) if typing_durations else 0

    return {
        "typing_history": unique_texts,  # Contains sequence of texts typed with timestamps
        "average_typing_speed": average_speed,
    }

def analyze_mouse_movements(events):
    mouse_events = [event for event in events if event['data'].get('source') == 1]
    return {"total_movements": len(mouse_events)}

def analyze_element_interactions(events):
    element_events = [event for event in events if event['data'].get('source') == 0]
    elements_added = sum(len(event['data']['adds']) for event in element_events)
    elements_removed = sum(len(event['data']['removes']) for event in element_events)
    return {
        "attributes_changes": len([event for event in element_events if event['data']['attributes']]),
        "total_elements_added": elements_added,
        "total_elements_removed": elements_removed,
    }

def detect_page_visits(events):
    page_visits = []
    for event in events:
        # Check for URL or page navigation patterns; adjust depending on event structure
        if event['type'] == 3 and 'page_url' in event['data']:
            url = event['data']['page_url']
            timestamp = event['timestamp']
            page_visits.append((url, timestamp))
    
    return {"page_visits": page_visits}

def analyze_session(events, session_id):
    typing_data = analyze_typing_events(events)
    mouse_data = analyze_mouse_movements(events)
    element_data = analyze_element_interactions(events)
    page_visit_data = detect_page_visits(events)
    
    start_timestamp = events[0]['timestamp']
    end_timestamp = events[-1]['timestamp']
    session_duration = (end_timestamp - start_timestamp) / 1000  # Convert to seconds

    return {
        "session_id": session_id,
        "start_time": datetime.fromtimestamp(start_timestamp / 1000).isoformat(),
        "session_duration_seconds": session_duration,
        "typing_analysis": typing_data,
        "mouse_movement_analysis": mouse_data,
        "element_interaction_analysis": element_data,
        "page_visit_analysis": page_visit_data,
    }

# Analyze all segmented sessions and save results
all_summaries = [analyze_session(session, i) for i, session in enumerate(segmented_sessions)]

# Output summary for each session
for summary in all_summaries:
    print("Session Summary:", json.dumps(summary, indent=2))

summary_output_path = "session_summary.json"
with open(summary_output_path, "w") as outfile:
    json.dump(all_summaries, outfile, indent=2)
