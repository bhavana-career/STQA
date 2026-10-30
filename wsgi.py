"""WSGI entry point: `gunicorn wsgi:app` (production) / `flask --app wsgi run` (local)."""
from app import create_app

app = create_app()
