# PostBot - Telegram Channel Management Bot

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=postbot&type=git&repository=KunalG932%2FPostBot&branch=main&instance_type=free&regions=was&instances_min=0&autoscaling_sleep_idle_delay=300)

A powerful Telegram bot for creating and publishing posts to multiple channels.

## Features

- Multi-channel post publishing
- Rich text with Markdown/HTML support
- Media support (photos, videos, documents)
- Interactive buttons with URLs
- Post editing and management
- Preview before publishing

## Quick Setup

### Prerequisites
- Python 3.8+
- MongoDB (cloud or local)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Local Installation

```bash
git clone https://github.com/KunalG932/PostBot.git
cd PostBot
pip install -r requirements.txt
python main.py
```

Create `.env` file:
```
BOT_TOKEN=your_bot_token
MONGO_URI=your_mongodb_uri
```

## Koyeb Deployment (Recommended)

1. Fork this repo to your GitHub
2. Sign up at [Koyeb.com](https://www.koyeb.com/)
3. Connect your GitHub repository
4. Set environment variables:
   - `BOT_TOKEN` - from @BotFather
   - `MONGO_URI` - MongoDB connection string
   - `ADMIN_IDS` - your Telegram user ID (optional)
5. Deploy!

**Free MongoDB:** Use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) M0 cluster.

## Usage

1. Start bot: `/start`
2. Connect channel: `/connect @yourchannel`
3. Create posts with text, media, and buttons
4. Preview and publish

## Configuration

All settings in `.env` file (see `.env.example`).

**Required:**
- `BOT_TOKEN` - Telegram bot token
- `MONGO_URI` - MongoDB connection

**Optional:** Limits, logging, features, etc. (see `config.py`)

## Support

- Developer: [@DevIncognito](https://t.me/DevIncognito)
- Channel: [@incognitobots](https://t.me/incognitobots)
- Issues: [GitHub](https://github.com/KunalG932/PostBot/issues)

## License

MIT License - see [LICENSE](LICENSE)

---

Made by [@KunalG932](https://github.com/KunalG932)
