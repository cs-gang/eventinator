"""Handles the authentication process with Firebase for the Login with Email function."""
from functools import partial
import json
from typing import Optional

from firebase_admin import auth
from firebase_admin.auth import UserRecord
import requests
from sanic import Sanic

from onehacks.server import app


API_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"


async def create_user(
    app: Sanic, username: str, email: str, password: str
) -> UserRecord:
    """
    Creates a new user on Firebase with the given username, email and password,
    and inserts the details to our database.
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
        uid=str(uid),
        display_name=username,
        email=email,
        password=password,
        app=app.ctx.firebase,
    )
    return await app.loop.run_in_executor(None, create_user)


async def authenticate_user(app: Sanic, email: str, password: str) -> Optional[dict]:
    """
    Authenticate a user with the provided email and password.
    This will be used while logging in.

    Arguments ::
        app: Sanic -> The running Sanic instance.
        email: str
        password: str

    Returns ::
        None, if the user failed authentication
        Raw response dictionary from the API if the user passed authentication.
    """
    payload = json.dumps(
        {"email": email, "password": password, "returnSecureToken": True}
    )
    post = partial(
        requests.post,
        API_URL,
        params={"key": app.config.FIREBASE_API_KEY},
        data=payload,
    )
    response = await app.loop.run_in_executor(None, post)
    response_data = response.json()

    if not response_data.get("idToken"):
        # the API didn't give back a regenerate token, so the authentication was a failure
        return
    else:
        return response_data


# TODO: make delete, update user functions
