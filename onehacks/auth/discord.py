import os
from functools import partial
from typing import Callable

from async_oauthlib import OAuth2Session
from dotenv import find_dotenv, load_dotenv
from sanic import Sanic
from sanic.request import Request

load_dotenv(find_dotenv())


CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8000/discord/callback")

API_BASE_URL = "https://discord.com/api"
AUTHORIZATION_BASE_URL = API_BASE_URL + "/oauth2/authorize"
TOKEN_URL = API_BASE_URL + "/oauth2/token"


def make_session(
    *, token: dict = None, state: dict = None, token_updater: Callable = None
) -> OAuth2Session:
    # token_updater should be a function which will update the token in the session
    return OAuth2Session(
        client_id=CLIENT_ID,
        token=token,
        state=state,
        redirect_uri=REDIRECT_URI,
        scope=["identify", "email"],
        auto_refresh_kwargs={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        token_updater=token_updater,
        auto_refresh_url=TOKEN_URL,
    )


def token_updater(request: Request, token: dict) -> None:
    # has to be made into a partial function before use
    request.ctx.session["discord_oauth2_token"] = token


async def redirect_to_oauth2(request: Request) -> str:
    """
    Returns the URL to the Discord OAuth2 page.
    Arguments ::
        request: Request
    Returns ::
        str
    """
    discord = make_session(token_updater=partial(token_updater, request))
    url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    request.ctx.session["discord_oauth2_state"] = state
    return url


async def handle_callback(request: Request) -> bool:
    """
    Handles the callback request sent by Discord.
    Returns boolean depending on whether the authentication was succesful.
    Arguments ::
        request: Request
    Note that this will modify the request object and add the oauth2_token to it's session.
    """
    if request.args.get("error"):
        return False

    discord = make_session(
        state=request.ctx.session.get("discord_oauth2_state"),
        token_updater=partial(token_updater, request),
    )
    token = await discord.fetch_token(
        TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url
    )
    request.ctx.session["discord_oauth2_token"] = token
    return True
