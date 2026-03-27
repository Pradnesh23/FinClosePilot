import sys
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)

# Add the project root to sys.path to import backend modules
sys.path.append(os.getcwd())

from backend.config import LETTA_SERVER_URL, LETTA_AGENT_ID
from backend.memory.letta_client import init_letta_client

print(f"--- Letta Cloud Connection Check ---")
print(f"Configured URL: {LETTA_SERVER_URL}")

try:
    wrapper = init_letta_client()
    if wrapper._use_fallback:
        print("[-] FAILED: The client is using the SQLite fallback. Letta server is likely unreachable.")
    else:
        print("[+] SUCCESS: Connected to Letta server!")
        
        # Test agent listing
        try:
            agents = wrapper.client.agents.list()
            print(f"Number of agents found: {len(agents.items)}")
            for a in agents.items:
                print(f" - Agent: {a.name} (id: {a.id})")
        except Exception as e:
            print(f"[-] Error listing agents: {e}")
            
except Exception as e:
    print(f"[-] CRITICAL ERROR: {e}")
