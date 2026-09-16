from flask import Flask

from .config import Config
from .db import initialize_database, seed_demo_data
from .routes.borrow import bp as borrow_bp
from .routes.dashboard import bp as dashboard_bp
from .routes.returns import bp as return_bp
from .routes.transfers import bp as transfer_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(borrow_bp)
    app.register_blueprint(return_bp)
    app.register_blueprint(transfer_bp)

    with app.app_context():
        initialize_database()
        seed_demo_data()

    return app
