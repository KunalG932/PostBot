"""
Test script to verify all imports work correctly
"""

def test_imports():
    try:
        print("Testing imports...")
        
        # Test basic imports
        from constants import router, dp, TOKEN
        print("✅ Constants imported successfully")
        
        from db import db, mongo_client
        print("✅ Database imports successful")
        
        # Test utils imports
        from utils.data_store import get_user_data, set_user_data, init_user_data
        from utils.keyboards import get_main_menu_keyboard, get_post_creation_keyboard
        from utils.url_preview import get_url_preview
        print("✅ Utils imports successful")
        
        # Test handlers imports
        from handlers import start, post_creation, buttons, media, text_input
        from handlers import preview_publish, chat, clone_quote, stats, post_settings
        print("✅ All handlers imported successfully")
        
        print("\n🎉 All imports successful! The modular structure is working correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_imports()
