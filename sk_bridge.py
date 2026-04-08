# sk_bridge.py
# =============
# Bridge between Semantic Kernel and LangChain/LangGraph
# Converts SK functions to LangChain tools

from typing import Any, Optional
from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field
from sk_kernel import get_kernel


def create_langchain_tools():
    """
    Convert all Semantic Kernel functions to LangChain tools.
    This bridges SK to LangGraph.
    
    Returns:
        List of LangChain Tool objects
    """
    kernel = get_kernel()
    tools = []
    
    for func_info in kernel.get_all_functions():
        plugin_name = func_info["plugin"]
        func_name = func_info["name"]
        sk_func = func_info["function"]
        
        # Get description from SK function
        description = sk_func.description or func_name
        
        # Create a wrapper that calls SK
        def make_wrapper(pn, fn):
            def wrapper(**kwargs):
                return kernel.execute_function(pn, fn, **kwargs)
            return wrapper
        
        # Get parameters from SK function metadata
        params = {}
        if hasattr(sk_func, "parameters") and sk_func.parameters:
            for param in sk_func.parameters:
                params[param.name] = param.description or param.name
        
        # Create LangChain tool
        full_name = plugin_name + "_" + func_name
        
        if params:
            # Create dynamic Pydantic model for structured tool
            tool = Tool(
                name=full_name,
                description=description,
                func=make_wrapper(plugin_name, func_name),
            )
        else:
            tool = Tool(
                name=full_name,
                description=description,
                func=make_wrapper(plugin_name, func_name),
            )
        
        tools.append(tool)
        print("[BRIDGE] Registered tool:", full_name)
    
    return tools


