"""
Negotiation Simulation — Unified FastAPI entry point.
======================================================
Single app serving student and admin dashboards with automatic
instructor access and optional DecisionLab SSO.

Run::

    uvicorn web.main:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent

for p in (_THIS_DIR, _PROJECT_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from starlette.middleware.base import BaseHTTPMiddleware

from web.routes.auth_routes import get_session

# ── Jinja2 setup ──────────────────────────────────────────────────────

_TEMPLATE_DIR = _THIS_DIR / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)

# Add custom filters
def format_number(value):
    """Format a number with commas."""
    try:
        num = float(value)
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num/1_000:.0f}K"
        return f"{num:,.0f}"
    except (ValueError, TypeError):
        return value

_jinja_env.filters["format_number"] = format_number


class TemplateRenderer:
    """Wrapper that mimics Starlette's Jinja2Templates interface."""

    def __init__(self, env: Environment):
        self._env = env

    def TemplateResponse(self, name: str, context: dict, status_code: int = 200):
        from starlette.responses import HTMLResponse
        template = self._env.get_template(name)
        html = template.render(**context)
        return HTMLResponse(content=html, status_code=status_code)


templates = TemplateRenderer(_jinja_env)


# ── FastAPI app ───────────────────────────────────────────────────────

app = FastAPI(title="Negotiation Simulation", docs_url=None, redoc_url=None)

# Static files
_STATIC_DIR = _THIS_DIR / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── Admin guard middleware ────────────────────────────────────────────

class AdminGuardMiddleware(BaseHTTPMiddleware):
    """Redirect non-admin users away from /admin routes."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/admin"):
            session = get_session(request)
            if not session or session.get("role") != "ADMIN":
                return RedirectResponse(url="/", status_code=302)
        return await call_next(request)


app.add_middleware(AdminGuardMiddleware)


# ── Include routers ──────────────────────────────────────────────────

from web.routes.auth_routes import router as auth_router
from web.routes.student_routes import router as student_router
from web.routes.admin_routes import router as admin_router

app.include_router(auth_router)
app.include_router(student_router)
app.include_router(admin_router)


# ── Demo provisioning ────────────────────────────────────────────────

@app.on_event("startup")
async def _provision_demo():
    """Ensure a demo simulation exists on startup."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from scripts.provision_demo import provision_demo
        provision_demo()
        logger.info("Demo simulation provisioned.")
    except Exception:
        logger.debug("Demo provisioning skipped (non-fatal).", exc_info=True)


__all__ = ["app", "templates"]
