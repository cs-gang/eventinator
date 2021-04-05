from sanic import Blueprint
from sanic.request import Request
from sanic.response import redirect, HTTPResponse

from onehacks.auth import UnauthenticatedError
from onehacks.auth import discord
from onehacks.server import app


discord_bp = Blueprint("discord", url_prefix="/discord")


@discord_bp.route("/")
async def discord_login(request: Request) -> HTTPResponse:
    url = await discord.redirect_to_oauth2(request)
    return redirect(url)


@discord_bp.route("/callback")
async def discord_callback(request: Request) -> HTTPResponse:
    response = await discord.handle_callback(request)
    if not response:
        raise UnauthenticatedError("Authentication failed.", status_code=401)
    else:
        url = app.url_for("user.user_dashboard")
        return redirect(url)


app.blueprint(discord_bp)
