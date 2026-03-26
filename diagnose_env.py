import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure root is in path
sys.path.append(os.getcwd())

async def check_letta():
    print("\n--- [MEMORY] Letta Memory Check ---")
    from backend.config import LETTA_SERVER_URL
    from backend.memory.letta_client import init_letta_client
    print(f"URL: {LETTA_SERVER_URL}")
    if "api.letta.com" in LETTA_SERVER_URL:
        print("[TIP] You are using the HOSTED Letta API. If you set up a private cloud server, update LETTA_SERVER_URL in .env to your server's IP.")
    
    try:
        wrapper = init_letta_client()
        if wrapper._use_fallback:
            print("[ERROR] Letta: Unreachable (Using SQLite fallback)")
            return False
        else:
            try:
                agents = wrapper.client.list_agents()
                print(f"[OK] Letta: Connected! ({len(agents)} agents found)")
                return True
            except Exception as e:
                print(f"[ERROR] Letta list_agents failed: {e}")
                if "AgentState" in str(e):
                    print("[TIP] This 'AgentState' error often means a version mismatch between your Letta SDK and the server. Try updating 'letta' in requirements.txt and running 'pip install -r requirements.txt'.")
                return False
    except Exception as e:
        print(f"[ERROR] Letta Error: {e}")
        return False

async def check_llm():
    print("\n--- [LLM] Multi-Provider Check ---")
    from backend.config import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
    from backend.agents.model_router import route_call, PRIMARY_PROVIDER
    
    keys = {
        "Gemini": GEMINI_API_KEY,
        "Groq": GROQ_API_KEY,
        "OpenRouter": OPENROUTER_API_KEY
    }
    
    for name, key in keys.items():
        if key:
            print(f"[OK] {name} Key: Found (starts with '{key[:6]}...')")
        else:
            print(f"[SKIP] {name} Key: Not configured")

    if not PRIMARY_PROVIDER:
        print("[ERROR] CRITICAL: No primary LLM provider found. Agents will not work.")
        return False
    
    print(f"Primary Provider: {PRIMARY_PROVIDER.upper()}")
    
    print("Testing minimal inference...")
    try:
        result = await route_call(
            task_type="connection_test",
            system_prompt="You are a system health checker.",
            user_message="Respond with exactly one word: 'Operational'",
            run_id="diagnostic"
        )
        response = result.get("response", "").strip()
        latency = result.get("latency_ms", 0)
        print(f"[OK] AI Response: '{response}' (Latency: {latency}ms)")
        return True
    except Exception as e:
        print(f"[ERROR] Inference Failed: {e}")
        if "404" in str(e) and "openrouter" in str(e).lower():
            print("[TIP] OpenRouter model name might be outdated. I've updated model_router.py to fix this.")
        return False

async def check_telegram():
    print("\n--- [TELEGRAM] Notification Check ---")
    from backend.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CFO_CHAT_ID
    if not TELEGRAM_BOT_TOKEN:
        print("[SKIP] Telegram: Not configured")
        return True
    
    import httpx
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                bot_name = data.get("result", {}).get("first_name", "Unknown")
                print(f"[OK] Telegram: Connected as @{bot_name}")
                if TELEGRAM_CFO_CHAT_ID:
                    print(f"[OK] CFO Chat ID: {TELEGRAM_CFO_CHAT_ID}")
                else:
                    print("[WARN] Note: TELEGRAM_CFO_CHAT_ID is missing.")
                return True
            else:
                print(f"[ERROR] Telegram API Error: {resp.status_code}")
                return False
    except Exception as e:
        print(f"[ERROR] Telegram Connection Failed: {e}")
        return False

async def main():
    print("==========================================")
    print("   FinClosePilot System Diagnostic        ")
    print("==========================================")
    
    # Check .env location
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        print(f"[OK] .env found in project root: {env_path}")

        load_dotenv(env_path)
    else:
        print(f"[WARN] .env NOT FOUND in project root.")
        print(f"Current Directory: {os.getcwd()}")
    
    await check_letta()
    await check_llm()
    await check_telegram()
    
    print("\n==========================================")
    print("Diagnostic Complete.")

if __name__ == "__main__":
    asyncio.run(main())
