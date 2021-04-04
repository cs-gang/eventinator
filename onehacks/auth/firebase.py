"""Handles the authentication process with Firebase for the Login with Email function."""
from functools import partial

from firebase_admin import auth
from firebase_admin.auth import UserRecord
from sanic import Sanic

from onehacks.server import app


async def create_user(
    app: Sanic, username: str, email: str, password: str
) -> UserRecord:
    """
    Creates a new user on Firebase with the given username, email and password.
    A snowflake will be generated and assigned as the user ID.

    Arguments ::
        app: Sanic -> The running Sanic instance.
        username: str
        email: str
        password: str -> The UNHASHED, raw string password.
    Returns ::
        firebase_admin.auth.UserRecord
    """
    uid = next(app.ctx.snowflake)
    create_user = partial(
        auth.create_user,
        uid=uid,
        display_name=username,
        email=email,
        password=password,
        app=app.ctx.firebase,
    )
    return await app.loop.run_in_executor(None, create_user)
