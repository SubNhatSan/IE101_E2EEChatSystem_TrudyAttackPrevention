"""Message storage operations."""
from datetime import datetime
from .db import load_json, save_json, MESSAGES_FILE


def get_messages(conversation_id):
    """
    Get all messages for a conversation.
    conversation_id format: 
      - "private|user1|user2" for private chats (sorted alphabetically)
      - "group|all" for public room
      - "groupchat|group_id" for group chats
    """
    messages = load_json(MESSAGES_FILE)
    return messages.get(conversation_id, [])


def add_message(conversation_id, message_data):
    """
    Add a message to a conversation.
    message_data should include: from, text, type, timestamp, and optionally to/groupId
    """
    messages = load_json(MESSAGES_FILE)
    if conversation_id not in messages:
        messages[conversation_id] = []
    
    # Add timestamp if not present
    if "timestamp" not in message_data:
        message_data["timestamp"] = datetime.utcnow().isoformat()
    
    messages[conversation_id].append(message_data)
    save_json(MESSAGES_FILE, messages)


def get_messages_for_conversation(conversation_type, to, from_user=None, group_name=None):
    """
    Get messages for a specific conversation type.
    Returns appropriately formatted conversation_id and messages.
    """
    if conversation_type == "private":
        # Sort usernames to create consistent conversation ID
        users = sorted([from_user, to]) if from_user else [to]
        conv_id = f"private|{users[0]}|{users[1]}"
    elif conversation_type == "group":
        conv_id = "group|all"
    elif conversation_type == "groupchat":
        conv_id = f"groupchat|{to}"
    else:
        return None, []
    
    messages = get_messages(conv_id)
    return conv_id, messages


def clear_conversation_messages(conversation_id):
    """Clear all messages for a conversation (mainly for testing)."""
    messages = load_json(MESSAGES_FILE)
    if conversation_id in messages:
        messages[conversation_id] = []
        save_json(MESSAGES_FILE, messages)


def delete_message(conversation_id, message_index):
    """Delete a specific message from a conversation (only for private chats)."""
    messages = load_json(MESSAGES_FILE)
    if conversation_id in messages and 0 <= message_index < len(messages[conversation_id]):
        messages[conversation_id].pop(message_index)
        save_json(MESSAGES_FILE, messages)
        return True
    return False


def clear_conversation(conversation_id):
    """Clear all messages from a conversation (completely delete the conversation)."""
    messages = load_json(MESSAGES_FILE)
    if conversation_id in messages:
        messages[conversation_id] = []
        save_json(MESSAGES_FILE, messages)
        return True
    return False
