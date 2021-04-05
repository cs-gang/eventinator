from sanic import Blueprint
from sanic.request import Request
from sanic.response import html, HTTPResponse, redirect

from onehacks.server import app


event = Blueprint("event", url_prefix="/event")

# TODO: complete this


@event.route("/<event_id:int>")
async def event_by_id(request: Request, event_id: int) -> HTTPResponse:
    pass


app.blueprint(event)
