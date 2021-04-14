from sanic import Blueprint
from sanic.exceptions import ServerError
from sanic.request import Request
from sanic.response import html, json, HTTPResponse, redirect  # TODO: change json

from onehacks.auth import authorized, User
from onehacks.events import Event
from onehacks.forms import EventCreationForm
from onehacks.server import app
from onehacks.utils import render_page


event = Blueprint("event", url_prefix="/event")

# TODO: complete this


@event.route("/<event_id:int>")
async def event_by_id(request: Request, event_id: int) -> HTTPResponse:
    event_data = await Event.by_id(app, str(event_id))
    return json({"event name": event_data.event_name})


@event.route("/new", methods=["GET", "POST"])
@authorized()
async def new_event(request: Request, user: User, platform: str) -> HTTPResponse:
    form = EventCreationForm(request)
    print(request.form)
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
