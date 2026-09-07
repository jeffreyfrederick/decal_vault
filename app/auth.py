import hmac
from functools import wraps

from flask import current_app, redirect, request, session, url_for


def is_staff():
    return session.get("staff_authenticated", False)


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_staff():
            return redirect(url_for("main.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def check_password(password):
    return hmac.compare_digest(password, current_app.config["STAFF_PASSWORD"])
