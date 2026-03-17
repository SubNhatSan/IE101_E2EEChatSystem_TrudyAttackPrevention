"""Groups routes."""
from flask import Blueprint, request, jsonify
from storage import get_group, set_group, delete_group, load_json, save_json, data_lock, GROUPS_FILE, USERS_FILE

groups_bp = Blueprint("groups", __name__, url_prefix="/api/groups")


@groups_bp.route("", methods=["GET"])
def get_groups():
    username = (request.args.get("me") or "").strip()
    if not username:
        return jsonify({"groups": []})

    groups = load_json(GROUPS_FILE)
    result = []
    for gid, g in groups.items():
        if username in g.get("members", []):
            result.append({
                "id": gid, 
                "name": g.get("name"), 
                "members": g.get("members", []),
                "owner": g.get("owner", "")
            })

    return jsonify({"groups": result})


@groups_bp.route("/create", methods=["POST"])
def create_group():
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
        groups[group_id] = {
            "name": name, 
            "members": list(dict.fromkeys(members)),
            "owner": owner  # Add owner field
        }
        save_json(GROUPS_FILE, groups)

        users = load_json(USERS_FILE)
        for u in members:
            if u in users:
                users[u].setdefault("groups", [])
                if group_id not in users[u]["groups"]:
                    users[u]["groups"].append(group_id)
        save_json(USERS_FILE, users)

    return jsonify({"success": True, "group": {"id": group_id, "name": name, "members": members, "owner": owner}})


@groups_bp.route("/delete", methods=["POST"])
def delete_group_route():
    """Delete a group (only owner can delete)."""
    payload = request.get_json(force=True)
    user = (payload.get("me") or "").strip()
    group_id = (payload.get("groupId") or "").strip()

    if not user or not group_id:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400

    with data_lock:
        groups = load_json(GROUPS_FILE)
        group = groups.get(group_id)
        
        if not group:
            return jsonify({"success": False, "message": "Nhóm không tồn tại."}), 404
        
        # Check if user is the owner
        if group.get("owner") != user:
            return jsonify({"success": False, "message": "Chỉ chủ sở hữu nhóm mới có thể xoá nhóm."}), 403
        
        # Delete the group
        if delete_group(group_id):
            # Remove group from all members' groups list
            users = load_json(USERS_FILE)
            for member in group.get("members", []):
                if member in users and group_id in users[member].get("groups", []):
                    users[member]["groups"].remove(group_id)
            save_json(USERS_FILE, users)
            
            return jsonify({"success": True, "message": "Đã xoá nhóm."})
        else:
            return jsonify({"success": False, "message": "Lỗi khi xoá nhóm."}), 500
