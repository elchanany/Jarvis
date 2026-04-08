import sys
from duckduckgo_search import DDGS

def test_search(query, backend='api'):
    print(f"\n🔍 Testing DuckDuckGo ('{backend}') with query: '{query}'...")
    try:
        # NEW IMPORT STYLE per warning
        from ddgs import DDGS
        import time
        
        with DDGS() as ddgs:
            # Rule 2 & 3: max_results=1
            results = list(ddgs.text(
                query,
                region='wt-wt',
                timelimit='d',
                max_results=1,
                backend=backend
            ))
            
            if not results:
                 print("❌ No results found.")
                 return

            print(f"✅ Success! Found {len(results)} results:")
            for i, r in enumerate(results):
                print(f"\n--- Result {i+1} ---")
                print(f"Title: {r.get('title')}")
                print(f"Link:  {r.get('href')}")
                print(f"Body:  {r.get('body')}")
        
        # Rule 4: Sleep for safety in loops
        time.sleep(2) 

    except Exception as e:
        print(f"❌ Error: {e}")

def test_google(query):
    print(f"\n🔍 Testing Google Search with query: '{query}'...")
    try:
        from googlesearch import search
        # advanced=True returns objects with title/desc/url
        results = list(search(query, num_results=3, advanced=True))
        
        if not results:
             print("❌ No Google results found.")
             return

        print(f"✅ Success! Found {len(results)} results:")
        for i, r in enumerate(results):
            print(f"\n--- Result {i+1} ---")
            print(f"Title: {r.title}")
            print(f"Link:  {r.url}")
            print(f"Desc:  {r.description}")

    except Exception as e:
        print(f"❌ Google Error: {e}")

def test_wikipedia(query):
    print(f"\n📚 Testing Wikipedia with query: '{query}'...")
    try:
        import wikipedia
        search_res = wikipedia.search(query, results=1)
        if search_res:
             print(f"✅ Page Found: {search_res[0]}")
             summary = wikipedia.summary(search_res[0], sentences=2)
             print(f"📖 Summary: {summary}")
        else:
             print("❌ No Wikipedia page found.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("========================================")
    print("   🦆 SEARCH BENCHMARK TOOL 🦆")
    print("========================================")
    
    while True:
        print("\nOptions:")
        print("1. Google Search (New Scraper)")
        print("2. Wikipedia (Fallback)")
        print("3. DuckDuckGo (Likely Blocked)")
        print("q. Quit")
        
        choice = input("\nSelect option (1-3, q): ").strip()
        
        if choice.lower() == 'q':
            break
            
        query = input("Enter search query: ").strip()
        if not query:
            continue
            
        if choice == '1':
            test_google(query)
        elif choice == '2':
            test_wikipedia(query)
        elif choice == '3':
            test_search(query, 'lite')
        else:
            print("Invalid choice.")

    print("Goodbye!")