# Pre-defined tools with proper argument handling
def get_sk_tools():
    """
    Get pre-defined LangChain tools that wrap SK functions.
    These have proper argument schemas.
    """
    kernel = get_kernel()
    
    tools = []
    
    # === Windows Plugin Tools ===
    
    @StructuredTool.from_function
    def launch_app(app_name: str) -> str:
        """Launch an application on Windows. Use for: open chrome, start spotify, launch notepad."""
        return kernel.execute_function("windows", "launch_app", app_name=app_name)
    tools.append(launch_app)
    
    @StructuredTool.from_function
    def open_url(url: str) -> str:
        """Open a URL in the default browser."""
        return kernel.execute_function("windows", "open_url", url=url)
    tools.append(open_url)
    
    @StructuredTool.from_function
    def set_volume(action: str) -> str:
        """Control system volume. Actions: up, down, mute, unmute."""
        return kernel.execute_function("windows", "set_volume", action=action)
    tools.append(set_volume)
    
    @StructuredTool.from_function
    def control_media(action: str) -> str:
        """Control media playback. Actions: play, pause, next, previous, stop."""
        return kernel.execute_function("windows", "control_media", action=action)
    tools.append(control_media)
    
    @StructuredTool.from_function
    def lock_screen() -> str:
        """Lock the Windows screen."""
        return kernel.execute_function("windows", "lock_screen")
    tools.append(lock_screen)
    
    @StructuredTool.from_function
    def take_screenshot() -> str:
        """Take a screenshot using the snipping tool."""
        return kernel.execute_function("windows", "take_screenshot")
    tools.append(take_screenshot)
    
    @StructuredTool.from_function
    def play_on_youtube(query: str) -> str:
        """Play a song or video on YouTube. Use for: play song X, play video X."""
        return kernel.execute_function("windows", "play_on_youtube", query=query)
    tools.append(play_on_youtube)
    
    @StructuredTool.from_function
    def ask_confirmation(question: str) -> str:
        """Ask user for confirmation (yes/no) before dangerous actions."""
        return kernel.execute_function("windows", "ask_confirmation", question=question)
    tools.append(ask_confirmation)
    
    # === FileIO Plugin Tools ===
    
    @StructuredTool.from_function
    def list_files(directory: str) -> str:
        """List files in a directory (documents, desktop, downloads, or path)."""
        return kernel.execute_function("fileio", "list_files", directory=directory)
    tools.append(list_files)
    
    @StructuredTool.from_function
    def search_file(filename: str) -> str:
        """Search for a file by name in common directories."""
        return kernel.execute_function("fileio", "search_file", filename=filename)
    tools.append(search_file)
    
    @StructuredTool.from_function
    def read_file(filepath: str) -> str:
        """Read the contents of a text file."""
        return kernel.execute_function("fileio", "read_file", filepath=filepath)
    tools.append(read_file)
    
    @StructuredTool.from_function
    def write_file(filepath: str, content: str) -> str:
        """Write content to a file."""
        return kernel.execute_function("fileio", "write_file", filepath=filepath, content=content)
    tools.append(write_file)
    
    # === Time Plugin Tools ===
    
    @StructuredTool.from_function
    def get_time() -> str:
        """Get the current time."""
        return kernel.execute_function("time", "get_time")
    tools.append(get_time)
    
    @StructuredTool.from_function
    def get_date() -> str:
        """Get the current date."""
        return kernel.execute_function("time", "get_date")
    tools.append(get_date)
    
    @StructuredTool.from_function
    def get_datetime() -> str:
        """Get both current date and time."""
        return kernel.execute_function("time", "get_datetime")
    tools.append(get_datetime)
    
    @StructuredTool.from_function
    def get_day() -> str:
        """Get the current day of the week."""
        return kernel.execute_function("time", "get_day")
    tools.append(get_day)
    
    # === Power Plugin Tools ===
    
    @StructuredTool.from_function
    def shutdown_pc() -> str:
        """Shutdown the computer. Use when user says 'shut down', 'turn off computer'."""
        return kernel.execute_function("power", "shutdown_pc")
    tools.append(shutdown_pc)
    
    @StructuredTool.from_function
    def restart_pc() -> str:
        """Restart the computer. Use when user says 'restart', 'reboot'."""
        return kernel.execute_function("power", "restart_pc")
    tools.append(restart_pc)
    
    @StructuredTool.from_function
    def sleep_pc() -> str:
        """Put the computer to sleep mode."""
        return kernel.execute_function("power", "sleep_pc")
    tools.append(sleep_pc)
    
    @StructuredTool.from_function
    def set_brightness(level: int) -> str:
        """Set screen brightness (0-100). Use when user says 'set brightness to 50', 'increase brightness'."""
        return kernel.execute_function("power", "set_brightness", level=level)
    tools.append(set_brightness)
    
    @StructuredTool.from_function
    def get_brightness() -> str:
        """Get current screen brightness level."""
        return kernel.execute_function("power", "get_brightness")
    tools.append(get_brightness)
    
    @StructuredTool.from_function
    def get_battery() -> str:
        """Get battery percentage and charging status."""
        return kernel.execute_function("power", "get_battery")
    tools.append(get_battery)
    
    @StructuredTool.from_function
    def cancel_shutdown() -> str:
        """Cancel a scheduled shutdown."""
        return kernel.execute_function("power", "cancel_shutdown")
    tools.append(cancel_shutdown)
    
    # === Network Plugin Tools ===
    
    @StructuredTool.from_function
    def get_ip_address() -> str:
        """Get the computer's IP address (local and public). Use when user asks 'what is my IP'."""
        return kernel.execute_function("network", "get_ip_address")
    tools.append(get_ip_address)
    
    @StructuredTool.from_function
    def get_wifi_networks() -> str:
        """List available WiFi networks. Use when user asks 'what WiFi networks are available'."""
        return kernel.execute_function("network", "get_wifi_networks")
    tools.append(get_wifi_networks)
    
    @StructuredTool.from_function
    def check_internet_speed() -> str:
        """Check internet speed (Download/Upload). Takes ~20 seconds."""
        return kernel.execute_function("network", "check_internet_speed")
    tools.append(check_internet_speed)
    
    @StructuredTool.from_function
    def toggle_wifi(state: str) -> str:
        """Turn WiFi on or off. State must be 'on' or 'off'."""
        return kernel.execute_function("network", "toggle_wifi", state=state)
    tools.append(toggle_wifi)
    
    @StructuredTool.from_function
    def toggle_bluetooth(state: str) -> str:
        """Turn Bluetooth on or off. State must be 'on' or 'off'."""
        return kernel.execute_function("network", "toggle_bluetooth", state=state)
    tools.append(toggle_bluetooth)
    
    @StructuredTool.from_function
    def connect_device(device_type: str) -> str:
        """Connect to headphones, speaker, or phone. Use when user says 'connect to headphones'."""
        return kernel.execute_function("network", "connect_device", device_type=device_type)
    tools.append(connect_device)
    
    # === Memory Plugin Tools ===
    
    @StructuredTool.from_function
    def remember_fact(fact: str) -> str:
        """Remember a fact about the user."""
        return kernel.execute_function("memory", "remember_fact", fact=fact)
    tools.append(remember_fact)
    
    @StructuredTool.from_function
    def recall_memories() -> str:
        """Recall what you remember about the user."""
        return kernel.execute_function("memory", "recall_memories")
    tools.append(recall_memories)
    
    @StructuredTool.from_function
    def forget_fact(fact_to_forget: str) -> str:
        """Forget/delete a specific memory. Use when user says 'forget that' or 'delete memory'."""
        return kernel.execute_function("memory", "forget_fact", fact_to_forget=fact_to_forget)
    tools.append(forget_fact)
    
    @StructuredTool.from_function
    def reset_system() -> str:
        """Reset conversation history. Use when user says 'reset system', 'clear history', 'start fresh'."""
        return kernel.execute_function("memory", "reset_system")
    tools.append(reset_system)
    
    # === Spotify Plugin Tools ===
    
    @StructuredTool.from_function
    def spotify_play(track_name: str) -> str:
        """Play a song on Spotify. Use when user says 'play X on Spotify'."""
        return kernel.execute_function("spotify", "spotify_play_track", track_name=track_name)
    tools.append(spotify_play)
    
    @StructuredTool.from_function
    def spotify_pause() -> str:
        """Pause or resume Spotify playback."""
        return kernel.execute_function("spotify", "spotify_pause_resume")
    tools.append(spotify_pause)
    
    @StructuredTool.from_function
    def spotify_next() -> str:
        """Skip to next track on Spotify."""
        return kernel.execute_function("spotify", "spotify_next")
    tools.append(spotify_next)
    
    @StructuredTool.from_function
    def spotify_previous() -> str:
        """Go to previous track on Spotify."""
        return kernel.execute_function("spotify", "spotify_previous")
    tools.append(spotify_previous)
    
    @StructuredTool.from_function
    def spotify_like() -> str:
        """Add current song to Liked Songs. Use when user says 'I love this song' or 'like this'."""
        return kernel.execute_function("spotify", "spotify_like_song")
    tools.append(spotify_like)
    
    @StructuredTool.from_function
    def spotify_now_playing() -> str:
        """Get the currently playing song on Spotify."""
        return kernel.execute_function("spotify", "spotify_now_playing")
    tools.append(spotify_now_playing)
    
    # === YouTube Plugin Tools ===
    
    @StructuredTool.from_function
    def youtube_play(topic: str) -> str:
        """Play a video on YouTube. Use when user says 'play X on YouTube' or 'watch X'."""
        return kernel.execute_function("youtube", "youtube_play", topic=topic)
    tools.append(youtube_play)
    
    @StructuredTool.from_function
    def youtube_search(query: str) -> str:
        """Search YouTube without auto-playing."""
        return kernel.execute_function("youtube", "youtube_search", query=query)
    tools.append(youtube_search)
    
    # === Media Control Plugin Tools (Universal) ===
    
    @StructuredTool.from_function
    def stop_media() -> str:
        """Stop/pause any playing media. Use when user says 'stop', 'quiet', 'pause'. DO NOT close apps."""
        return kernel.execute_function("mediacontrol", "stop_media")
    tools.append(stop_media)
    
    @StructuredTool.from_function
    def play_media() -> str:
        """Resume playing media. Use when user says 'play', 'resume'."""
        return kernel.execute_function("mediacontrol", "play_media")
    tools.append(play_media)
    
    @StructuredTool.from_function
    def next_media() -> str:
        """Skip to next track in any media player."""
        return kernel.execute_function("mediacontrol", "next_media")
    tools.append(next_media)
    
    @StructuredTool.from_function
    def previous_media() -> str:
        """Go to previous track in any media player."""
        return kernel.execute_function("mediacontrol", "previous_media")
    tools.append(previous_media)
    
    # === System Plugin Tools ===
    
    @StructuredTool.from_function
    def system_status() -> str:
        """Get PC health status - CPU, RAM, Battery. Use when user asks 'how is my PC?' or 'system status'."""
        return kernel.execute_function("system", "system_status")
    tools.append(system_status)
    
    @StructuredTool.from_function
    def cpu_usage() -> str:
        """Get CPU usage percentage."""
        return kernel.execute_function("system", "cpu_usage")
    tools.append(cpu_usage)
    
    @StructuredTool.from_function
    def ram_usage() -> str:
        """Get RAM/memory usage."""
        return kernel.execute_function("system", "ram_usage")
    tools.append(ram_usage)
    
    @StructuredTool.from_function
    def battery_status() -> str:
        """Get battery level and charging status."""
        return kernel.execute_function("system", "battery_status")
    tools.append(battery_status)
    
    @StructuredTool.from_function
    def top_processes() -> str:
        """List top 5 processes by memory usage."""
        return kernel.execute_function("system", "running_processes")
    tools.append(top_processes)
    
    # === Vision Plugin Tools ===
    
    @StructuredTool.from_function
    def read_screen() -> str:
        """Read text from the screen using OCR. Use when user says 'read screen', 'what's on screen', 'look at screen'."""
        return kernel.execute_function("vision", "read_screen")
    tools.append(read_screen)
    
    @StructuredTool.from_function
    def take_screenshot() -> str:
        """Take a screenshot and save to desktop."""
        return kernel.execute_function("vision", "take_screenshot_and_save")
    tools.append(take_screenshot)
    
    # === Smart Search Tool (Cascading) ===
    
    @StructuredTool.from_function
    def duckduckgo_search(query: str) -> str:
        """Smart multi-stage search. Tries Israel first, then global."""
        from duckduckgo_search import DDGS
        
        def format_results(results, source):
            summary = f"--- Results ({source}) ---\n"
            for r in results[:3]:
                title = r.get('title', '')
                body = r.get('body', '')[:200]
                url = r.get('href', '')
                summary += f"• {title}: {body}\n  URL: {url}\n"
            return summary
        
        print(f"[ARCH] Smart Search: {query}")
        
        # Attempt 1: Israel region
        try:
            results = DDGS().text(query, region='il-he', max_results=3)
            if results:
                return format_results(results, "Israel")
        except:
            pass
        
        # Attempt 2: Global fallback
        try:
            print("[ARCH] Fallback to Global...")
            results = DDGS().text(query, max_results=3)
            if results:
                return format_results(results, "Global")
        except Exception as e:
            return f"Search Error: {e}"
        
        return "No results found. Try rephrasing your query."
    tools.append(duckduckgo_search)
    
    # === Deep Read Tool ===
    
    @StructuredTool.from_function
    def read_website_content(url: str) -> str:
        """Read full content from a webpage URL. Use AFTER searching to get full article details."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            print(f"[READER] Fetching text from: {url}")
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'  # Force Hebrew support
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
            
            # Get text
            text = soup.get_text()
            
            # Clean text (remove empty lines)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:4000]  # First 4000 chars to avoid overflow
        except ImportError:
            return "Install: pip install requests beautifulsoup4"
        except Exception as e:
            return f"Error reading website: {e}"
    tools.append(read_website_content)
    
    # === Deep Thinking Research Tool ===
    # Uses 8 layers of LLM reasoning with detailed logging
    
    # Global LLM invoker - will be set by brain.py
    _llm_invoker = None
    
    def set_research_llm(invoker):
        """Set the LLM invoker function for research."""
        nonlocal _llm_invoker
        _llm_invoker = invoker
        print("[BRIDGE] Research LLM callback registered")
    
    # Store setter in tools list for brain.py to access
    tools.append(("_set_research_llm", set_research_llm))
    
    @StructuredTool.from_function
    def smart_research(query: str) -> str:
        """
        DEEP THINKING RESEARCH with 8 layers of reasoning.
        Uses multiple LLM calls for understanding, query generation, filtering, and summarization.
        """
        # Check if we have LLM access
        if _llm_invoker:
            try:
                from thinking_research import deep_thinking_research
                return deep_thinking_research(query, _llm_invoker)
            except ImportError as e:
                print(f"[RESEARCH] thinking_research not available: {e}")
            except Exception as e:
                print(f"[RESEARCH] Deep thinking error: {e}")
        
        # Fallback to simple research if LLM callback not available
        print(f"\n[RESEARCH] 🔍 Starting simple research: '{query}'")
        print("[RESEARCH] ⚠️ LLM callback not set - using simple mode")
        
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            import trafilatura
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            bad_domains = ['baidu.com', 'weibo.com', 'qq.com', 'yandex.ru', 'current.com']
            
            # Search
            print("[RESEARCH] 🔍 Searching...")
            all_results = []
            seen_urls = set()
            
            for sq in [query, f"{query} latest", f"{query} news"]:
                try:
                    results = DDGS().text(sq, max_results=3)
                    for r in results:
                        url = r.get('href', '')
                        if url not in seen_urls and not any(bad in url for bad in bad_domains):
                            seen_urls.add(url)
                            all_results.append({
                                'url': url,
                                'title': r.get('title', ''),
                                'snippet': r.get('body', '')
                            })
                except:
                    continue
            
            print(f"[RESEARCH] ✅ Found {len(all_results)} results")
            
            if not all_results:
                return "לא מצאתי תוצאות. נסה לנסח אחרת."
            
            # Scrape
            print("[RESEARCH] 🕷️ Scraping...")
            
            def scrape(r):
                try:
                    downloaded = trafilatura.fetch_url(r['url'])
                    if downloaded:
                        text = trafilatura.extract(downloaded)
                        if text and len(text) > 100:
                            return {**r, 'content': text[:1500]}
                except:
                    pass
                return {**r, 'content': r['snippet']}
            
            scraped = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                for result in executor.map(scrape, all_results[:5]):
                    if result.get('content'):
                        scraped.append(result)
            
            if not scraped:
                scraped = all_results[:3]
            
            # Build output
            output = f"### RESEARCH: {query} ###\n\n"
            for i, r in enumerate(scraped, 1):
                output += f"[{i}] {r.get('title', 'N/A')}\n{r.get('content', '')[:1000]}\nURL: {r['url']}\n\n"
            
            output += "\n--- Summarize the above for the user ---"
            print(f"[RESEARCH] ✅ Done ({len(scraped)} sources)")
            return output
            
        except Exception as e:
            return f"Research error: {e}"
    tools.append(smart_research)
    
    # === Telegram News Tool ===
    
    @StructuredTool.from_function
    def telegram_news(channel: str = "all", limit: int = 3, time_limit: str = None) -> str:
        """
        Read news from Telegram channels.
        
        Args:
            channel: Channel name or "all"
            limit: Number of messages to fetch (default: 3)
            time_limit: Time limit e.g. "20m", "1h" (default: None)
        """
        print(f"\n[TELEGRAM] 📰 Reading news from: {channel} (limit={limit}, time={time_limit})")
        
        try:
            from telegram_manager import get_channel_updates, get_all_news, format_news_for_jarvis, NEWS_CHANNELS
            
            if channel == "all" or channel == "הכל":
                messages = get_all_news(limit_per_channel=limit, time_limit=time_limit)
            else:
                # Try to match channel name
                if channel in NEWS_CHANNELS:
                    messages = get_channel_updates(channel, limit=limit, time_limit=time_limit)
                else:
                    # Try partial match
                    matched = None
                    for key in NEWS_CHANNELS.keys():
                        if channel in key or key in channel:
                            matched = key
                            break
                    
                    if matched:
                        messages = get_channel_updates(matched, limit=limit, time_limit=time_limit)
                    else:
                        return f"ערוץ לא נמצא: {channel}. ערוצים זמינים: {', '.join(NEWS_CHANNELS.keys())}"
            
            if not messages:
                return "לא נמצאו הודעות חדשות."
            
            result = format_news_for_jarvis(messages)
            print(f"[TELEGRAM] ✅ Got {len(messages)} messages")
            return result
            
        except ImportError as e:
            return f"Telegram not configured: {e}"
        except Exception as e:
            return f"Telegram error: {e}"
    tools.append(telegram_news)
    
    print("[BRIDGE] Created", len(tools), "SK-backed LangChain tools (GOD MODE)")
    return tools


# Export
SK_TOOLS = None

def get_all_tools():
    """Get all SK tools (lazy initialization)."""
    global SK_TOOLS
    if SK_TOOLS is None:
        SK_TOOLS = get_sk_tools()
    return SK_TOOLS
