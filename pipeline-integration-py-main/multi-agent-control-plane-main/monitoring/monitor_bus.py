#!/usr/bin/env python3
"""Monitor sovereign bus events in real-time."""

from core.sovereign_bus import bus
import json

def print_event(message):
    """Print formatted event message."""
    print(f"[{message['timestamp']}] {message['event_type']}: {json.dumps(message['data'], indent=2)}")

def main():
    """Monitor bus events via file watching."""
    print("🚌 Sovereign Bus Monitor Started")
    print("Monitoring for NEW events only...")
    
    # Start from current message count (ignore history)
    last_count = len(bus.get_messages())
    print(f"Ignoring {last_count} historical events")
    
    try:
        import time
        while True:
            messages = bus.get_messages()
            if len(messages) > last_count:
                # Show only new messages
                for msg in messages[last_count:]:
                    print_event(msg)
                last_count = len(messages)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Bus monitor stopped")

if __name__ == "__main__":
    main()