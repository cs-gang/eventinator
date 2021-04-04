from sanic import Blueprint
from sanic.request import Request
from sanic.response import html, HTTPResponse

from onehacks.server import app
from onehacks.utils import render_page
from onehacks.forms import LoginForm, SignInForm

bp = Blueprint("user")


@bp.route("/login", methods=["POST"])
async def login(request: Request) -> HTTPResponse:
    form = LoginForm(request)
    output = await render_page(app.ctx.env, file="index.html", form=form)
    return htmp(output)


@bp.route("/new", methods=["POST"])
async def new(request: Request) -> HTTPResponse:
    form = SignInForm(request)
    output = await render_page(app.ctx.env, file="index.html", form=form)
    return htmp(output)
