"""ASGI application entry point."""

from app.api.app import create_app

app = create_app()
