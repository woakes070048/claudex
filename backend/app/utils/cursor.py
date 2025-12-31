import base64
from datetime import datetime
from uuid import UUID


def encode_cursor(created_at: datetime, id: UUID) -> str:
    return base64.urlsafe_b64encode(
        f"{created_at.isoformat()}|{id}".encode()
    ).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, id_str = decoded.split("|")
    return datetime.fromisoformat(ts_str), UUID(id_str)
