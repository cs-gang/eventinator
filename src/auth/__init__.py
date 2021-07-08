from dataclasses import dataclass
from functools import partial, wraps
from src.events import Event
from typing import Any, Callable, List, Mapping, Optional

import requests
from sanic import Sanic
from sanic.exceptions import SanicException
from sanic.request import Request
from sanic.response import HTTPResponse

from src.auth import discord, firebase


class UnauthenticatedError(SanicException):
    """
    Exception raised when a user attempts to reach a route
    that requires authentication.
    """


class OwnerOnlyActionError(UnauthenticatedError):
    """
    Exception raised when a user attempts to run an action
    that requires them to be the owner of that resource.
    """


@dataclass
class User:
    """
    Represents a user, either from Discord or from the Firebase login system.
    All (both UIDs we generate and discord) IDs are stored as CHAR in the database, and will hence
    be treated as strings here.
    """

    uid: str
    username: str
    email: Optional[str] = None
    tz: Optional[str] = None
    discord_id: Optional[str] = None

    @classmethod
    async def from_discord(cls, app: Sanic, request: Request) -> "User":
        """Fetches a user's data from discord and our database.
        This function is meant to be used after a user has finished authentication only.
        It will register the user in the database if they aren't already."""
        token = discord.check_logged_in(request)
        if token:
            token = {"Authorization": f"Bearer {token['access_token']}"}  # type: ignore
            get = partial(requests.get, headers=token)
            response = await app.loop.run_in_executor(
                None, get, discord.API_BASE_URL + "/users/@me"
            )
        else:
            raise UnauthenticatedError("User has not been logged in.")

        data = response.json()

        _id = str(data.get("id"))
        username = data.get("username")

        try:
            record = await cls.from_db(app, _id, discord=True)

        except TypeError:
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
            if username != record.username:
                await app.ctx.db.execute(
                    "UPDATE users SET username = :username WHERE uid = :uid",
                    username=username,
                    uid=record.uid,
                )
            return cls(
                uid=record.uid,
                username=username,
                discord_id=record.discord_id,
                tz=record.tz,
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

    @classmethod
    async def from_db(cls, app: Sanic, _id: str, *, discord: bool = False) -> "User":
        """Fetches a user's record from the database.
        If `discord` is set to True, the matching row with provided discord ID will be returned."""
        if discord:
            return cls(
                **(
                    await app.ctx.db.fetchrow(
                        "SELECT * FROM users WHERE discord_id = :_id", _id=_id
                    )
                )
            )
        else:
            return cls(
                **(
                    await app.ctx.db.fetchrow(
                        "SELECT * FROM users WHERE uid = :_id", _id=_id
                    )
                )
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

    async def join_event(self, app: Sanic, event: Event) -> None:
        """Adds the user to specified event."""
        await app.ctx.db.execute(
            "INSERT INTO users_events(uid, event_id) VALUES(:uid, :eid)",
            uid=self.uid,
            eid=event.event_id,
        )

    async def leave_event(self, app: Sanic, event: Event) -> None:
        """Removes the user from the specified event."""
        await app.ctx.db.execute(
            "DELETE FROM users_events WHERE uid=:uid AND event_id=:eid",
            uid=self.uid,
            eid=event.event_id,
        )

    async def get_owned_events(self, app: Sanic) -> List[Mapping]:
        """Get all events owned by this user."""
        return await app.ctx.db.fetch(
            "SELECT * FROM events WHERE event_owner=:uid", uid=self.uid
        )

    async def delete(self, app: Sanic) -> None:
        """
        Deletes a user and the events they own.
        """
        # same TODO as src/events.py
        await app.ctx.db.execute(
            "DELETE FROM users_events WHERE uid = :id", id=self.uid
        )
        await app.ctx.db.execute("DELETE FROM events WHERE owner_id = :id", id=self.uid)
        await app.ctx.db.execute("DELETE FROM users WHERE uid = :id", id=self.uid)


def authorized():
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> HTTPResponse:
            """
            Decorator that checks if a user is signed in.
            The decorator will inject two arguments:
                user: User -> The User object for the signed in user.
                platform: str -> Platform the user used to sign in.
            """
            from_discord = discord.check_logged_in(request)
            from_firebase = await firebase.check_logged_in(request)

            if from_discord:
                user = await User.from_discord(request.app, request)
                return await func(
                    request, platform="discord", user=user, *args, **kwargs
                )
            elif from_firebase:
                user = await User.from_db(request.app, from_firebase["uid"])
                return await func(
                    request, platform="firebase", user=user, *args, **kwargs
                )
            else:
                raise UnauthenticatedError("Not logged in.", status_code=403)

        return wrapper

    return decorator


def guest_or_authorized():
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> HTTPResponse:
            """
            Decorator that checks if a user is signed in.
            Unlike the `src.auth.authenticated` decorator, this will NOT
            raise an UnauthenticatedError in the case the user is not logged
            in, but sets the injected User variable to "guest".
            """
            from_discord = discord.check_logged_in(request)
            from_firebase = await firebase.check_logged_in(request)

            if from_discord:
                user = await User.from_discord(request.app, request)
                return await func(
                    request, platform="discord", user=user, *args, **kwargs
                )
            elif from_firebase:
                user = await User.from_db(request.app, from_firebase["uid"])
                return await func(
                    request, platform="firebase", user=user, *args, **kwargs
                )
            else:
                return await func(request, platform=None, user="guest", *args, **kwargs)

        return wrapper

    return decorator
