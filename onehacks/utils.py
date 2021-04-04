from typing import Any

from jinja2 import Environment


async def render_page(environment: Environment, *, file: str, **context: Any) -> str:
    """Helper function to render the template.
    Use to give final output in the route functions."""
    template = environment.get_template(file)
    return await template.render_async(**context)
