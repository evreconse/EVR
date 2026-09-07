Í"""Test Telegram token validity."""
import asyncio
import aiohttp

bot_token = "8730872028:AAEYFDMfc-Fv9Pe0x7beZL14GP4Jb7cd2_M"
chat_id = "8307060083"

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
Q *cascade08QR*cascade08RT *cascade08TU*cascade08UV *cascade08VW*cascade08WX *cascade08XZ*cascade08Z] *cascade08]_*cascade08_` *cascade08`a*cascade08ab *cascade08bf*cascade08fg *cascade08gi*cascade08ij *cascade08jm*cascade08mn *cascade08nt*cascade08tu *cascade08uy*cascade08yz *cascade08z~*cascade08~Í *cascade082Rfile:///C:/Users/user/Documents/Default%20Project/EVRECONSE/test_telegram_token.py