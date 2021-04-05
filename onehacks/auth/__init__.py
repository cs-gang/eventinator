from dataclasses import dataclass
from functools import partial
from typing import Mapping, Optional

import requests
from sanic import Sanic
from sanic.exceptions import SanicException
from sanic.request import Request

from onehacks.auth import discord, firebase


class UnauthenticatedError(SanicException):
    pass


@dataclass
class User:
    """
    Represents a user, either from Discord or from the Firebase login system.
    All (both UIDs we generate and discord) IDs are stored as CHAR in the database, and will hence
    be treated as strings here.
    """

    uid: str
    username: str
    email: str = None
    tz: str = None
    discord_id: str = None

    @classmethod
    async def from_discord(cls, app: Sanic, request: Request) -> "User":
        """Fetches a user's data from discord and our database.
        This function is meant to be used after a user has finished authentication only."""
        token = discord.check_logged_in(request)
        if token:
            token = {"Authorization": f"Bearer {token['access_token']}"}
            get = partial(requests.get, headers=token)
            response = await app.loop.run_in_executor(
                None, get, discord.API_BASE_URL + "/users/@me"
            )
        else:
            raise UnauthenticatedError("User has not been logged in.")

        data = response.json()

        _id = str(data.get("id"))
        username = data.get("username")
        record = await cls.from_db(_id, discord=True)

        if not record:
            # query returned None, user doesn't exist in db
            uid = str(next(app.ctx.snowflake))
            await app.ctx.db.execute(
                "INSERT INTO users(uid, username, discord_id) VALUES(:uid, :username, :discord_id)",
                uid=uid,
                username=data.get("username"),
                discord_id=_id,
            )
            return cls(uid=uid, username=username, discord_id=_id)
        else:
            return cls(**record)

    @staticmethod
    async def from_db(
        app: Sanic, _id: str, *, discord: bool = False
    ) -> Optional[Mapping]:
        """Fetches a user's record from the database.
        If `discord` is set to True, the matching row with provided discord ID will be returned."""
        if discord:
            return await app.ctx.db.fetchrow(
                "SELECT * FROM users WHERE discord_id = :_id", _id=_id
            )
        else:
            return await app.ctx.db.fetchrow(
                "SELECT * FROM users WHERE uid = :_id", _id=_id
            )
