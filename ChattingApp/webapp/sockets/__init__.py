"""Socket event handlers."""
from flask import request
from flask_socketio import emit
from storage import load_json, GROUPS_FILE, add_message, are_friends, get_messages_for_conversation
from extensions import socketio

# Connected users: username -> sid
connected_users = {}


def register_socket_handlers():
    """Register all socket handlers."""
    
    @socketio.on("connect")
    def on_connect():
        username = request.args.get("username")
        print(f"[WS DEBUG] Connection attempt - request.args: {dict(request.args)}")
        print(f"[WS DEBUG] Extracted username: {username}")
        
        if not username:
            print(f"[WS ERROR] Connection rejected - no username provided")
            return False

        connected_users[username] = request.sid
        print(f"[WS] {username} connected ({request.sid})")
        print(f"[WS DEBUG] Connected users now: {list(connected_users.keys())}")

    @socketio.on("disconnect")
    def on_disconnect():
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
    def on_authenticate(data):
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
    def on_send_message(payload):
        """Handle incoming messages."""
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

            # Save message
            conv_id, _ = get_messages_for_conversation("private", to_user, sender)
            add_message(conv_id, {
                "from": sender,
                "to": to_user,
                "type": "private",
                "text": text,
            })

            # Send to recipient only (sender already added message to their UI)
            sid = connected_users.get(to_user)
            if sid:
                emit(
                    "message",
                    {"from": sender, "to": to_user, "type": "private", "text": text},
                    to=sid,
                )

        elif msg_type == "group":
            # Save message
            add_message("group|all", {
                "from": sender,
                "type": "group",
                "text": text,
            })
            
            # broadcast to all connected except sender (sender already added to UI)
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
            
            # Save message
            add_message(f"groupchat|{group_id}", {
                "from": sender,
                "type": "groupchat",
                "groupId": group_id,
                "groupName": group.get("name"),
                "text": text,
            })
            
            # Send to group members except sender (sender already added to UI)
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


    @socketio.on("delete_conversation")
    def on_delete_conversation(payload):
        """Handle conversation deletion - notify other user in real-time."""
        user = payload.get("user")
        other_user = payload.get("other_user")
        
        if not user or not other_user:
            return
        
        # Notify the other user to clear their chat
        other_sid = connected_users.get(other_user)
        if other_sid:
            emit(
                "conversation_deleted",
                {"user": user, "other_user": other_user},
                to=other_sid,
            )


def get_connected_users():
    """Get current connected users dict."""
    return connected_users
