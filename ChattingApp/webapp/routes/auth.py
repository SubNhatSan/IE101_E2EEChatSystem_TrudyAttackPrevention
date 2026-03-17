"""Auth routes."""
from flask import Blueprint, request, jsonify, render_template
from storage import get_user, load_json, save_json, data_lock, USERS_FILE

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


@auth_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@auth_bp.route("/register", methods=["POST"])
def register():
    payload = request.get_json(force=True)
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username và password không được để trống."}), 400

    with data_lock:
        users = load_json(USERS_FILE)
        if username in users:
            return jsonify({"success": False, "message": "Username đã tồn tại."}), 400

        users[username] = {"password": password, "friends": [], "groups": [], "requests": []}
        save_json(USERS_FILE, users)

    return jsonify({"success": True, "message": "Đăng ký thành công."})


@auth_bp.route("/login", methods=["POST"])
def login():
    payload = request.get_json(force=True)
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username và password không được để trống."}), 400

    users = load_json(USERS_FILE)
    user = users.get(username)
    if not user or user.get("password") != password:
        return jsonify({"success": False, "message": "Tên đăng nhập hoặc mật khẩu sai."}), 401

    return jsonify({
        "success": True,
        "user": {
            "username": username,
            "friends": user.get("friends", []),
            "groups": user.get("groups", []),
            "requests": user.get("requests", []),
        },
    })


@auth_bp.route("/users", methods=["GET"])
def get_users():
    query = (request.args.get("q") or "").strip().lower()
    me = (request.args.get("me") or "").strip()

    users = load_json(USERS_FILE)
    result = []
    for u in users:
        if u == me:
            continue
        if query and query not in u.lower():
            continue
        result.append(u)

    return jsonify({"users": sorted(result)})
