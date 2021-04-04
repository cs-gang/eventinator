from sanic import Blueprint
from sanic.request import Request
from sanic.response import html, HTTPResponse

from onehacks.server import app
from onehacks.utils import render_page
from onehacks.forms import LoginForm, SignInForm

user = Blueprint("user", url_prefix="/user")


@user.route("/login", methods=["POST"])
async def login(request: Request) -> HTTPResponse:
    form = LoginForm(request)
    # TODO: change rendered page, do firebase login logic here
    output = await render_page(app.ctx.env, file="index.html", form=form)
    return html(output)


@user.route("/new", methods=["POST"])
async def new(request: Request) -> HTTPResponse:
    form = SignInForm(request)
    # TODO: change rendered page, do firebase sign up logic here
    output = await render_page(app.ctx.env, file="index.html", form=form)
    return html(output)


app.blueprint(user)
