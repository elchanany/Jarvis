import requests
import json
from gemma_brain import generate_system_prompt

payload = {
    "model": "gemma4:e4b",
    "messages": [
        {"role": "system", "content": generate_system_prompt()},
        {"role": "user", "content": "היי"}
    ],
    "stream": True,
    "options": {"temperature": 0.2}
}

try:
    resp = requests.post("http://127.0.0.1:11434/api/chat", json=payload, stream=True)
    print(f"Status: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")
