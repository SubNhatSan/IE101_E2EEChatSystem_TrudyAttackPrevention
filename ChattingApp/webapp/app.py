"""Flask web chat application entry point."""
import os
from flask import Flask, render_template
from flask_session import Session

# Initialize storage
from storage import ensure_data_files

# Initialize extensions
from extensions import socketio
from config import SECRET_KEY, SESSION_TYPE, PERMANENT_SESSION_LIFETIME, HOST, PORT

# Import routes and sockets
from routes import auth_bp, friends_bp, groups_bp, messages_bp, debug_bp, set_friends_connected_users
from sockets import register_socket_handlers, get_connected_users

# Create Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")

# Configure app
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SESSION_TYPE"] = SESSION_TYPE
app.config["PERMANENT_SESSION_LIFETIME"] = PERMANENT_SESSION_LIFETIME

# Initialize extensions
socketio.init_app(app, cors_allowed_origins="*")
Session(app)

# Initialize storage
ensure_data_files()

# Register routes
@app.route("/")
def index():
    return render_template("index.html")

app.register_blueprint(auth_bp)
app.register_blueprint(friends_bp)
app.register_blueprint(groups_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(debug_bp)

# Register socket handlers
register_socket_handlers()

# Connect friends route to connected_users
set_friends_connected_users(get_connected_users())

# Debug endpoint for connected users
from flask import jsonify

@app.route("/api/debug/connected", methods=["GET"])
def debug_connected_users():
    """Xem ai đang online"""
    connected = get_connected_users()
    return jsonify({"connected_users": list(connected.keys())})


if __name__ == "__main__":
    print(f"[+] Starting web chat server on http://{HOST}:{PORT}")
    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )


