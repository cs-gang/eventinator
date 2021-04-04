from sanic.request import Request
from sanic.response import html, HTTPResponse

from onehacks.server import app
from onehacks.utils import render_page


@app.route("/")
async def index(request: Request) -> HTTPResponse:
    output = await render_page(app.ctx.env, file="index.html")
    return html(output)
