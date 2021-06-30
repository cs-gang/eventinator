from typing import Optional, Union

from sanic import Blueprint
from sanic.exceptions import ServerError
from sanic.request import Request
from sanic.response import html, HTTPResponse, redirect

from src.auth import authorized, guest_or_authorized, User
from src.events import Event
from src.forms import EventCreationForm, LeaveEventForm
from src.server import app
from src.utils import render_page


event = Blueprint("event", url_prefix="/event")

# TODO: complete this


@event.get("/<event_id:int>")
@guest_or_authorized()
async def event_by_id(
    request: Request, event_id: int, user: Union[User, str], platform: Optional[str]
) -> HTTPResponse:
    event = await Event.by_id(app, str(event_id))
    owner = await User.from_db(app, _id=event.event_owner)

    if isinstance(user, User):
        # the user is logged in, display all the details
        user_tz = user.tz
        event_members_names = await event.get_members_usernames(app)
    else:
        # not logged in, show only minimal info
        user_tz = None
        event_members_names = None

    output = await render_page(
        app.ctx.env,
        file="event-display.html",
        event=event,
        event_members=event_members_names,
        user_tz=user_tz,
        owner_tz=owner.tz,
    )

    return html(output)


@event.post("/leave")
@authorized()
async def leave_event(request: Request, user: User, platform: str) -> HTTPResponse:
    form = LeaveEventForm(request)

    if form.validate():
        event = await Event.by_id(app, form.event_id.data)
        await user.join_event(app, event)
        return redirect("user.dashboard")
    else:
        raise ServerError("Form did not validate.", status_code=500)


@event.route("/new", methods=["GET", "POST"])
@authorized()
async def new_event(request: Request, user: User, platform: str) -> HTTPResponse:
    form = EventCreationForm(request)
    if request.method == "POST":
        if form.validate():
            event_id = str(next(app.ctx.snowflake))
            details = dict(
                event_id=event_id,
                event_name=form.eventname.data,
                event_owner=user.uid,
                start_time=form.starttime.data,
                end_time=form.endtime.data,
                long_desc=form.longdescription.data,
                short_desc=form.shortdescription.data,
            )

            await Event(**details).create(app)

            url = app.url_for("event.event_by_id", event_id=event_id)

            return redirect(url)
        else:
            raise ServerError("Form didn't validate.", status_code=500)
    else:
        output = await render_page(app.ctx.env, file="event-creation.html", form=form)
        return html(output)


app.blueprint(event)
