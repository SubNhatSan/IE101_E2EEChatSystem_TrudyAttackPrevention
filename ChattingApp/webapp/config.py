"""Application configuration."""
import os

# Flask config
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_TYPE = "filesystem"
PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days

# Socket.IO config
SOCKETIO_CORS_ALLOWED_ORIGINS = "*"

# App config
DEBUG = os.environ.get("FLASK_DEBUG", "False") == "True"
HOST = os.environ.get("FLASK_HOST", "0.0.0.0")  # Listen on all interfaces
PORT = int(os.environ.get("FLASK_PORT", 5000))
