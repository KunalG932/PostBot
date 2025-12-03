"""
Keyboard utility functions for creating common keyboards
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    """Get the main menu keyboard with developer info"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Create Post")],
            [KeyboardButton(text="Edit Post"), KeyboardButton(text="Chat")],
            [KeyboardButton(text="Developer Info")],
        ],
        resize_keyboard=True,
    )

def get_post_creation_keyboard():
    """Get the post creation menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Add Text"), KeyboardButton(text="Add Media")],
            [KeyboardButton(text="Add Buttons"), KeyboardButton(text="Pin Post")],
            [KeyboardButton(text="Toggle Notifications"), KeyboardButton(text="Link Preview")],
            [KeyboardButton(text="Preview Post"), KeyboardButton(text="Publish Post")],
            [KeyboardButton(text="Clear All"), KeyboardButton(text="Back")]
        ],
        resize_keyboard=True,
    )

def get_chat_menu_keyboard():
    """Get the chat menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Connect"), KeyboardButton(text="Connected")],
            [KeyboardButton(text="Back")],
        ],
        resize_keyboard=True,
    )

def get_back_to_post_menu_keyboard():
    """Get keyboard with only back to post menu button"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Back to Post Menu")]],
        resize_keyboard=True,
    )

def get_media_management_keyboard():
    """Get keyboard for media management"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Clear Media"), KeyboardButton(text="Done Adding Media")],
            [KeyboardButton(text="Back to Post Menu")]
        ],
        resize_keyboard=True,
    )

def get_button_management_keyboard():
    """Get keyboard for button management"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Add New Button"), KeyboardButton(text="Clear Buttons")],
            [KeyboardButton(text="Send Message Format"), KeyboardButton(text="Back to Post Menu")]
        ],
        resize_keyboard=True,
    )

def get_clear_confirmation_keyboard():
    """Get keyboard for clear confirmation"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Yes, Clear All"), KeyboardButton(text="No, Keep Content")],
            [KeyboardButton(text="Back to Post Menu")]
        ],
        resize_keyboard=True,
    )

def create_inline_buttons_keyboard(buttons_list):
    """Create inline keyboard from buttons list"""
    if not buttons_list:
        return None
    
    buttons = []
    for button in buttons_list:
        buttons.append([InlineKeyboardButton(text=button["text"], url=button["url"])])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
