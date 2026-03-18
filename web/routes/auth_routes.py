"""
Auth routes — login, logout, session management.
==================================================
"""

from __future__ import annotations

import os
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import URLSafeSerializer

from app.auth.login_manager import login

router = APIRouter()

SESSION_SECRET = os.environ.get("SESSION_SECRET", "negotiation-sim-dev-secret")
COOKIE_NAME = "neg_session"
_signer = URLSafeSerializer(SESSION_SECRET, salt="neg-session")


def get_session(request: Request) -> dict | None:
    """Read and verify the session cookie."""
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        return _signer.loads(raw)
    except Exception:
        return None


def set_session_cookie(response, session_data: dict):
    """Set a signed session cookie on the response."""
    token = _signer.dumps(session_data)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return response


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    session = get_session(request)
    if session:
        if session.get("role") == "ADMIN":
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    from web.main import templates
    session = get_session(request)
    if session:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": None,
    })


@router.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    from web.main import templates
    result = login(username, password)
    if not result.success:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": result.message,
        })

    user = result.user
    session_data = {
        "username": user.username,
        "user_id": user.user_id,
        "role": user.role,
        "sim_id": user.sim_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "dashboard": user.dashboard,
    }

    if user.dashboard == "admin":
        response = RedirectResponse(url="/admin", status_code=302)
    else:
        response = RedirectResponse(url="/dashboard", status_code=302)

    return set_session_cookie(response, session_data)


@router.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response
