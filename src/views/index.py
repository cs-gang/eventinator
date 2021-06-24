from sanic.request import Request
from sanic.response import html, HTTPResponse

from src.forms import LoginForm, SignUpForm
from src.server import app
from src.utils import render_page


@app.route("/")
async def index(request: Request) -> HTTPResponse:
    login_form = LoginForm(request)
    signup_form = SignUpForm(request)
    output = await render_page(
        app.ctx.env, file="index.html", login_form=login_form, signup_form=signup_form
    )
    return HTTPResponse(output, content_type="text/html")
