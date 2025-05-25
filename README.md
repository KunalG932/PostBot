# 🤖 PostBot - Advanced Telegram Channel Management Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4.svg)](https://telegram.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248.svg)](https://www.mongodb.com/)
[![GitHub](https://img.shields.io/badge/GitHub-KunalG932/PostBot-blue.svg)](https://github.com/KunalG932/PostBot)

> A powerful, feature-rich Telegram bot for effortless channel content management, creation, and publishing.

## ✨ Features

### 📝 **Advanced Post Creation**
- **Rich Text Support** - Add formatted text with Markdown/HTML support
- **Multi-Media Posts** - Support for photos, videos, documents, and animations
- **Media Groups** - Create posts with multiple media files (up to 10 files)
- **Smart Media Handling** - Automatic file type detection and validation

### 🔗 **Interactive Buttons**
- **Single Button Creation** - Add individual buttons with custom text and URLs
- **Bulk Button Format** - Quick format: `Button1 - URL1 | Button2 - URL2`
- **URL Validation** - Automatic URL format validation and correction
- **Button Management** - Add, edit, and remove buttons dynamically

### 📤 **Multi-Channel Publishing**
- **Channel Selection** - Choose specific channels or publish to all
- **Bulk Publishing** - Publish to multiple channels simultaneously
- **Multi-Select Interface** - Advanced channel selection with toggle options
- **Publishing Status** - Real-time feedback on publishing success/failure

### ✏️ **Post Editing & Management**
- **Live Post Editing** - Edit existing channel posts with ease
- **Content Modification** - Update text, media, and buttons of published posts
- **Quick Actions** - Special options for posts without buttons
- **Smart Editing Flow** - Intuitive interface for content modifications

### ⚙️ **Advanced Settings & Options**
- **Pin Posts** - Automatically pin important posts
- **Notification Control** - Toggle notifications for silent posting
- **Link Preview** - Control link preview display
- **Smart Defaults** - Intelligent default settings

### 🎯 **Additional Features**
- **Post Preview** - See exactly how your post will look before publishing
- **Content Validation** - Ensures posts have content before publishing
- **Error Handling** - Comprehensive error messages and recovery
- **User-Friendly Interface** - Intuitive menu system with clear navigation
- **Real-time Status** - Live updates on post creation progress

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- MongoDB database (local or cloud)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/KunalG932/PostBot.git
   cd PostBot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file or set environment variables
   export BOT_TOKEN="your_bot_token_here"
   export MONGO_URI="your_mongodb_connection_string"
   export CHANNEL_ID="your_channel_id"  # Optional
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## 📋 Setup Guide

### 1. Create Your Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command and follow instructions
3. Save your bot token securely

### 2. Prepare Your Channel
1. Create a Telegram channel or use existing one
2. Add your bot as an administrator
3. Grant necessary permissions:
   - ✅ Post messages
   - ✅ Edit messages
   - ✅ Delete messages
   - ✅ Pin messages

### 3. Connect Your Channel
1. Start your bot with `/start`
2. Use `/connect @yourchannel` to connect
3. Verify bot admin status in channel

## 🎮 How to Use

### Creating Posts

1. **Start Creating** 📝
   ```
   /start → 🌟 Create Post 🌟
   ```

2. **Add Content**
   - `📝 Add Text` - Include your message text
   - `📷 Add Media` - Upload photos, videos, or documents
   - `🔗 Add Buttons` - Add interactive buttons

3. **Configure Settings**
   - `📌 Pin Post` - Pin the post in channel
   - `🔔 Toggle Notifications` - Control notification settings
   - `🔗 Link Preview` - Enable/disable link previews

4. **Preview & Publish**
   - `👁️ Preview Post` - See how it will look
   - `📤 Publish Post` - Send to your channels

### Editing Existing Posts

1. **Start Editing** ✏️
   ```
   /edit or ✏️ Edit Post button
   ```

2. **Provide Message Link**
   - Copy link from channel post
   - Send link to bot
   - Bot will load current content

3. **Make Changes**
   - Edit text, media, or buttons
   - Use quick actions for posts without buttons
   - Save changes when done

### Button Formats

**Single Button:**
```
Button Text - https://example.com
```

**Multiple Buttons:**
```
Visit Website - https://site.com | Join Channel - https://t.me/channel
```

## 🛠️ Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Your Telegram bot token | ✅ Yes | - |
| `MONGO_URI` | MongoDB connection string | ✅ Yes | `mongodb://localhost:27017/postbot` |
| `CHANNEL_ID` | Default channel ID | ❌ No | `0` |

## 📁 Project Structure

```
postbot/
├── 📄 main.py                    # Bot entry point
├── 📄 constants.py               # Configuration constants
├── 📄 db.py                      # Database connection
├── 📄 requirements.txt           # Python dependencies
├── 📁 handlers/                  # Bot command handlers
│   ├── start.py                  # Start command and main menu
│   ├── post_creation.py          # Post creation flow
│   ├── edit_post.py              # Post editing functionality
│   ├── buttons.py                # Button management
│   ├── media.py                  # Media handling
│   ├── channel_selection.py      # Multi-channel publishing
│   ├── preview_publish.py        # Preview and publishing
│   └── ...                       # Other handlers
└── 📁 utils/                     # Utility modules
    ├── data_store.py             # User data management
    ├── keyboards.py              # Keyboard layouts
    └── url_preview.py            # URL handling utilities
```

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Development Guidelines
- Follow PEP 8 style guidelines
- Add docstrings to functions and classes
- Include error handling for external APIs
- Test your changes thoroughly

## 📞 Support & Contact

### Developer
- **GitHub:** [@KunalG932](https://github.com/KunalG932)
- **Telegram:** [@DevIncognito](https://t.me/DevIncognito)

### Channel
- **Updates & Support:** [@incognitobots](https://t.me/incognitobots)

### Issues & Bug Reports
- Open an issue on [GitHub Issues](https://github.com/KunalG932/PostBot/issues)
- Include detailed reproduction steps
- Provide error logs if applicable

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Modern Telegram Bot API framework
- [MongoDB](https://www.mongodb.com/) - Database for user data and channel management
- [Telegram Bot API](https://core.telegram.org/bots/api) - For making this bot possible

## 🔄 Changelog

### v1.0.0
- ✅ Initial release
- ✅ Multi-channel publishing
- ✅ Post editing functionality
- ✅ Advanced button management
- ✅ Media group support
- ✅ Quick actions for post enhancement

---

**Made with ❤️ by [@KunalG932](https://github.com/KunalG932)**

**Join our channel for updates: [@incognitobots](https://t.me/incognitobots)**
