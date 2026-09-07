import os

from flask import Flask

from config import Config

from .csrf import init_csrf
from .icons import category_icon_name, icon_url
from .models import db


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    if not app.debug and (
        app.config["SECRET_KEY"] == "dev-secret-key-change-me"
        or app.config["STAFF_PASSWORD"] == "hunter-decals"
    ):
        app.logger.warning(
            "Running with a default SECRET_KEY and/or staff password outside debug mode - "
            "set SECRET_KEY and DECAL_VAULT_STAFF_PASSWORD before this is reachable off your machine."
        )

    app.jinja_env.globals["icon_url"] = icon_url
    app.jinja_env.globals["category_icon_name"] = category_icon_name

    db.init_app(app)
    init_csrf(app)

    from . import routes

    app.register_blueprint(routes.bp)

    with app.app_context():
        db.create_all()

    return app
