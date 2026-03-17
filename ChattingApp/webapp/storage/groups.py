"""Group storage operations."""
from .db import load_json, save_json, data_lock, GROUPS_FILE


def get_group(group_id):
    """Get group by ID."""
    groups = load_json(GROUPS_FILE)
    return groups.get(group_id)


def set_group(group_id, data):
    """Set group data."""
    groups = load_json(GROUPS_FILE)
    groups[group_id] = data
    save_json(GROUPS_FILE, groups)


def delete_group(group_id):
    """Delete a group by ID."""
    groups = load_json(GROUPS_FILE)
    if group_id in groups:
        del groups[group_id]
        save_json(GROUPS_FILE, groups)
        return True
    return False
