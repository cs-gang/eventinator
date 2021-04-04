import asyncio
import os

from dotenv import find_dotenv, load_dotenv
import firebase_admin
from firebase_admin import credentials
from jinja2 import Environment, PackageLoader, select_autoescape
from sanic import Sanic

from onehacks.database import Database


load_dotenv(find_dotenv())


app = Sanic("onehacks")
app.config.DB_URI = os.environ.get("DB_URI", "sqlite:///data.db")
app.ctx.db = Database(app)

# initializing firebase app
cred = credentials.Certificate("admin-sdk.json")
firebase = firebase_admin.initialize_app(cred)

# initializing jinja2 templates
app.ctx.env = Environment(
    loader=PackageLoader("onehacks", "templates"),
    autoescape=select_autoescape(["html"]),
    enable_async=True,
)

app.static("/static", "./onehacks/static")


@app.before_server_start
async def connect_db(app: Sanic, loop: asyncio.AbstractEventLoop) -> None:
    await app.ctx.db.connect()
    await app.ctx.db.initialize_tables()


@app.after_server_stop
async def disconnect_db(app: Sanic, loop: asyncio.AbstractEventLoop) -> None:
    await app.ctx.db.disconnect()
