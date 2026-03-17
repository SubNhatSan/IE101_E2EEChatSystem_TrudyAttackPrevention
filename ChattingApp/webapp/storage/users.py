"""User storage operations."""
from .db import load_json, save_json, data_lock, USERS_FILE


def get_user(username):
    """Get user by username, with default fields."""
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
    """Set user data."""
    users = load_json(USERS_FILE)
    users[username] = data
    save_json(USERS_FILE, users)


def are_friends(user_a, user_b):
    """Check if user_a and user_b are friends."""
    if not user_a or not user_b:
        return False
    user = get_user(user_a)
    return user and user_b in user.get("friends", [])


def remove_friend(user_a, user_b):
    """Remove friendship between two users (bilateral)."""
    if not user_a or not user_b:
        return False
    
    users = load_json(USERS_FILE)
    
    if user_a in users and user_b in users:
        # Remove user_b from user_a's friends
        if user_b in users[user_a].get("friends", []):
            users[user_a]["friends"].remove(user_b)
        
        # Remove user_a from user_b's friends
        if user_a in users[user_b].get("friends", []):
            users[user_b]["friends"].remove(user_a)
        
        save_json(USERS_FILE, users)
        return True
    
    return False
