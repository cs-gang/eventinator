from functools import wraps
from typing import Any, AsyncGenerator, List, Mapping, Optional

from databases import Database as _Database
from sanic import Sanic


class DatabaseNotConnectedError(Exception):
    """Exception raised when any queries are attempted before the connection was made
    using the `Database.connect` method."""


def is_connected(func: Any) -> Any:
    """
    A decorator which checks if the connection has been initialized using the
    `Database.connect` method before running any queries.

    Raises ::
        DatabaseNotConnectedError`
    """

    @wraps(func)
    async def wrapper(ref, *args, **kwargs):
        if not ref.is_connected:
            raise DatabaseNotConnectedError(
                "No database operation can take place without connecting "
                "to the database first. Has the app started up normally?"
            )
        else:
            return await func(ref, *args, **kwargs)

    return wrapper


class Database:
    """Represents a connection to the underlying database.
    To be added as an attribute of `app.ctx`"""

    def __init__(self, app: Sanic) -> None:
        """
        Initializes a database instance.
        The database does not CONNECT until the `Database.connect` coroutine is called.

        Arguments ::
            app: Sanic -> The running Sanic instance.
                Note: The database URI must be set to the `config` of the Sanic instance.
        """
        self.db = _Database(app.config.DB_URI)
        self.is_connected = False
        self.app = app

    async def connect(self) -> None:
        """Establishes the connection with the database."""
        await self.db.connect()
        self.is_connected = True

    @is_connected
    async def disconnect(self) -> None:
        """Disconnects the connection with the database."""
        await self.db.disconnect()
        self.is_connected = False

    @is_connected
    async def initialize_tables(self) -> None:
        """
        Creates the tables in the database if they haven't been made already.
        """
        users = """CREATE TABLE IF NOT EXISTS users(
            uid CHAR(20) PRIMARY KEY,
            email TEXT UNIQUE,
            username VARCHAR(25) NOT NULL,
            tz VARCHAR(50),
            discord_id CHAR(20) UNIQUE
        )"""
        events = """CREATE TABLE IF NOT EXISTS events(
            event_id CHAR(20) PRIMARY KEY,
            event_name VARCHAR(25) NOT NULL,
            event_owner CHAR(20) REFERENCES users(uid),
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            long_desc VARCHAR(5000) NOT NULL,
            short_desc VARCHAR(75),
            passcode CHAR(8)
        )"""
        users_events = """CREATE TABLE IF NOT EXISTS users_events(
            uid CHAR(20) REFERENCES users(uid),
            event_id CHAR(20) REFERENCES events(event_id)
        )"""

        await self.db.execute(query=users)
        await self.db.execute(query=events)
        await self.db.execute(query=users_events)

    @is_connected
    async def execute(self, query: str, **kwargs: Any) -> str:
        return await self.db.execute(query=query, values=kwargs)

    @is_connected
    async def executemany(self, query: str, *args: Any) -> None:
        return await self.db.execute_many(query=query, values=list(args))

    @is_connected
    async def fetch(self, query: str, **kwargs: Any) -> List[Mapping]:
        return await self.db.fetch_all(query=query, values=kwargs)

    @is_connected
    async def fetchrow(self, query: str, **kwargs: Any) -> Optional[Mapping]:
        return await self.db.fetch_one(query=query, values=kwargs)

    @is_connected
    async def fetchval(self, query: str, **kwargs: Any) -> Optional[Any]:
        return await self.db.fetch_one(query=query, values=kwargs)

    @is_connected
    async def iterate(self, query: str, **kwargs: Any) -> AsyncGenerator[Mapping, None]:
        # to be used like a cursor, in case large amounts of data is to be retrieved
        async for record in self.db.iterate(query=query, values=kwargs):
            yield record
