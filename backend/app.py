import os

from flask import Flask, send_from_directory

from backend.blueprints.events import events_bp
from backend.blueprints.tokens import tokens_bp
from backend.config import Config


def create_app():
    app = Flask(__name__, static_folder=None)

    app.register_blueprint(events_bp)
    app.register_blueprint(tokens_bp)

    static_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    )

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        if path.startswith("api/"):
            return {"error": "Not found"}, 404
        file_path = os.path.join(static_dir, path) if path else os.path.join(static_dir, "index.html")
        if path and os.path.exists(file_path):
            return send_from_directory(static_dir, path)
        return send_from_directory(static_dir, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT)
