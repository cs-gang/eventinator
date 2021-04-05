from dataclasses import dataclass
from datetime import datetime
from typing import List, Mapping

from sanic import Sanic


@dataclass
class Event:
    """A dataclass representing an event."""

    event_id: str  # pass the snowflake in while instantiating
    event_name: str
    event_owner: str
    start_time: datetime
    end_time: datetime
    long_desc: str
    short_desc: str
    passcode: str = None

    async def create(self, app: Sanic) -> None:
        """Inserts a record for the event in the database."""
        await app.ctx.db.execute(
            """INSERT INTO events
                                    (event_id, event_name, event_owner, start_time, end_time, long_desc, short_desc, passcode)
                                    VALUES(:event_id, :event_name, :event_owner, :start_time, :end_time, :long_desc, :short_desc, :passcode)""",
            event_id=self.event_id,
            event_owner=self.event_owner,
            start_time=self.start_time,
            end_time=self.end_time,
            long_desc=self.long_desc,
            short_desc=self.short_desc,
            passcode=self.passcode,
        )
        await app.ctx.db.execute(
            "INSERT INTO users_events(uid, event_id) VALUES(:uid, :event_id)",
            uid=self.event_owner,
            event_id=self.event_id,
        )
        return self

    @classmethod
    async def by_id(cls, app: Sanic, id: str) -> "Event":
        """Retrieve an Event from the database by event ID."""
        record = await app.ctx.db.fetchrow(
            "SELECT * FROM events WHERE event_id = :event_id", event_id=id
        )
        return cls(**record)

    async def get_members(self, app: Sanic) -> List[Mapping]:
        """Retrieve all members of this particular Event."""
        # does NOT return User objects, but the raw response from the database
        return await app.ctx.db.fetch(
            "SELECT * FROM users WHERE uid IN (SELECT uid FROM users_events WHERE event_id = :event_id)",
            event_id=self.event_id,
        )

    def __dict__(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "event_owner": self.event_owner,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "long_desc": self.long_desc,
            "short_desc": self.short_desc,
            "passcode": self.passcode,
        }
