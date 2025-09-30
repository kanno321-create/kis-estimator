"""Fake Gmail Client for Testing"""
from typing import Dict, Any, List
from datetime import datetime
import hashlib

class FakeGmail:
    """Mock Gmail Service"""
    def __init__(self):
        self.sent_messages = []
        self.drafts = []
        self.labels = ["INBOX", "SENT", "DRAFT", "TRASH"]

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: List[str] = None,
        bcc: List[str] = None,
        attachments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock send email"""
        message_id = hashlib.md5(f"{to}{subject}{datetime.utcnow()}".encode()).hexdigest()

        message = {
            "id": message_id,
            "threadId": message_id,
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc or [],
            "bcc": bcc or [],
            "attachments": attachments or [],
            "timestamp": datetime.utcnow().isoformat(),
            "status": "sent"
        }

        self.sent_messages.append(message)

        return {
            "success": True,
            "messageId": message_id,
            "timestamp": message["timestamp"]
        }

    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Mock create draft"""
        draft_id = hashlib.md5(f"draft_{to}{subject}{datetime.utcnow()}".encode()).hexdigest()

        draft = {
            "id": draft_id,
            "message": {
                "to": to,
                "subject": subject,
                "body": body
            },
            "created_at": datetime.utcnow().isoformat()
        }

        self.drafts.append(draft)

        return {"draftId": draft_id, "success": True}

    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages"""
        return self.sent_messages

    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get message by ID"""
        for msg in self.sent_messages:
            if msg["id"] == message_id:
                return msg
        return None

    def search_messages(self, query: str) -> List[Dict[str, Any]]:
        """Search messages"""
        results = []
        for msg in self.sent_messages:
            if query.lower() in msg["subject"].lower() or query.lower() in msg["body"].lower():
                results.append(msg)
        return results

    def add_label(self, message_id: str, label: str) -> bool:
        """Add label to message"""
        for msg in self.sent_messages:
            if msg["id"] == message_id:
                if "labels" not in msg:
                    msg["labels"] = []
                if label not in msg["labels"]:
                    msg["labels"].append(label)
                return True
        return False

    def reset(self):
        """Reset all messages for testing"""
        self.sent_messages = []
        self.drafts = []