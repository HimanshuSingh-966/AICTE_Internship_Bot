# 🚀 InternBeacon

An automated internship monitoring bot that scrapes **AICTE** and **Internshala** for relevant internships in your preferred domains and sends real-time notifications via Telegram.

## 🎯 Features

- 🏛️ **AICTE Integration**: Monitors official AICTE internship portal
- 💼 **Internshala Integration**: Searches Internshala for matching opportunities
- 🤖 **Smart Filtering**: Filters by preferred domains (Data Science, AI/ML, etc.)
- 📱 **Telegram Notifications**: Instant alerts with apply buttons
- 🔄 **Duplicate Prevention**: Tracks seen internships across platforms
- ⏰ **Automated Scheduling**: Runs checks every hour (configurable)
- 📊 **Comprehensive Reports**: Summary statistics for both platforms
- 🌐 **Cloud Ready**: Optimized for Render deployment

## 📋 Prerequisites

- Python 3.9+
- Telegram Bot Token
- Telegram Chat ID

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/HimanshuSingh-966/InternBeacon.git
cd InternBeacon
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file:
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Optional (defaults provided)
ENABLE_AICTE=true
ENABLE_INTERNSHALA=true
CHECK_INTERVAL_HOURS=2
```

### 4. Run the Bot
```bash
python main.py
```

## 🔑 Getting Telegram Credentials

### Bot Token
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Follow the prompts to create your bot
4. Copy the bot token (format: `1234567890:ABCdef...`)

### Chat ID
1. Start a chat with your new bot
2. Send any message to the bot
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find `"chat":{"id":12345678}` in the response
5. Use that number as your `TELEGRAM_CHAT_ID`

## 🎛️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | ✅ | - | Your Telegram chat ID |
| `ENABLE_AICTE` | ❌ | `true` | Enable AICTE scraping |
| `ENABLE_INTERNSHALA` | ❌ | `true` | Enable Internshala scraping |
| `CHECK_INTERVAL_HOURS` | ❌ | `1` | Hours between checks |
| `RENDER` | ❌ | `false` | Enable Render deployment mode |
| `PORT` | ❌ | `10000` | Port for health checks |

### Preferred Domains
Edit the `preferred_domains` list in `bot.py` to customize your interests:
```python
self.preferred_domains = [
    'data science', 'machine learning', 'artificial intelligence', 
    'ai', 'ml', 'data analyst', 'ai/ml'
]
```

## 🌐 Deploy to Render

### Option 1: One-Click Deploy
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Option 2: Manual Deployment

1. **Fork this repository**

2. **Connect to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

3. **Configure Environment Variables** in Render:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   RENDER=true
   ENABLE_AICTE=true
   ENABLE_INTERNSHALA=true
   CHECK_INTERVAL_HOURS=2
   ```

4. **Deploy**: Render will automatically use the `render.yaml` configuration

## 📊 Sample Output

### Individual Notifications
```
🏛️ New AICTE Internship!

📋 Role: Data Science Intern
🏢 Company: Tech Corp India
💰 Stipend: ₹15,000/month
📍 Location: Remote
⏰ Duration: 6 months
📅 Start Date: 2025-09-01
⚡ Apply By: 2025-08-25
🕐 Posted: Just now

🔍 Found: 2025-08-17 14:30:25 IST

#AICTEInternship #TechCorpIndia
```

### Summary Reports
```
📊 Dual-Platform Internship Bot Summary

🏛️ AICTE:
   • Found: 25
   • Matching: 12
   • New: 3

💼 Internshala:
   • Found: 40
   • Matching: 18
   • New: 5

🔍 Total across platforms:
   • Found: 65
   • Matching your domains: 30
   • New notifications sent: 8

⏰ Last checked: 2025-08-17 14:30:25 IST

🎉 New opportunities above!
```

## 🔧 Technical Details

### Architecture
- **Modular Design**: Separate scrapers for each platform
- **Abstract Base Class**: Easy to add new platforms
- **Error Handling**: Platform-specific error isolation
- **Rate Limiting**: Respectful scraping with delays
- **Persistent Storage**: JSON-based seen internships tracking

### Data Flow
1. **Scheduled Check** → Runs every N hours
2. **Platform Scraping** → Fetches from AICTE and Internshala
3. **Domain Filtering** → Matches against preferred keywords
4. **Duplicate Detection** → Checks against seen internships
5. **Telegram Notification** → Sends alerts for new matches
6. **Summary Report** → Provides statistics

### File Structure
```
internship-bot/
├── bot.py                 # Main application
├── requirements.txt       # Python dependencies
├── render.yaml           # Render deployment config
├── README.md             # This file
├── .env                  # Environment variables (create this)
├── seen_internships.json # Auto-generated tracking file
└── bot.log               # Auto-generated log file
```

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run with debug logging
python bot.py

# Check logs
tail -f bot.log
```

### Adding New Platforms
1. Create a new scraper class extending `InternshipScraper`
2. Implement `fetch_internships()` method
3. Add the scraper to `DualPlatformInternshipBot.__init__()`
4. Update configuration and documentation

## 📝 Logs

The bot creates detailed logs in `bot.log`:
- ✅ Successful operations
- ❌ Error details and stack traces  
- 📊 Statistics and performance metrics
- 🔍 Debug information for troubleshooting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for educational and personal use only. Please respect the terms of service of AICTE and Internshala platforms. Use responsibly and ensure compliance with their scraping policies.

## 🆘 Support

- **Issues**: Open a GitHub issue
- **Questions**: Check existing issues or create a new one
- **Logs**: Include `bot.log` contents when reporting issues

## 🚀 Roadmap

- [ ] Add more platforms (Indeed, Naukri.com)
- [ ] Web dashboard for monitoring
- [ ] Advanced filtering options
- [ ] Email notifications
- [ ] Mobile app integration
- [ ] Analytics dashboard

---

**Built with ❤️ for students seeking internship opportunities**
