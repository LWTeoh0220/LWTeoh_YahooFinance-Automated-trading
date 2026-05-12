# Yahoo Finance Stock Price Monitor

Real-time stock price monitoring system with LINE notifications. Automatically sends alerts when stock prices reach target levels.

## Features

- 📊 Real-time stock price monitoring via Yahoo Finance
- 🔔 LINE Messaging API notifications
- 💾 SQLite database for alert history and cooldown management
- ⏱️ Configurable check intervals (default: 15 minutes)
- 🎯 Multiple stock support with flexible price conditions
- 🤖 GitHub Actions integration for automated scheduling
- 📝 Comprehensive logging for debugging

## Quick Start

### 1. Create Virtual Environment

```bash
conda create -n YahooFinance_310 python=3.10
conda activate YahooFinance_310
pip install -r requirements.txt
```

### 2. Configuration Setup

#### Create `.env` file with your LINE credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```
LINE_CHANNEL_TOKEN=your_channel_token
LINE_CHANNEL_SECRET=your_channel_secret
LINE_USER_ID=your_line_user_id
CHECK_INTERVAL_MINUTES=15
```

#### Edit `config.json` to add stocks to monitor:
```json
{
  "stocks": [
    {
      "symbol": "2330.TW",
      "name": "台积电",
      "target_price": 2300,
      "condition": ">=",
      "enabled": true
    }
  ]
}
```

**Stock symbol examples:**
- `2330.TW` - Taiwan Semiconductor Manufacturing
- `0050.TW` - Taiwan Index
- `AAPL` - Apple
- `MSFT` - Microsoft

**Price conditions:**
- `>=` - Greater than or equal (alert when price reaches this level)
- `<=` - Less than or equal (alert when price drops to this level)
- `>` - Strictly greater than
- `<` - Strictly less than

### 3. Get LINE Credentials

1. Create LINE Official Account: https://business.line.biz/
2. Go to Messaging API settings
3. Copy Channel Token and Channel Secret
4. Add your User ID to `.env`

### 4. Run Locally

```bash
python src/main.py
```

Monitor will:
- ✓ Test LINE connection
- ✓ Run initial price check
- ✓ Schedule periodic checks every 15 minutes
- ✓ Send LINE notifications when conditions are met

### 5. Deploy to GitHub Actions

1. Push code to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:
   - `LINE_CHANNEL_TOKEN`
   - `LINE_CHANNEL_SECRET`
   - `LINE_USER_ID`
4. Workflow runs automatically every 15 minutes

## Project Structure

```
├── src/
│   ├── main.py              # Main entry point
│   ├── config.py            # Configuration management
│   ├── stock_monitor.py     # Price monitoring logic
│   ├── database.py          # SQLite operations
│   └── line_notifier.py     # LINE API integration
├── config.json              # Stock configuration
├── .env.example             # Environment variables template
├── requirements.txt         # Python dependencies
├── logs/                    # Application logs
└── .github/workflows/       # GitHub Actions automation
```

## Important Notes

### Cooldown Period
- Default: 30 minutes between notifications for the same stock/price
- Prevents spam if price hovers around target
- Configurable in `src/database.py`

### Check Interval
- Recommended: 15 minutes (safe for GitHub Actions)
- Don't set below 5 minutes to avoid API rate limits
- Customize in `.env` or `config.json`

### Database
- SQLite automatically creates `stock_monitor.db`
- Stores alert history and prevents duplicate notifications
- Safe to delete; will be recreated on next run

## Troubleshooting

### "LINE connection test failed"
- Verify `LINE_CHANNEL_TOKEN` and `LINE_USER_ID` are correct
- Check .env file is in project root

### "No price data available"
- Verify stock symbol is correct (must be Yahoo Finance format)
- Add `.TW` suffix for Taiwan stocks
- Market may be closed

### Logs
- Check `logs/stock_monitor.log` for detailed error messages
- Use `LOG_LEVEL=DEBUG` in `.env` for verbose output

## Example Alert Message

```
🚨 股票价格提醒

股票: 台积电 (2330.TW)
目标价格: 2300.00
现价: 2305.50
状态: 已达到或超过

触发时间: 2026-05-12 14:30:00
```

## License

This is a school assignment project.

## Author

LWTeoh
