½ """
Test script to verify real Telegram message delivery.
"""
import asyncio
import aiohttp
from datetime import UTC, datetime

# Telegram credentials from config
BOT_TOKEN = "8693203470:AAF3eRn8WHUXHiJSP0V6di02cMvgebHzmPc"
CHAT_ID = "8307060083"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.

    Characters to escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def test_telegram_delivery():
    """Test actual Telegram message delivery."""
    print(f"Testing Telegram delivery...")
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    print(f"Chat ID: {CHAT_ID}")
    print(f"API URL: {API_URL}")
    print()
    
    # First, test getMe to verify bot is valid
    print("Step 1: Testing bot authentication (getMe)...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/getMe") as resp:
            data = await resp.json()
            print(f"Status: {resp.status}")
            print(f"Response: {data}")
            
            if not data.get("ok"):
                print(f"[X] Bot authentication failed: {data}")
                return False
            
            bot_info = data.get("result", {})
            print(f"[OK] Bot authenticated: {bot_info.get('username')}")
            print()
    
    # Test sending a message with MarkdownV2
    print("Step 2: Sending test message with MarkdownV2...")
    subject = "EVRECONSE Telegram Delivery Test"
    body = f"""Timestamp: {datetime.now(UTC).isoformat()}
Test: Real message delivery verification
This is a test message to verify the Telegram Bot API is working correctly."""
    
    # Format with MarkdownV2 escaping
    formatted_subject = f"*{escape_markdown_v2(subject)}*"
    formatted_body = escape_markdown_v2(body)
    message_text = f"{formatted_subject}\n\n{formatted_body}"
    
    print(f"Formatted message (first 200 chars): {message_text[:200]}...")
    
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/sendMessage", json=payload) as resp:
            data = await resp.json()
            print(f"Status: {resp.status}")
            print(f"Response: {data}")
            
            if not data.get("ok"):
                print(f"[X] Message send failed: {data}")
                error = data.get("description", "Unknown error")
                print(f"Error description: {error}")
                return False
            
            result = data.get("result", {})
            message_id = result.get("message_id")
            print(f"[OK] Message sent successfully!")
            print(f"Message ID: {message_id}")
            print(f"Chat ID: {result.get('chat', {}).get('id')}")
            print(f"Date: {result.get('date')}")
            print()
            
            # Verify message was delivered by getting chat info
            print("Step 3: Verifying chat access...")
            async with session.get(f"{API_URL}/getChat", params={"chat_id": CHAT_ID}) as resp:
                data = await resp.json()
                print(f"Status: {resp.status}")
                print(f"Response: {data}")
                
                if data.get("ok"):
                    chat_info = data.get("result", {})
                    print(f"[OK] Chat accessible: {chat_info.get('type')} - {chat_info.get('title', chat_info.get('first_name', 'Unknown'))}")
                else:
                    print(f"[!] Could not verify chat access: {data}")
            
            return True

if __name__ == "__main__":
    result = asyncio.run(test_telegram_delivery())
    print()
    print("=" * 60)
    if result:
        print("[OK] TELEGRAM DELIVERY VERIFICATION PASSED")
    else:
        print("[X] TELEGRAM DELIVERY VERIFICATION FAILED")
    print("=" * 60)
­ *cascade08­Á*cascade08Á€  *cascade08€ ½  *cascade082Lfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/test_telegram.py