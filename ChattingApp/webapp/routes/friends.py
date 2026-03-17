"""Friends routes."""
from flask import Blueprint, request, jsonify
from storage import get_user, set_user, load_json, save_json, data_lock, USERS_FILE, are_friends, remove_friend
from extensions import socketio

friends_bp = Blueprint("friends", __name__, url_prefix="/api/friends")

# Will be populated by main app
connected_users = {}


def set_connected_users(users_dict):
    """Set reference to connected_users from main app."""
    global connected_users
    connected_users = users_dict


@friends_bp.route("", methods=["GET"])
def get_friends():
    username = (request.args.get("me") or "").strip()
    if not username:
        return jsonify({"friends": []})

    user = get_user(username)
    return jsonify({"friends": user.get("friends", []) if user else []})


@friends_bp.route("/requests", methods=["GET"])
def get_friend_requests():
    username = (request.args.get("me") or "").strip()
    if not username:
        return jsonify({"requests": []})

    user = get_user(username)
    return jsonify({"requests": user.get("requests", []) if user else []})


@friends_bp.route("/request", methods=["POST"])
def send_friend_request():
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


@friends_bp.route("/respond", methods=["POST"])
def respond_friend_request():
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
        
        # Notify requester in real-time if they are online
        if accept:
            requester_sid = connected_users.get(requester)
            if requester_sid:
                socketio.emit(
                    "friend_accepted",
                    {"from": username},
                    to=requester_sid,
                )

    return jsonify({"success": True, "message": "Đã xử lý yêu cầu."})


@friends_bp.route("/add", methods=["POST"])
def add_friend():
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


@friends_bp.route("/remove", methods=["POST"])
def remove_friend_route():
    """Remove a friend (bilateral)."""
    payload = request.get_json(force=True)
    username = (payload.get("me") or "").strip()
    friend = (payload.get("friend") or "").strip()

    if not username or not friend:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400

    if username == friend:
        return jsonify({"success": False, "message": "Không thể xoá chính bạn."}), 400

    success = remove_friend(username, friend)
    if success:
        return jsonify({"success": True, "message": "Đã xoá bạn bè."})
    else:
        return jsonify({"success": False, "message": "Người dùng không tồn tại hoặc không phải bạn bè."}), 404
