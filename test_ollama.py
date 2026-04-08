import requests
import json

def test():
    req = {
        "model": "gemma4:e4b",
        "messages": [{"role": "user", "content": "היי"}],
        "stream": True
    }
    resp = requests.post("http://127.0.0.1:11434/api/chat", json=req, stream=True)
    with open("test_raw_chunks.txt", "w", encoding="utf-8") as f:
        for line in resp.iter_lines():
            if line:
                f.write(line.decode('utf-8') + "\n")
    print("Done")

if __name__ == "__main__":
    test()
