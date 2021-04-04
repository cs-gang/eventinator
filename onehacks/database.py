from databases import Database as _Database
from sanic import Sanic

# TODO: Complete query functions, make models and migrations.


class Database:
    """Represents a connection to the underlying database.
    To be added as an attribute of `app.ctx`"""

    def __init__(self, app: Sanic) -> None:
        """
        Initializes a database instance.
        The database does not CONNECT until the `Database.connect` coroutine is called.

        Arguments ::
            app: Sanic -> The running Sanic instance.
                Note: The database URI must be set to the `config` of the Sanic instance.
        """
        self.db = _Database(app.config.DB_URI)

    async def connect(self) -> None:
        """Establishes the connection with the database."""
        await self.db.connect()

    async def initialize_tables(self) -> None:
        """Creates the tables in the database if they haven't been made already."""
        raise NotImplementedError
