"""Routes package."""
from .auth import auth_bp
from .friends import friends_bp, set_connected_users as set_friends_connected_users
from .groups import groups_bp
from .messages import messages_bp
from .debug import debug_bp

__all__ = ["auth_bp", "friends_bp", "groups_bp", "messages_bp", "debug_bp", "set_friends_connected_users"]
