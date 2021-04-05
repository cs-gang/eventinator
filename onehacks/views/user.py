from sanic import Blueprint
from sanic.exceptions import ServerError
from sanic.request import Request
from sanic.response import html, HTTPResponse, redirect

from onehacks.auth import authorized, firebase, User, UnauthenticatedError
from onehacks.forms import DashboardForm, LoginForm, SignUpForm
from onehacks.server import app
from onehacks.utils import render_page, transform_tz

user = Blueprint("user", url_prefix="/user")


@user.post("/login")
async def email_login(request: Request) -> HTTPResponse:
    if request.method != "POST":
        raise ServerError(
            "Only POST requests are allowed to this route.", status_code=405
        )
    form = LoginForm(request)

    if form.validate():
        email = form.email.data
        password = form.password.data
        auth_data = await firebase.authenticate_user(
            app, email=email, password=password
        )

        request.ctx.session["firebase_auth_data"] = auth_data

        valid = await firebase.create_session_cookie(app, request, auth_data)

        if valid:
            url = app.url_for("user.user_dashboard")
            response = redirect(url)
            response.cookies["session"] = valid["session_cookie"]
            response.cookies["session"]["httponly"] = True
            response.cookies["session"]["secure"] = True
            response.cookies["session"]["expires"] = valid["expires"]
            return response

        raise UnauthenticatedError("Login failed", status_code=403)
    raise UnauthenticatedError("Form did not validate", status_code=403)


@user.post("/new")
async def email_signup(request: Request) -> HTTPResponse:
    if request.method != "POST":
        raise ServerError(
            "Only POST requests are allowed to this route.", status_code=405
        )

    form = SignUpForm(request)

    if form.validate():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        user = await User.on_firebase(
            app, username=username, email=email, password=password
        )
        auth_data = await firebase.authenticate_user(
            app, email=user.email, password=password
        )

        request.ctx.session["firebase_auth_data"] = auth_data

        valid = await firebase.create_session_cookie(app, request, auth_data)

        url = app.url_for("user.user_dashboard")
        response = redirect(url)
        response.cookies["session"] = valid["session_cookie"]
        response.cookies["session"]["httponly"] = True
        response.cookies["session"]["secure"] = True
        response.cookies["session"]["expires"] = valid["expires"]
        return response

    raise UnauthenticatedError("Form did not validate", status_code=403)


@user.post("/logout")
@authorized()
async def user_logout(request: Request, platform: str) -> HTTPResponse:
    if request.method != "POST":
        raise ServerError(
            "Only POST requests are allowed to this route.", status_code=405
        )
    del request.ctx.session["firebase_auth_data"]

    if platform == "firebase":
        await firebase.delete_session_cookie(app, request)
    url = app.url_for("index")
    response = redirect(url)
    del response.cookies["session"]

    return response


@user.get("/dashboard")
@authorized()
async def user_dashboard(request: Request, platform: str) -> HTTPResponse:
    form = DashboardForm(request)

    from_discord = True if platform == "discord" else False

    if from_discord:
        user = await User.from_discord(app, request)
    else:
        uid = request.ctx.session.get("firebase_auth_data").get("localId")
        user = await User.from_db(app, uid)

    events = await user.get_events(app)

    output = await render_page(
        app.ctx.env,
        file="dashboard.html",
        form=form,
        from_discord=from_discord,
        events=events,
        username=user.username,
        tz=user.tz,
    )
    return html(output)


@user.route("/tz", methods=["POST"])
@authorized()
async def set_user_tz(request: Request, platform: str):
    form = DashboardForm(request)
    from_discord = True if platform == "discord" else False

    if form.validate():
        tz = transform_tz(form.timezone.data)

        if from_discord:
            user = await User.from_discord(app, request)
        else:
            uid = request.ctx.session.get("firebase_auth_data").get("localId")
            user = await User.from_db(app, uid)

        await user.set_tz(app, tz)
        url = app.url_for("user.user_dashboard")
        return redirect(url)
    raise ServerError("Form didn't validate.", status_code=500)


app.blueprint(user)
