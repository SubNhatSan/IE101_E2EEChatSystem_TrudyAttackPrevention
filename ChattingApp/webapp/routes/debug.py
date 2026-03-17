"""Debug routes (for testing)."""
from flask import Blueprint, jsonify
from storage import get_user, load_json, save_json, data_lock, USERS_FILE, GROUPS_FILE

debug_bp = Blueprint("debug", __name__, url_prefix="/api/debug")


@debug_bp.route("/users", methods=["GET"])
def debug_users():
    """Xem toàn bộ user data"""
    users = load_json(USERS_FILE)
    return jsonify(users)


@debug_bp.route("/reset-friends", methods=["POST"])
def debug_reset_friends():
    """Xoá tất cả friend relationships"""
    with data_lock:
        users = load_json(USERS_FILE)
        for user in users:
            users[user]["friends"] = []
            users[user]["requests"] = []
        save_json(USERS_FILE, users)
    return jsonify({"success": True, "message": "Đã xoá tất cả friends và requests"})


@debug_bp.route("/user/<username>", methods=["GET"])
def debug_user(username):
    """Xem chi tiết một user"""
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@debug_bp.route("/user/<username>/reset", methods=["POST"])
def debug_reset_user(username):
    """Reset một user (xoá friends và requests)"""
    with data_lock:
        users = load_json(USERS_FILE)
        if username not in users:
            return jsonify({"error": "User not found"}), 404
        users[username]["friends"] = []
        users[username]["requests"] = []
        save_json(USERS_FILE, users)
    return jsonify({"success": True, "message": f"Đã reset {username}"})


@debug_bp.route("/connected", methods=["GET"])
def debug_connected():
    """Xem ai đang online (placeholder - will be updated by main app)"""
    return jsonify({"connected_users": []})
