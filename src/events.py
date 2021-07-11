from dataclasses import dataclass
from datetime import datetime
from typing import List, Mapping, Optional, TYPE_CHECKING

from sanic import Sanic

if TYPE_CHECKING:
    from src.auth import User


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
    passcode: Optional[str] = None

    async def create(self, app: Sanic) -> "Event":
        """Inserts a record for the event in the database."""
        await app.ctx.db.execute(
            """INSERT INTO events
                                    (event_id, event_name, event_owner, start_time, end_time, long_desc, short_desc, passcode)
                                    VALUES(:event_id, :event_name, :event_owner, :start_time, :end_time, :long_desc, :short_desc, :passcode)""",
            event_id=self.event_id,
            event_name=self.event_name,
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

    async def get_members_usernames(self, app: Sanic) -> List[str]:
        """Retrieve the usernames of all members of this particular Event."""
        return [
            i["username"]
            for i in await app.ctx.db.fetch(
                "SELECT username FROM users WHERE uid IN (SELECT uid FROM users_events WHERE event_id = :event_id)",
                event_id=self.event_id,
            )
        ]

    def is_owner(self, user: "User") -> bool:
        return user.uid == self.event_owner

    async def delete(self, app: Sanic) -> None:
        """
        Deletes the event.
        """
        # the local sqlite db was not configured to ON DELETE CASCADE
        # and testing this again will be a pain
        # if we deploy, TODO: write a proper init.sql for postgres
        # for now, just delete from both tables.
        await app.ctx.db.execute(
            "DELETE FROM users_events WHERE event_id = :id", id=self.event_id
        )
        await app.ctx.db.execute(
            "DELETE FROM events WHERE event_id = :id", id=self.event_id
        )
