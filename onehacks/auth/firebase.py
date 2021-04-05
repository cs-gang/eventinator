"""Handles the authentication process with Firebase for the Login with Email function."""
from datetime import datetime, timedelta
from functools import partial
import json
from typing import Optional

from firebase_admin import auth, exceptions
from firebase_admin.auth import UserRecord
import requests
from sanic import Sanic
from sanic.request import Request
from sanic.exceptions import ServerError

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


async def create_session_cookie(app: Sanic, request: Request, data: dict) -> dict:
    """
    Creates a session cookie for a user with the given `idToken`.

    Arguments ::
        app: Sanic -> The running Sanic instance
        request: Request
        data: dict -> The raw response dictionary sent by the Firebase API on a succesful login.
        This will be returned by the `authenticate_user` function.

    Returns ::
        ON SUCCESS =>
        Dictionary with 2 keys:
            session_cookie: bytes
            expires: datetime.datetime (UTC)
        NOTE: Don't forget to set the session_cookie on the HTTPResponse!
        ON FAILURE =>
        boolean False
    """
    id_token = data.get("idToken")
    expires_in = timedelta(days=5)
    try:
        create_session_cookie = partial(
            auth.create_session_cookie,
            id_token=id_token,
            expires_in=expires_in,
            app=app.ctx.firebase,
        )
        session_cookie = await app.loop.run_in_executor(None, create_session_cookie)
        expires = datetime.utcnow() + expires_in
        return {"session_cookie": session_cookie, "expires": expires}
    except exceptions.FirebaseError:
        return False


async def delete_session_cookie(app: Sanic, request: Request) -> None:
    """Clears the session cookie. Meant to be used on sign out.
    Arguments ::
        app: Sanic -> The running Sanic instance
        request: Request
    """
    session_cookie = request.cookies.get("session")
    try:
        verify_session_cookie = partial(
            auth.verify_session_cookie, session_cookie, check_revoked=True
        )
        decoded_claims = await app.loop.run_in_executor(None, verify_session_cookie)
        revoke = partial(auth.revoke_refresh_tokens, decoded_claims["sub"])
        await app.loop.run_in_executor(None, revoke)
    except auth.InvalidSessionCookieError:
        raise ServerError("Tried to revoke an invalid session cookie", quiet=True)


async def check_logged_in(request: Request) -> bool:
    """Checks whether a user is signed in (on Firebase, with email and password)
    NOTE: This function is a coroutine, unlike `onehacks.auth.discord.check_logged_in`"""
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return False

    try:
        verify_session_cookie = partial(
            auth.verify_session_cookie, session_cookie, check_revoked=True
        )
        decoded_claims = await app.loop.run_in_executor(None, verify_session_cookie)
        return True
    except auth.InvalidSessionCookieError:
        return False


# TODO: make delete, update user functions
