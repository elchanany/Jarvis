import sys

print("🚀 STARTING DEBUG SCRIPT...", flush=True)

try:
    from duckduckgo_search import DDGS
    print("✅ Import successful", flush=True)
except Exception as e:
    print(f"❌ Import Failed: {e}", flush=True)
    sys.exit(1)

import json

def test_search(backend_name):
    print(f"\n--- Testing Backend: {backend_name} ---", flush=True)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                "latest python version",
                region='wt-wt',
                timelimit='d',
                max_results=3,
                backend=backend_name
            ))
            
        print(f"✅ Success! Found {len(results)} results.")
        for i, r in enumerate(results):
            print(f"[{i+1}] {r.get('title')} ({r.get('href')})")
            print(f"    {r.get('body')[:100]}...")
            
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    print("🔍 DIAGNOSTIC: Testing Search Backends")
    
    # Test 1: Lite (Current)
    test_search('lite')
    
    # Test 2: HTML (Old default)
    test_search('html')
    
    # Test 3: API (Alternative)
    test_search('api')
