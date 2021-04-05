from dataclasses import dataclass
from functools import partial, wraps
from typing import Any, Awaitable, List, Mapping, Optional

import requests
from sanic import Sanic
from sanic.exceptions import SanicException
from sanic.request import Request
from sanic.response import HTTPResponse

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
        This function is meant to be used after a user has finished authentication only.
        It will register the user in the database if they aren't already."""
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
        record = await cls.from_db(app, _id, discord=True)

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
            # if the username from the api is different than the one we've stored, update it
            if username != record["username"]:
                await app.ctx.db.execute(
                    "UPDATE users SET username = :username WHERE uid = :uid",
                    username=username,
                    uid=record["uid"],
                )
            return cls(
                uid=record["uid"], username=username, discord_id=record["discord_id"]
            )

    @classmethod
    async def on_firebase(
        cls, app: Sanic, username: str, email: str, password: str
    ) -> "User":
        """
        Used on the sign-up route. Registers a new user on Firebase and saves their data in the database.

        Arguments ::
            app: Sanic -> The running Sanic instance.
            email: str
            username: str
            password: str
        """
        user_record = await firebase.create_user(
            app, username=username, email=email, password=password
        )

        await app.ctx.db.execute(
            "INSERT INTO users(uid, username, email) VALUES(:uid, :username, :email)",
            uid=user_record.uid,
            username=user_record.display_name,
            email=user_record.email,
        )
        return cls(
            uid=user_record.uid,
            username=user_record.display_name,
            email=user_record.email,
        )

    @classmethod
    async def from_firebase(cls, app: Sanic, uid: str) -> "User":
        """
        Fetches a user's details from Firebase.
        This method does an API call, use it sparingly. Wherever possible, use `User.from_db` instead."""
        user_record = await firebase.get_user(app, uid)
        return cls(
            uid=user_record.uid,
            username=user_record.display_name,
            email=user_record.email,
        )

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

    async def get_events(self, app: Sanic) -> List[Mapping]:
        """Gets a user's events from the database."""
        # does NOT return Event objects, but the raw response from the database
        return await app.ctx.db.fetch(
            "SELECT * FROM events WHERE event_id IN (SELECT event_id FROM users_events WHERE uid = :uid)",
            uid=self.uid,
        )

    async def set_tz(self, app: Sanic, tz: str) -> None:
        """Sets the user's timezone."""
        self.tz = tz
        await app.ctx.db.execute(
            "UPDATE users SET tz = :tz WHERE uid = :uid", tz=tz, uid=self.uid
        )


def authorized():
    def decorator(func: Awaitable) -> Awaitable:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> HTTPResponse:
            """
            Decorator that checks if a user is signed in.
            The decorator will inject an argument:
                platform: str -> Either "discord" or "firebase"
            """
            from_discord = discord.check_logged_in(request)
            from_firebase = await firebase.check_logged_in(request)

            if from_discord:
                return await func(request, platform="discord")
            elif from_firebase:
                return await func(request, platform="firebase")
            else:
                raise UnauthenticatedError("Not logged in.", status=403)

        return wrapper

    return decorator
