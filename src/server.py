import asyncio
import os

from dotenv import find_dotenv, load_dotenv
import firebase_admin
from firebase_admin import credentials
from jinja2 import Environment, PackageLoader, select_autoescape
from sanic import Sanic
from sanic_session import Session, InMemorySessionInterface

from src.database import Database
from src.utils import IDGenerator


load_dotenv(find_dotenv())


app = Sanic("eventinator")

app.config.DB_URI = os.environ.get("DB_URI", "sqlite:///data.db")
app.ctx.db = Database(app)

# initializing firebase app
cred = credentials.Certificate("admin-sdk.json")
app.ctx.firebase = firebase_admin.initialize_app(cred)
app.config.FIREBASE_API_KEY = os.environ.get("FIREBASE_WEB_API_KEY")

# initializing jinja2 templates
app.ctx.env = Environment(
    loader=PackageLoader("src", "templates"),
    autoescape=select_autoescape(["html"]),
    enable_async=True,
)

# make snowflake generator instance
app.ctx.snowflake = IDGenerator()

# initialize sessions
Session(
    app,
    interface=InMemorySessionInterface(
        sessioncookie=True, cookie_name="plantech", expiry=3600
    ),
)

# csrf config
app.config["WTF_CSRF_SECRET_KEY"] = os.environ.get("CSRF_TOKEN")


app.static("/static", "./src/static")


@app.before_server_start
async def connect_db(app: Sanic, loop: asyncio.AbstractEventLoop) -> None:
    await app.ctx.db.connect()
    await app.ctx.db.initialize_tables()


@app.after_server_stop
async def disconnect_db(app: Sanic, loop: asyncio.AbstractEventLoop) -> None:
    await app.ctx.db.disconnect()
