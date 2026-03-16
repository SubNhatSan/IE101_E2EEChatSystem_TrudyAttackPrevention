import json
import os
import threading

from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")

os.makedirs(DATA_DIR, exist_ok=True)

# Ensure data files exist
for path in (USERS_FILE, GROUPS_FILE):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)

app = Flask(__name__, template_folder="templates", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

data_lock = threading.Lock()

# In-memory connected users: username -> sid
connected_users = {}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(username):
    users = load_json(USERS_FILE)
    user = users.get(username)
    if not user:
        return None

    # Ensure default fields exist (backwards compatible)
    user.setdefault("friends", [])
    user.setdefault("groups", [])
    user.setdefault("requests", [])
    return user


def set_user(username, data):
    users = load_json(USERS_FILE)
    users[username] = data
    save_json(USERS_FILE, users)


def are_friends(user_a, user_b):
    if not user_a or not user_b:
        return False
    user = get_user(user_a)
    return user and user_b in user.get("friends", [])


def get_group(group_id):
    groups = load_json(GROUPS_FILE)
    return groups.get(group_id)


def set_group(group_id, data):
    groups = load_json(GROUPS_FILE)
    groups[group_id] = data
    save_json(GROUPS_FILE, groups)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def api_register():
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


@app.route("/api/login", methods=["POST"])
def api_login():
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


@app.route("/api/users")
def api_users():
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


@app.route("/api/friends", methods=["GET"])
def api_friends():
    username = (request.args.get("me") or "").strip()
    if not username:
        return jsonify({"friends": []})

    user = get_user(username)
    return jsonify({"friends": user.get("friends", []) if user else []})


@app.route("/api/friends/requests", methods=["GET"])
def api_friend_requests():
    username = (request.args.get("me") or "").strip()
    if not username:
        return jsonify({"requests": []})

    user = get_user(username)
    return jsonify({"requests": user.get("requests", []) if user else []})


@app.route("/api/friends/request", methods=["POST"])
def api_friend_request():
    try:
        payload = request.get_json(force=True)
        username = (payload.get("me") or "").strip()
        target = (payload.get("to") or "").strip()

        print(f"[DEBUG] Friend request - from: {username}, to: {target}, payload: {payload}")

        if not username or not target:
            print(f"[DEBUG] Missing info - username: '{username}', target: '{target}'")
            return jsonify({"success": False, "message": "Thiếu thông tin."}), 400

        if username == target:
            print(f"[DEBUG] Same user - cannot send to self")
            return jsonify({"success": False, "message": "Không thể gửi yêu cầu cho chính bạn."}), 400

        with data_lock:
            users = load_json(USERS_FILE)
            print(f"[DEBUG] Users in DB: {list(users.keys())}")
            
            if username not in users or target not in users:
                print(f"[DEBUG] User not found")
                return jsonify({"success": False, "message": "Người dùng không tồn tại."}), 404

            # Nếu đã là bạn, không cần gửi request
            friends_list = users[username].get("friends", [])
            print(f"[DEBUG] {username} friends: {friends_list}")
            if target in friends_list:
                print(f"[DEBUG] Already friends")
                return jsonify({"success": False, "message": "Đã là bạn bè."}), 400

            # Thêm vào danh sách request của người nhận nếu chưa có
            reqs = users[target].setdefault("requests", [])
            print(f"[DEBUG] {target} current requests: {reqs}")
            if username in reqs:
                print(f"[DEBUG] Already sent request")
                return jsonify({"success": False, "message": "Đã gửi yêu cầu trước đó."}), 400

            reqs.append(username)
            save_json(USERS_FILE, users)
            print(f"[DEBUG] Friend request sent successfully - {username} -> {target}")

            # Notify recipient if they are online
            target_sid = connected_users.get(target)
            print(f"[DEBUG] Target {target} connected: {target_sid is not None}")
            if target_sid:
                socketio.emit(
                    "friend_request",
                    {"from": username},
                    to=target_sid,
                )

        return jsonify({"success": True, "message": "Đã gửi yêu cầu kết bạn."})
    
    except Exception as e:
        print(f"[ERROR] Friend request error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500


@app.route("/api/friends/respond", methods=["POST"])
def api_friend_respond():
    payload = request.get_json(force=True)
    username = (payload.get("me") or "").strip()
    requester = (payload.get("from") or "").strip()
    accept = payload.get("accept") is True

    if not username or not requester:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400

    with data_lock:
        users = load_json(USERS_FILE)
        if username not in users or requester not in users:
            return jsonify({"success": False, "message": "Người dùng không tồn tại."}), 404

        reqs = users[username].setdefault("requests", [])
        if requester not in reqs:
            return jsonify({"success": False, "message": "Không có yêu cầu này."}), 400

        reqs.remove(requester)

        if accept:
            users[username].setdefault("friends", [])
            users[requester].setdefault("friends", [])
            if requester not in users[username]["friends"]:
                users[username]["friends"].append(requester)
            if username not in users[requester]["friends"]:
                users[requester]["friends"].append(username)

        save_json(USERS_FILE, users)

    return jsonify({"success": True, "message": "Đã xử lý yêu cầu."})


@app.route("/api/friends/add", methods=["POST"])
def api_friends_add():
    payload = request.get_json(force=True)
    username = (payload.get("me") or "").strip()
    friend = (payload.get("friend") or "").strip()

    if not username or not friend:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400

    with data_lock:
        users = load_json(USERS_FILE)
        if username not in users or friend not in users:
            return jsonify({"success": False, "message": "Người dùng không tồn tại."}), 404

        if friend not in users[username].get("friends", []):
            users[username].setdefault("friends", []).append(friend)
        if username not in users[friend].get("friends", []):
            users[friend].setdefault("friends", []).append(username)

        save_json(USERS_FILE, users)

    return jsonify({"success": True, "message": "Đã thêm bạn bè."})


@app.route("/api/groups", methods=["GET"])
def api_groups():
    username = (request.args.get("me") or "").strip()
    if not username:
        return jsonify({"groups": []})

    groups = load_json(GROUPS_FILE)
    result = []
    for gid, g in groups.items():
        if username in g.get("members", []):
            result.append({"id": gid, "name": g.get("name"), "members": g.get("members", [])})

    return jsonify({"groups": result})


@app.route("/api/groups/create", methods=["POST"])
def api_groups_create():
    payload = request.get_json(force=True)
    owner = (payload.get("me") or "").strip()
    name = (payload.get("name") or "").strip()
    members = payload.get("members") or []

    if not owner or not name or not members:
        return jsonify({"success": False, "message": "Thiếu thông tin tạo nhóm."}), 400

    # Ensure owner is in members list
    if owner not in members:
        members.append(owner)

    with data_lock:
        groups = load_json(GROUPS_FILE)
        group_id = f"group_{len(groups) + 1}"
        groups[group_id] = {"name": name, "members": list(dict.fromkeys(members))}
        save_json(GROUPS_FILE, groups)

        users = load_json(USERS_FILE)
        for u in members:
            if u in users:
                users[u].setdefault("groups", [])
                if group_id not in users[u]["groups"]:
                    users[u]["groups"].append(group_id)
        save_json(USERS_FILE, users)

    return jsonify({"success": True, "group": {"id": group_id, "name": name, "members": members}})


@socketio.on("connect")
def ws_connect():
    # Try to get username from query parameters
    username = request.args.get("username")
    
    # Debug: log what we're receiving
    print(f"[WS DEBUG] Connection attempt - request.args: {dict(request.args)}")
    print(f"[WS DEBUG] Extracted username: {username}")
    
    if not username:
        print(f"[WS ERROR] Connection rejected - no username provided")
        return False

    connected_users[username] = request.sid
    print(f"[WS] {username} connected ({request.sid})")
    print(f"[WS DEBUG] Connected users now: {list(connected_users.keys())}")


@socketio.on("disconnect")
def ws_disconnect():
    username = None
    for u, sid in list(connected_users.items()):
        if sid == request.sid:
            username = u
            break
    if username:
        del connected_users[username]
        print(f"[WS] {username} disconnected")
        print(f"[WS DEBUG] Connected users now: {list(connected_users.keys())}")


@socketio.on("authenticate")
def ws_authenticate(data):
    """Fallback method to authenticate if query parameter fails"""
    username = data.get("username") if isinstance(data, dict) else None
    print(f"[WS DEBUG] Authentication attempt via event: {username}, sid: {request.sid}")
    
    if not username:
        print(f"[WS ERROR] Authentication failed - no username")
        emit("auth_error", {"message": "No username provided"})
        return False
    
    # Check if this sid is already associated with another user
    existing_user = None
    for u, sid in connected_users.items():
        if sid == request.sid:
            existing_user = u
            break
    
    if existing_user and existing_user != username:
        print(f"[WS WARNING] User {username} already connected as {existing_user}, replacing")
        del connected_users[existing_user]
    
    connected_users[username] = request.sid
    print(f"[WS] {username} authenticated via event ({request.sid})")
    print(f"[WS DEBUG] Connected users now: {list(connected_users.keys())}")
    emit("auth_success", {"message": f"Authenticated as {username}"})


@socketio.on("send_message")
def ws_send_message(payload):
    # payload: {type, to, groupId?, text, clientId, from}
    sender = payload.get("from")
    msg_type = payload.get("type")
    text = payload.get("text")
    client_id = payload.get("clientId")

    # Ack to sender
    emit("message_ack", {"clientId": client_id})

    if msg_type == "private":
        to_user = payload.get("to")
        # Only allow private messages between friends
        if not are_friends(sender, to_user):
            emit(
                "message",
                {
                    "from": "System",
                    "type": "private",
                    "text": "Bạn chưa là bạn bè. Gửi yêu cầu kết bạn trước khi trò chuyện.",
                },
            )
            return

        sid = connected_users.get(to_user)
        if sid:
            emit(
                "message",
                {"from": sender, "to": to_user, "type": "private", "text": text},
                to=sid,
            )

    elif msg_type == "group":
        # broadcast to all connected except sender
        for u, sid in connected_users.items():
            if u != sender:
                emit(
                    "message",
                    {"from": sender, "type": "group", "text": text},
                    to=sid,
                )

    elif msg_type == "groupchat":
        group_id = payload.get("groupId")
        groups = load_json(GROUPS_FILE)
        group = groups.get(group_id)
        if not group:
            return
        for member in group.get("members", []):
            if member == sender:
                continue
            sid = connected_users.get(member)
            if sid:
                emit(
                    "message",
                    {
                        "from": sender,
                        "type": "groupchat",
                        "groupId": group_id,
                        "groupName": group.get("name"),
                        "text": text,
                    },
                    to=sid,
                )

# ===== DEBUG/TEST ENDPOINTS =====
@app.route("/api/debug/users", methods=["GET"])
def debug_users():
    """Xem toàn bộ user data"""
    users = load_json(USERS_FILE)
    return jsonify(users)


@app.route("/api/debug/reset-friends", methods=["POST"])
def debug_reset_friends():
    """Xoá tất cả friend relationships"""
    with data_lock:
        users = load_json(USERS_FILE)
        for user in users:
            users[user]["friends"] = []
            users[user]["requests"] = []
        save_json(USERS_FILE, users)
    return jsonify({"success": True, "message": "Đã xoá tất cả friends và requests"})


@app.route("/api/debug/user/<username>", methods=["GET"])
def debug_user(username):
    """Xem chi tiết một user"""
    user = get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@app.route("/api/debug/user/<username>/reset", methods=["POST"])
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


@app.route("/api/debug/connected", methods=["GET"])
def debug_connected():
    """Xem ai đang online"""
    return jsonify({"connected_users": list(connected_users.keys())})


if __name__ == "__main__":
    print("[+] Starting web chat server on http://127.0.0.1:5000")
    socketio.run(app, host="127.0.0.1", port=5000)


