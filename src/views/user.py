from sanic import Blueprint
from sanic.exceptions import ServerError
from sanic.request import Request
from sanic.response import html, HTTPResponse, redirect

from src.forms import DashboardForm, LoginForm, SignUpForm, EventActionForm
from src.auth import authorized, firebase, User, UnauthenticatedError
from src.server import app
from src.utils import render_page, transform_tz

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


@user.route("/logout")
@authorized()
async def user_logout(request: Request, user: User, platform: str) -> HTTPResponse:
    url = app.url_for("index")
    response = redirect(url)

    if platform == "firebase":
        del request.ctx.session["firebase_auth_data"]
        await firebase.delete_session_cookie(app, request)
    elif platform == "discord":
        del response.cookies["session"]

    return response


@user.get("/dashboard")
@authorized()
async def user_dashboard(request: Request, user: User, platform: str) -> HTTPResponse:
    dashboard_form = DashboardForm(request)
    delete_form = EventActionForm(request)

    all_events = await user.get_events(app)
    owned_events = await user.get_owned_events(app)
    from_discord = True if platform == "discord" else False

    output = await render_page(
        app.ctx.env,
        file="dashboard.html",
        dashboard_form=dashboard_form,
        delete_event_form=delete_form,
        from_discord=from_discord,
        all_events=all_events,
        owned_events=owned_events,
        username=user.username,
        tz=user.tz,
    )
    return html(output)


@user.route("/tz", methods=["POST"])
@authorized()
async def set_user_tz(request: Request, user: User, platform: str) -> HTTPResponse:
    form = DashboardForm(request)

    if form.validate():
        tz = transform_tz(form.timezone.data)

        await user.set_tz(app, tz)
        url = app.url_for("user.user_dashboard")
        return redirect(url)
    raise ServerError("Form didn't validate.", status_code=500)


app.blueprint(user)
