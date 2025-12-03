"""
Data storage utilities for user post data management
"""

# Enhanced user input dictionary to store complex post data
user_post_data = {}

def get_user_data(user_id):
    """Get user post data by user ID"""
    data = user_post_data.get(user_id, {})
    print(f"DEBUG DATA_STORE: Getting data for user {user_id}: {bool(data)} (keys: {list(data.keys()) if data else 'None'})")
    return data

def set_user_data(user_id, data):
    """Set user post data"""
    user_post_data[user_id] = data
    print(f"DEBUG DATA_STORE: Setting data for user {user_id}: {list(data.keys()) if data else 'None'}")

def clear_user_data(user_id):
    """Clear user post data"""
    if user_id in user_post_data:
        del user_post_data[user_id]

def init_user_data(user_id):
    """Initialize user post data with default values"""
    user_post_data[user_id] = {
        "text": "",
        "media": [],
        "buttons": [],
        "pin_post": False,
        "notifications": True,
        "link_preview": True,
        "state": "main_post_menu"
    }
