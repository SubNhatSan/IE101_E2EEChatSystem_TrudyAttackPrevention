"""Message retrieval routes."""
from flask import Blueprint, request, jsonify
from storage import get_messages_for_conversation, clear_conversation

messages_bp = Blueprint("messages", __name__, url_prefix="/api/messages")


@messages_bp.route("/history", methods=["GET"])
def get_message_history():
    """
    Get message history for a conversation.
    Query params:
    - me: current user (required)
    - type: conversation type (private, group, groupchat)
    - to: for private/group chats, the recipient or conversation ID
    - groupId: for group chats, the group ID
    """
    me = (request.args.get("me") or "").strip()
    conv_type = (request.args.get("type") or "").strip()
    to = (request.args.get("to") or "").strip()
    group_id = (request.args.get("groupId") or "").strip()

    if not me or not conv_type:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400

    # Build conversation ID
    if conv_type == "private" and to:
        conv_id, messages = get_messages_for_conversation("private", to, me)
    elif conv_type == "group":
        conv_id, messages = get_messages_for_conversation("group", None)
    elif conv_type == "groupchat" and group_id:
        conv_id, messages = get_messages_for_conversation("groupchat", group_id)
    else:
        return jsonify({"success": False, "message": "Conversation type không hợp lệ."}), 400

    return jsonify({"success": True, "messages": messages})


@messages_bp.route("/delete", methods=["POST"])
def delete_msg():
    """
    Clear entire conversation between two users (both sides).
    Body params:
    - me: current user
    - to: the other user
    """
    payload = request.get_json(force=True)
    me = (payload.get("me") or "").strip()
    to = (payload.get("to") or "").strip()

    if not me or not to:
        return jsonify({"success": False, "message": "Thiếu thông tin."}), 400

    # Build conversation ID (same as in get_messages_for_conversation)
    users = sorted([me, to])
    conv_id = f"private|{users[0]}|{users[1]}"

    # Clear the entire conversation
    if clear_conversation(conv_id):
        return jsonify({"success": True, "message": "Đã xoá toàn bộ đoạn chat."})
    else:
        return jsonify({"success": False, "message": "Không thể xoá đoạn chat."}), 400
