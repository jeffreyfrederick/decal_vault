import secrets

from flask import abort, request, session


def _get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["csrf_token"] = token
    return token


def init_csrf(app):
    app.jinja_env.globals["csrf_token"] = _get_csrf_token

    @app.before_request
    def _check_csrf():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return
        expected = session.get("csrf_token")
        submitted = request.form.get("csrf_token")
        if not expected or not submitted or not secrets.compare_digest(expected, submitted):
            abort(400, description="Missing or invalid CSRF token.")
