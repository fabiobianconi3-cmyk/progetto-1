"""
P&ID Management Tool - Lundbeck SOP
Flask web application for P&ID tag generation, verification, DXF extraction, and Excel import.
"""

import os
from flask import Flask, render_template

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Register blueprints
from modules.tag_generator import tag_bp
from modules.pid_verifier import verifier_bp
from modules.dxf_extractor import extractor_bp
from modules.dxf_importer import importer_bp

app.register_blueprint(tag_bp, url_prefix="/tags")
app.register_blueprint(verifier_bp, url_prefix="/verify")
app.register_blueprint(extractor_bp, url_prefix="/extract")
app.register_blueprint(importer_bp, url_prefix="/import")


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
