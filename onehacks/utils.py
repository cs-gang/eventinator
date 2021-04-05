from typing import Any
from time import time

from jinja2 import Environment


async def render_page(environment: Environment, *, file: str, **context: Any) -> str:
    """Helper function to render the template.
    Use to give final output in the route functions."""
    template = environment.get_template(file)
    return await template.render_async(**context)


class IDGenerator:
    """Snowflake generator.
    Used for making both user and event IDs."""

    def __init__(self):
        self.wid = 0
        self.inc = 0

    def __next__(self) -> int:
        t = round(time() * 1000) - 1609459200000
        self.inc += 1
        return (t << 14) | (self.wid << 6) | (self.inc % 2 ** 6)
