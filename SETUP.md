# EVRECONSE Setup Instructions

## Prerequisites

- Python 3.12 or higher
- Bybit API Key and Secret (can use testnet)
- Telegram Bot Token and Chat ID

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd C:\Users\user\Documents\Default Project\EVRECONSE
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Copy environment template:**
   ```bash
   copy .env.example .env
   ```

2. **Edit .env file with your credentials:**
   ```env
   EVRECONSE_EXCHANGE_API_KEY=your_bybit_api_key_here
   EVRECONSE_EXCHANGE_API_SECRET=your_bybit_api_secret_here
   EVRECONSE_TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   EVRECONSE_TELEGRAM_CHAT_ID=your_telegram_chat_id_here
   ```

3. **Optional: Modify config.yaml for custom settings**
   - Adjust risk parameters (TP/SL)
   - Change scoring thresholds
   - Modify notification settings
   - Configure symbols and timeframes

## Running the Application

### Basic Run
```bash
python -m src.main
```

### With Custom Config
```bash
python -m src.main --config config.yaml
```

### With Debug Logging
```bash
python -m src.main --log-level DEBUG
```

### On Testnet
```bash
python -m src.main --testnet
```

### Dry Run (Initialize Only)
```bash
python -m src.main --dry-run
```

## Testing

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Project Structure

```
EVRECONSE/
├── src/                    # Source code
│   ├── application/        # Application lifecycle
│   ├── config/             # Configuration management
│   ├── core/               # Core utilities
│   ├── data_provider/      # Bybit WebSocket/REST
│   ├── event_engine/       # Event processing
│   ├── models/             # Data models
│   ├── notification/       # Telegram notifications
│   ├── outcome/            # TP/SL monitoring
│   ├── scoring/            # Signal scoring
│   ├── storage/            # Data persistence
│   └── strategy/           # Trading strategies
├── tests/                  # Test suite
├── docs/                   # Documentation
├── strategies/             # Strategy specifications
├── config.yaml             # Main configuration
├── requirements.txt         # Python dependencies
└── .env                    # Environment variables (create from .env.example)
```

## Getting API Keys

### Bybit API
1. Go to https://www.bybit.com/app/user/api-management
2. Create API key
3. Set permissions: Read + Trade (or Read only for testnet)
4. Copy API Key and Secret to .env

### Telegram Bot
1. Message @BotFather on Telegram
2. Create new bot with `/newbot`
3. Copy bot token
4. Message your bot and get chat ID from @userinfobot
5. Copy bot token and chat ID to .env

## Troubleshooting

### Import Errors
Ensure you're running from the project root directory:
```bash
cd "C:\Users\user\Documents\Default Project\EVRECONSE"
python -m src.main
```

### Connection Errors
- Check API keys are correct
- Verify testnet/mainnet setting matches your keys
- Check internet connection
- Verify Bybit service status

### Notification Errors
- Verify Telegram bot token is valid
- Ensure you've started a conversation with your bot
- Check chat ID is correct

## Support

For issues or questions, refer to:
- `docs/CORE_SPECIFICATION.md` - System specification
- `docs/SCORING.md` - Scoring system details
- `strategies/LW-001.md` - Strategy documentation
