# Storage module
from .db import load_json, save_json, data_lock, ensure_data_files, USERS_FILE, GROUPS_FILE, MESSAGES_FILE
from .users import get_user, set_user, are_friends, remove_friend
from .groups import get_group, set_group, delete_group
from .messages import get_messages, add_message, get_messages_for_conversation, delete_message, clear_conversation

__all__ = [
    "load_json", "save_json", "data_lock", "ensure_data_files",
    "USERS_FILE", "GROUPS_FILE", "MESSAGES_FILE",
    "get_user", "set_user", "are_friends", "remove_friend",
    "get_group", "set_group", "delete_group",
    "get_messages", "add_message", "get_messages_for_conversation", "delete_message", "clear_conversation",
]
