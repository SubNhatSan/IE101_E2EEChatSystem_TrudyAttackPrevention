"""Database utilities - handle JSON file I/O and threading."""
import json
import os
import threading
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

USERS_FILE = os.path.join(DATA_DIR, "users.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")

# Thread safety
data_lock = threading.Lock()


def ensure_data_files():
    """Ensure all data files exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    for path in (USERS_FILE, GROUPS_FILE, MESSAGES_FILE):
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f)


def load_json(path):
    """Load JSON from file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    """Save JSON to file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_data_paths():
    """Get all data file paths."""
    return {
        "users": USERS_FILE,
        "groups": GROUPS_FILE,
        "messages": MESSAGES_FILE,
    }
