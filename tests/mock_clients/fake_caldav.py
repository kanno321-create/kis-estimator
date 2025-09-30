"""Fake CalDAV Client for Testing"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import uuid

class FakeCalDAVEvent:
    """Mock Calendar Event"""
    def __init__(self, summary: str, start: datetime, end: datetime, description: str = ""):
        self.uid = str(uuid.uuid4())
        self.summary = summary
        self.start = start
        self.end = end
        self.description = description
        self.attendees = []
        self.location = ""
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "summary": self.summary,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "description": self.description,
            "attendees": self.attendees,
            "location": self.location,
            "created_at": self.created_at.isoformat()
        }

class FakeCalDAV:
    """Mock CalDAV Service"""
    def __init__(self):
        self.calendars = {"default": []}
        self.events = {}

    def create_event(
        self,
        calendar: str,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        attendees: List[str] = None,
        location: str = ""
    ) -> Dict[str, Any]:
        """Create calendar event"""
        event = FakeCalDAVEvent(summary, start, end, description)
        event.attendees = attendees or []
        event.location = location

        if calendar not in self.calendars:
            self.calendars[calendar] = []

        self.calendars[calendar].append(event)
        self.events[event.uid] = event

        return {
            "success": True,
            "eventId": event.uid,
            "event": event.to_dict()
        }

    def get_events(
        self,
        calendar: str = "default",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get events from calendar"""
        if calendar not in self.calendars:
            return []

        events = self.calendars[calendar]

        # Filter by date range if provided
        if start_date and end_date:
            events = [
                e for e in events
                if start_date <= e.start <= end_date
            ]

        return [e.to_dict() for e in events]

    def update_event(self, event_id: str, **kwargs) -> bool:
        """Update existing event"""
        if event_id in self.events:
            event = self.events[event_id]
            for key, value in kwargs.items():
                if hasattr(event, key):
                    setattr(event, key, value)
            return True
        return False

    def delete_event(self, event_id: str) -> bool:
        """Delete event"""
        if event_id in self.events:
            event = self.events[event_id]
            # Remove from all calendars
            for cal_events in self.calendars.values():
                if event in cal_events:
                    cal_events.remove(event)
            del self.events[event_id]
            return True
        return False

    def search_events(self, query: str) -> List[Dict[str, Any]]:
        """Search events"""
        results = []
        for event in self.events.values():
            if (query.lower() in event.summary.lower() or
                query.lower() in event.description.lower()):
                results.append(event.to_dict())
        return results

    def create_recurring_event(
        self,
        calendar: str,
        summary: str,
        start: datetime,
        duration: timedelta,
        recurrence: str,  # "daily", "weekly", "monthly"
        count: int = 10
    ) -> List[str]:
        """Create recurring events"""
        event_ids = []
        current_start = start

        for i in range(count):
            end = current_start + duration
            result = self.create_event(calendar, f"{summary} #{i+1}", current_start, end)
            event_ids.append(result["eventId"])

            # Calculate next occurrence
            if recurrence == "daily":
                current_start += timedelta(days=1)
            elif recurrence == "weekly":
                current_start += timedelta(weeks=1)
            elif recurrence == "monthly":
                current_start += timedelta(days=30)  # Simplified

        return event_ids

    def reset(self):
        """Reset all calendars for testing"""
        self.calendars = {"default": []}
        self.events = {}