"""
JARVIS Telegram Manager
========================
Module for reading news from Telegram channels and sending messages.
Uses Telethon (official Telegram API client).

Features:
- Read messages from predefined news channels
- Send messages to users/groups
- Async operations with sync bridge

Setup:
1. Get API credentials from https://my.telegram.org
2. Fill in API_ID and API_HASH below
3. Run this file directly to authenticate first time
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional

try:
    from telethon import TelegramClient
    from telethon.tl.types import Message
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    print("[TELEGRAM] ⚠️ Telethon not installed. Run: pip install telethon")


# ============================================
# CONFIGURATION - Fill in your credentials
# ============================================

API_ID = None
API_HASH = "YOUR_API_HASH"
SESSION_NAME = 'jarvis_session'

# ============================================
# NEWS CHANNELS DICTIONARY
# Maps Hebrew short names to Telegram usernames
# ============================================

NEWS_CHANNELS = {
    "חדשות ביטחון ללא צנזורה": "lelotsenzura",
    "חדשות 100 שטח":          "yediotnews25",
    "הערינג":                  "GbmMDm",
    "סודות החדשות":            "secrets_news1",
}


# ============================================
# GLOBAL CLIENT (lazy initialization)
# ============================================

_client: Optional[TelegramClient] = None
_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_client() -> TelegramClient:
    """Get or create Telegram client."""
    global _client
    
    if not TELETHON_AVAILABLE:
        raise ImportError("Telethon not installed. Run: pip install telethon")
    
    if API_ID is None or API_HASH is None:
        raise ValueError("API_ID and API_HASH must be set in telegram_manager.py")
    
    if _client is None:
        _client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    return _client


def _get_loop() -> asyncio.AbstractEventLoop:
    """Get or create event loop."""
    global _loop
    
    try:
        _loop = asyncio.get_event_loop()
    except RuntimeError:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    
    return _loop


# ============================================
# ASYNC CORE FUNCTIONS
# ============================================

from datetime import datetime, timedelta

def _parse_time_limit(limit_str: str) -> Optional[datetime]:
    """Parse time limit string (e.g. '20m', '1h') to datetime."""
    if not limit_str or limit_str == "None":
        return None
        
    now = datetime.now()
    try:
        if limit_str.endswith('m'):
            minutes = int(limit_str[:-1])
            return now - timedelta(minutes=minutes)
        elif limit_str.endswith('h'):
            hours = int(limit_str[:-1])
            return now - timedelta(hours=hours)
    except:
        pass
    return None

async def _get_channel_updates_async(channel_key: str, limit: int = 3, time_limit: str = None) -> List[Dict]:
    """
    Get recent messages from a news channel (async version).
    """
    # Resolve channel username
    if channel_key in NEWS_CHANNELS:
        channel = NEWS_CHANNELS[channel_key]
    else:
        channel = channel_key
    
    client = _get_client()
    cutoff_time = _parse_time_limit(time_limit)
    
    # Increase limit if filtering by time to ensure we get enough messages to filter
    fetch_limit = limit * 3 if cutoff_time else limit
    
    async with client:
        try:
            messages = []
            async for message in client.iter_messages(channel, limit=fetch_limit):
                if not message.text:
                    continue
                    
                # Time filter
                if cutoff_time:
                    # telethon dates are timezone aware (UTC), make cutoff aware if needed or naive
                    msg_date = message.date.replace(tzinfo=None)
                    if msg_date < cutoff_time:
                        continue
                        
                messages.append({
                    'text': message.text[:1000],
                    'date': message.date.strftime("%Y-%m-%d %H:%M"),
                    'id': message.id,
                    'channel': channel_key
                })
                
                if len(messages) >= limit:
                    break
            
            return messages
            
        except Exception as e:
            print(f"[TELEGRAM] ❌ Error reading {channel}: {e}")
            return []

async def _get_all_news_async(limit_per_channel: int = 2, time_limit: str = None) -> List[Dict]:
    """
    Get news from ALL configured channels.
    """
    client = _get_client()
    all_messages = []
    cutoff_time = _parse_time_limit(time_limit)
    fetch_limit = limit_per_channel * 3 if cutoff_time else limit_per_channel
    
    async with client:
        for channel_key, channel_username in NEWS_CHANNELS.items():
            try:
                channel_msgs = []
                async for message in client.iter_messages(channel_username, limit=fetch_limit):
                    if not message.text:
                        continue
                        
                    if cutoff_time:
                        msg_date = message.date.replace(tzinfo=None)
                        if msg_date < cutoff_time:
                            continue

                    channel_msgs.append({
                        'text': message.text[:500],
                        'date': message.date.strftime("%Y-%m-%d %H:%M"),
                        'id': message.id,
                        'channel': channel_key
                    })
                    
                    if len(channel_msgs) >= limit_per_channel:
                        break
                
                all_messages.extend(channel_msgs)
                
            except Exception as e:
                print(f"[TELEGRAM] ⚠️ Error reading {channel_key}: {e}")
    
    all_messages.sort(key=lambda x: x['date'], reverse=True)
    return all_messages


# ============================================
# SYNC BRIDGE FUNCTIONS
# These are what you call from synchronous code
# ============================================

def get_channel_updates(channel_key: str, limit: int = 3, time_limit: str = None) -> List[Dict]:
    """
    SYNC: Get recent messages from a news channel.
    
    Usage:
        messages = get_channel_updates("עמית סגל", limit=5)
        for msg in messages:
            print(msg['text'])
    """
    loop = _get_loop()
    return loop.run_until_complete(_get_channel_updates_async(channel_key, limit, time_limit))


def send_message(target: str, text: str) -> bool:
    """
    SYNC: Send a message to a user or group.
    
    Usage:
        send_message("username", "Hello!")
    """
    loop = _get_loop()
    return loop.run_until_complete(_send_message_async(target, text))


def get_all_news(limit_per_channel: int = 2, time_limit: str = None) -> List[Dict]:
    """
    SYNC: Get news from all configured channels.
    
    Usage:
        news = get_all_news(limit_per_channel=3)
        for item in news:
            print(f"[{item['channel']}] {item['text'][:100]}")
    """
    loop = _get_loop()
    return loop.run_until_complete(_get_all_news_async(limit_per_channel, time_limit))


def format_news_for_jarvis(messages: List[Dict]) -> str:
    """
    Format news messages for JARVIS to process.
    Clean format: time + channel + text (no markdown)
    """
    if not messages:
        return "לא נמצאו חדשות."
    
    output = ""
    current_channel = None
    
    for msg in messages:
        # Extract just the time (HH:MM)
        time_str = msg['date'].split(' ')[1] if ' ' in msg['date'] else msg['date']
        
        # Clean the text - remove markdown
        text = msg['text']
        text = text.replace('**', '').replace('__', '').replace('*', '')
        text = text.split('\n')[0][:200]  # First line, max 200 chars
        
        # Group by channel
        if msg['channel'] != current_channel:
            if current_channel is not None:
                output += "\n"
            output += f"[{msg['channel']}]\n"
            current_channel = msg['channel']
        
        output += f"  {time_str} - {text}\n"
    
    return output


def get_all_news_for_ai_summary(limit_per_channel: int = 10) -> str:
    """
    Fetch up to `limit_per_channel` messages from every configured channel and
    return a single string prompt ready for Jarvis to analyse and summarise.
    Includes ALL raw text so the model can decide what is news vs. ads/promo.
    """
    loop = _get_loop()
    all_messages = loop.run_until_complete(_get_all_news_async(limit_per_channel))
    
    if not all_messages:
        return "לא נמצאו הודעות בערוצים."
    
    lines = [
        "להלן הודעות גולמיות מערוצי הטלגרם. נתח אותן וסכם:",
        "- התעלם ממודעות, פרסומות, הזמנות להצטרף לערוצים, ספירת עוקבים, וכל תוכן שאינו חדשות.",
        "- הצג רק אירועים חשובים, אחד-לאחד, ממוין לפי חשיבות.",
        "- קבץ נושאים דומים.",
        "- ציין את שם המקור בסוגריים.",
        "---",
    ]
    
    current_channel = None
    for msg in all_messages:
        time_str = msg['date'].split(' ')[1] if ' ' in msg['date'] else msg['date']
        text = msg['text'].replace('**', '').replace('__', '').replace('*', '').strip()
        # Keep text short so total payload stays manageable
        text = text[:200]
        if msg['channel'] != current_channel:
            lines.append(f"\n=== {msg['channel']} ===")
            current_channel = msg['channel']
        lines.append(f"[{time_str}] {text}")
    
    return "\n".join(lines)



# ============================================
# FIRST-TIME AUTHENTICATION
# ============================================

async def _authenticate():
    """Interactive authentication for first-time setup."""
    if API_ID is None or API_HASH is None:
        print("=" * 50)
        print("❌ ERROR: API credentials not set!")
        print("=" * 50)
        print("\n1. Go to https://my.telegram.org")
        print("2. Log in with your phone number")
        print("3. Go to 'API development tools'")
        print("4. Create an app and get API_ID and API_HASH")
        print("5. Edit telegram_manager.py and fill in the values")
        print("\nExample:")
        print("  API_ID = 12345678")
        print('  API_HASH = "your_hash_here"')
        return
    
    client = _get_client()
    
    print("=" * 50)
    print("🔐 Telegram Authentication")
    print("=" * 50)
    
    await client.start()
    
    me = await client.get_me()
    print(f"\n✅ Connected as: {me.first_name} (@{me.username})")
    print(f"📱 Phone: {me.phone}")
    
    # Test reading from a channel
    print("\n🔍 Testing channel access...")
    try:
        async for msg in client.iter_messages("amitsegal", limit=1):
            print(f"✅ Can read channels: {msg.text[:50]}...")
            break
    except Exception as e:
        print(f"⚠️ Channel access test failed: {e}")
    
    print("\n✅ Authentication complete! Session saved.")
    print(f"   Session file: {SESSION_NAME}.session")


# ============================================
# MAIN - Run for first-time setup
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  JARVIS Telegram Manager - Setup")
    print("=" * 50 + "\n")
    
    if not TELETHON_AVAILABLE:
        print("❌ Telethon not installed!")
        print("   Run: pip install telethon")
    else:
        asyncio.run(_authenticate())
