"""Test Telegram token validity."""
import asyncio
import aiohttp
import os

bot_token = os.getenv("EVRECONSE_TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here")
chat_id = os.getenv("EVRECONSE_TELEGRAM_CHAT_ID", "your_telegram_chat_id_here")

async def test_token():
    api_url = f"https://api.telegram.org/bot{bot_token}"
    
    async with aiohttp.ClientSession() as session:
        # Test getMe
        print("Testing getMe...")
        async with session.get(f"{api_url}/getMe") as resp:
            data = await resp.json()
            print(f"Status: {resp.status}")
            print(f"Response: {data}")
        
        # Test sendMessage
        print("\nTesting sendMessage...")
        payload = {
            "chat_id": chat_id,
            "text": "Test message from EVRECONSE"
        }
        async with session.post(f"{api_url}/sendMessage", json=payload) as resp:
            data = await resp.json()
            print(f"Status: {resp.status}")
            print(f"Response: {data}")

if __name__ == "__main__":
    asyncio.run(test_token())
