"""
Jarvis Intent Classifier
========================
Classifies user input BEFORE any action is taken.

Modes:
- COMMAND: System action (open app, volume, etc.)
- QUESTION: Knowledge query (who is, what is, etc.)  
- SEARCH: Web search (news, weather, general info)
- PLAY_MUSIC: Music playback request
- UNCLEAR: Need clarification
"""

import re
from typing import Dict, Tuple, Optional

# Known command patterns (high confidence direct match)
COMMAND_PATTERNS = {
    # App opening patterns
    r"open\s+(\w+)": "open_app",
    r"launch\s+(\w+)": "open_app",
    r"start\s+(\w+)": "open_app",
    # Volume patterns - INCLUDING "can you" variations
    r"(volume\s+up|louder|increase\s+volume|turn\s+up)": "volume_up",
    r"(volume\s+down|quieter|decrease\s+volume|turn\s+down)": "volume_down",
    r"(can you|please|could you).*(increase|raise|turn up|louder).*(volume|sound)": "volume_up",
    r"(can you|please|could you).*(decrease|lower|turn down|quieter).*(volume|sound)": "volume_down",
    r"(can you|please|could you).*(mute|unmute)": "mute_toggle",
    r"(mute|unmute)": "mute_toggle",
    # Media patterns
    r"(next\s+song|skip|next\s+track)": "media_next",
    r"(previous\s+song|back|previous\s+track)": "media_prev",
    r"(pause|resume|play\s+music|stop\s+music)": "media_control",
    # System patterns
    r"(lock\s+screen|lock\s+computer)": "lock",
    r"(shut\s*down|shutdown|turn\s+off)": "shutdown",
    r"(restart|reboot)": "restart",
    r"(take\s+screenshot|screenshot)": "screenshot",
}

# CONVERSATIONAL / GENERAL KNOWLEDGE (Goes to LLM)
# We want Jarvis to answer these directly without searching if possible
CONVERSATIONAL_PATTERNS = [
    # Personal
    r"who are you", r"what('s| is) your name", r"what do you know about me",
    r"how are you", r"introduce yourself",
    # General queries (LLM should answer these)
    r"explain", r"define", r"meaning of",
    r"why (is|are|do|does)", r"how (do|does|can|to)",
    r"write (a|an|the)", r"create (a|an|the)",
    r"tell me a (story|joke|fact)", 
    r"what is (a|an) .*", # "What is a loop" -> LLM
    r"(help|assist) me",
    
    r"(help|assist) me",
    
    # Semantic / Broken English Patterns (Broad matching)
    r"what.*(do|are|is|u).*know.*about", # "what are you know about..."
    r"tell.*me.*(all|everything).*about", # "tell me all you know about..."
    r"give.*(me|us|an).*overview",
    r"talk.*about",
    r"who\s+(am|are)\s+(i|we)", # "Who am I?"
    r"you\s+know\s+who\s+(am|are)\s+(i|we)", # "You know who am I?"
]

# Statements / Chatter (Should be ignored or acknowledged, not searched)
STATEMENT_PATTERNS = [
    r"^i (am|will|have|think|feel|want|going)", # "I am going to..."
    r"^(it|that|this) (is|was|looks|seems)",    # "It is nice"
    r"^just (saying|checking)",
    r"^never mind",
]

# External Knowledge (Explicit Wikipedia/Fact lookup)
QUESTION_KEYWORDS = [
    # Specific entity/fact lookups
    "who is", "who were", # "Who is Obama" -> Wiki
    "when was", "when did", "when is",
    "where is", "where are",
    "what is the capital", "what is the population",
    "who invented", "who created",
]

# Web Search (Explicit search intent)
SEARCH_KEYWORDS = [
    "search for", "search online", "look up", "find",
    "news about", "news on", "latest news",
    "weather", "price of", "stock",
    "buy", "shop for", "review",
]

# Music playback patterns
MUSIC_PATTERNS = [
    r"play\s+(.+?)\s+(on|in)\s+(spotify|youtube|yt)",
    r"play\s+(.+?)\s+spotify",
    r"play\s+(.+?)\s+youtube",
    r"play\s+song\s+(.+)",
    r"play\s+(.+)",  # Generic "play X" - default to spotify
]

# Known app names for fuzzy matching
KNOWN_APPS = {
    "chrome": ["chrome", "crome", "grome", "krom", "browser"],
    "spotify": ["spotify", "spotifi", "spotyfy"],
    "youtube": ["youtube", "utube", "you tube", "yt"],
    "tiktok": ["tiktok", "tik tok", "tick tock", "tictok"],
    "chatgpt": ["chatgpt", "chat gpt", "gpt", "charge gpt", "chargy", "charge-y"],
    "whatsapp": ["whatsapp", "whats app", "watsapp"],
    "notepad": ["notepad", "note pad", "notes"],
    "calculator": ["calculator", "calc", "calculate"],
    "gmail": ["gmail", "g mail", "email", "mail"],
    "instagram": ["instagram", "insta", "ig"],
    "twitter": ["twitter", "x", "tweet"],
    "facebook": ["facebook", "fb"],
}


def fuzzy_match_app(text: str) -> Tuple[Optional[str], float]:
    """Try to match text to a known app name with confidence score."""
    text_lower = text.lower().strip()
    
    for app_name, variants in KNOWN_APPS.items():
        for variant in variants:
            if variant in text_lower:
                # Exact match = high confidence
                if variant == text_lower or f"open {variant}" == text_lower:
                    return app_name, 0.95
                # Partial match = medium confidence
                return app_name, 0.75
    
    return None, 0.0


def extract_music_request(text: str) -> Tuple[Optional[str], Optional[str], float]:
    """Extract song name and platform from music request."""
    text_lower = text.lower().strip()
    
    for pattern in MUSIC_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            groups = match.groups()
            if len(groups) >= 3:
                song = groups[0].strip()
                platform = groups[2].strip()
            elif len(groups) >= 1:
                song = groups[0].strip()
                platform = "spotify"  # Default
            else:
                continue
            
            # Clean song name
            song = re.sub(r'\s+(on|in)\s+(spotify|youtube|yt)$', '', song).strip()
            
            if song and len(song) > 2:
                return song, platform, 0.85
    
    return None, None, 0.0


def classify_intent(text: str) -> Dict:
    """
    Classify user input into intent category.
    
    Returns:
        {
            "mode": "COMMAND" | "QUESTION" | "SEARCH" | "PLAY_MUSIC" | "UNCLEAR",
            "confidence": 0.0 - 1.0,
            "action": specific action if applicable,
            "params": extracted parameters,
            "clarification": suggested question if unclear
        }
    """
    if not text or not text.strip():
        return {
            "mode": "UNCLEAR",
            "confidence": 0.0,
            "clarification": "I didn't hear anything. Could you repeat?"
        }
    
    text_lower = text.lower().strip()
    
    # 1. Check for COMMAND patterns (highest priority)
    for pattern, action in COMMAND_PATTERNS.items():
        match = re.search(pattern, text_lower)
        if match:
            # For "open X" commands, try to match the app
            if action == "open_app":
                app_text = match.group(1) if match.groups() else ""
                matched_app, app_conf = fuzzy_match_app(app_text)
                
                if matched_app and app_conf >= 0.7:
                    return {
                        "mode": "COMMAND",
                        "confidence": app_conf,
                        "action": "open_app",
                        "params": {"app": matched_app}
                    }
                elif app_conf > 0.5:
                    return {
                        "mode": "UNCLEAR",
                        "confidence": app_conf,
                        "action": "open_app",
                        "params": {"raw": app_text},
                        "clarification": f"Did you mean to open {matched_app}?"
                    }
                else:
                    # Unknown app - try fuzzy search
                    return {
                        "mode": "UNCLEAR",
                        "confidence": 0.4,
                        "action": "open_app",
                        "params": {"raw": app_text},
                        "clarification": f"I don't recognize '{app_text}'. Which app did you mean?"
                    }
            else:
                # Direct action (volume, media, etc.)
                return {
                    "mode": "COMMAND",
                    "confidence": 0.9,
                    "action": action,
                    "params": {}
                }
    
    # 2. Check for PERSONAL/CONVERSATIONAL questions (goes to LLM, not search)
    for pattern in CONVERSATIONAL_PATTERNS:
        if re.search(pattern, text_lower):
            return {
                "mode": "CONVERSATIONAL",
                "confidence": 0.9,
                "action": "llm_chat",
                "params": {"message": text}
            }
    
    # 3. Check for MUSIC playback
    song, platform, music_conf = extract_music_request(text)
    if song and music_conf >= 0.7:
        return {
            "mode": "PLAY_MUSIC",
            "confidence": music_conf,
            "action": "play_song",
            "params": {"song": song, "platform": platform}
        }
    
    # 4. Check for QUESTION keywords (external knowledge search)
    for keyword in QUESTION_KEYWORDS:
        if keyword in text_lower:
            # Extract the actual question topic
            topic = text_lower.replace(keyword, "").strip()
            topic = re.sub(r'^(a|an|the)\s+', '', topic)  # Remove articles
            
            # Skip if topic is about "you" or "me" - that's conversational
            if topic in ["you", "me", "yourself", "myself"] or not topic:
                return {
                    "mode": "CONVERSATIONAL",
                    "confidence": 0.85,
                    "action": "llm_chat",
                    "params": {"message": text}
                }
            
            return {
                "mode": "QUESTION",
                "confidence": 0.85,
                "action": "search_wikipedia",
                "params": {"query": topic}
            }
    
    # 4. Check for SEARCH keywords
    for keyword in SEARCH_KEYWORDS:
        if keyword in text_lower:
            # Extract search query
            query = text_lower
            for kw in SEARCH_KEYWORDS:
                query = query.replace(kw, "").strip()
            
            return {
                "mode": "SEARCH",
                "confidence": 0.8,
                "action": "search_web",
                "params": {"query": query if query else text}
            }
    
    # 5. Check if it looks like a question (ends with ?)
    if text.strip().endswith("?"):
        return {
            "mode": "QUESTION",
            "confidence": 0.7,
            "action": "search_wikipedia",
            "params": {"query": text.rstrip("?")}
        }
    

    
    # 6. Check for STATEMENTS (Treat as Conversational, not Ignore)
    for pattern in STATEMENT_PATTERNS:
        if re.search(pattern, text_lower):
            return {
                "mode": "CONVERSATIONAL",  # Changed from IGNORE
                "confidence": 0.85,
                "action": "llm_chat",
                "params": {"message": text}
            }

    # 7. Unclear / Fallback logic
    # If text has no clear keywords but is long, it's likely conversational
    if len(text.split()) > 3:
        return {
            "mode": "CONVERSATIONAL",  # Fallback to chat instead of Search
            "confidence": 0.5,
            "action": "llm_chat",
            "params": {"message": text}
        }
    
    # If very short (1-2 words) and no keywords -> Unclear
    if len(text.split()) <= 2:
        return {
            "mode": "UNCLEAR",
            "confidence": 0.3,
            "clarification": f"I'm not sure what you mean by '{text}'."
        }
    
    # 8. Default: Treat as general search with medium confidence
    return {
        "mode": "SEARCH",
        "confidence": 0.6,
        "action": "search_web",
        "params": {"query": text}
    }

def preprocess_query(raw_query: str, intent_mode: str = "SEARCH") -> str:
    """
    Clean and expand a raw query into a proper search query.
    Fixes broken grammar, expands abbreviations, and clarifies intent.
    """
    if not raw_query or not raw_query.strip():
        return raw_query
    
    query = raw_query.strip().lower()
    
    # 0. Smart Extraction (Semantic Topic extraction)
    # "tell me about X" -> "X"
    extract_patterns = [
        r"tell.*me.*about\s+(.*)",
        r"what.*know.*about\s+(.*)",
        r"overview.*of\s+(.*)",
        r"information.*on\s+(.*)",
    ]
    for pattern in extract_patterns:
        match = re.search(pattern, query)
        if match:
            # Found a semantic Topic! Return just the topic.
            return match.group(1).strip()
    
    # 1. Remove incomplete phrases
    incomplete_patterns = [
        r'\.\.\.$', r'\.\.\s*$', r'\s+is$', r'\s+are$', r'\s+the$',
        r'\s+a$', r'\s+an$', r'\s+of$', r'\s+for$', r'\s+on$'
    ]
    for pattern in incomplete_patterns:
        query = re.sub(pattern, '', query).strip()
    
    # 2. Fix common misheard/typo patterns
    typo_fixes = {
        r"main full of": "main nutrients in",
        r"main of": "meaning of",
        r"meaningful of": "meaning of",
        r"the other side of israel": "Palestinian perspective on Israel conflict",
        r"charge-y|chargy|charge gpt": "ChatGPT",
        r"groom|crome|krom": "Chrome",
        r"watis": "what is",
        r"wat is": "what is",
    }
    for pattern, replacement in typo_fixes.items():
        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
        
    # Remove trailing question mark for search queries
    query = query.rstrip("?")
    
    # 3. Expand question fragments into proper questions
    if intent_mode == "QUESTION":
        # (Removed aggressive 'what is' formatting - let LLM/Search handle natural phrasing)
        pass
    
    # 4. For news/search, add context words
    if intent_mode == "SEARCH":
        news_keywords = ["news", "latest", "today", "current", "recent"]
        if any(kw in query for kw in news_keywords):
            # Add date context for news
            query = query.replace("latest news", "news today")
    
    # 5. Clean up extra spaces
    query = re.sub(r'\s+', ' ', query).strip()
    
    # 6. Capitalize properly
    if query and len(query) > 0:
        query = query[0].upper() + query[1:]
    
    return query


def validate_result(result: str, original_query: str, intent_mode: str = "SEARCH") -> Dict:
    """
    Validate if a search result is relevant to the original query.
    
    Returns:
        {
            "valid": True/False,
            "reason": explanation if invalid,
            "confidence": 0.0 - 1.0
        }
    """
    if not result or not result.strip():
        return {"valid": False, "reason": "Empty result", "confidence": 0.0}
    
    result_lower = result.lower()
    query_lower = original_query.lower()
    
    # 1. Check for error messages in result
    error_indicators = [
        "could not", "couldn't", "error", "failed", "not found",
        "no results", "no information", "unable to"
    ]
    if any(err in result_lower for err in error_indicators):
        return {"valid": False, "reason": "Result contains error", "confidence": 0.2}
    
    # 2. Check for keyword overlap
    query_words = set(query_lower.split())
    # Remove common words
    stop_words = {"the", "a", "an", "is", "are", "what", "who", "how", "why", "when", "where", "of", "in", "on", "for", "to"}
    query_words = query_words - stop_words
    
    result_words = set(result_lower.split())
    overlap = query_words.intersection(result_words)
    
    if len(query_words) > 0:
        overlap_ratio = len(overlap) / len(query_words)
    else:
        overlap_ratio = 0.5  # Default for empty query words
    
    # 3. Result length check
    if len(result) < 20:
        return {"valid": False, "reason": "Result too short", "confidence": 0.3}
    
    # 4. Final validation
    if overlap_ratio >= 0.3:
        return {"valid": True, "reason": "Good keyword overlap", "confidence": 0.7 + (overlap_ratio * 0.3)}
    elif len(result) > 100:
        # Long result might still be relevant even without keyword overlap
        return {"valid": True, "reason": "Detailed result", "confidence": 0.6}
    else:
        return {"valid": False, "reason": "Low relevance", "confidence": overlap_ratio}


def get_smart_fallback(intent: Dict, action_attempted: str = None) -> str:
    """
    Generate an intelligent fallback message instead of generic errors.
    
    Returns a helpful, transparent message that:
    - Admits confusion when appropriate
    - Suggests alternative actions
    - Never performs random actions
    """
    mode = intent.get("mode", "UNCLEAR")
    params = intent.get("params", {})
    
    if action_attempted == "open_app":
        app_name = params.get("raw", params.get("app", "that app"))
        return f"I don't recognize '{app_name}'. Could you spell it or try a different name?"
    
    elif action_attempted == "search_web":
        query = params.get("query", "your request")
        return f"I couldn't find good results for '{query}'. Try being more specific?"
    
    elif action_attempted == "search_wikipedia":
        query = params.get("query", "that topic")
        return f"No Wikipedia article found for '{query}'. Should I search the web instead?"
    
    elif mode == "UNCLEAR":
        clarification = intent.get("clarification")
        if clarification:
            return clarification
        return "I'm not sure what you mean. Could you rephrase that?"
    
    else:
        return "I didn't understand. Could you try again?"


def should_ask_clarification(intent: Dict) -> bool:
    """
    Determine if we should ask for clarification based on confidence policy.
    Policy:
    - High (>0.85): Act immediately.
    - Medium (0.65 - 0.85): Act, but confirm if risky.
    - Low (<0.65): ALWAYS ask clarification.
    """
    conf = intent.get("confidence", 0.0)
    mode = intent.get("mode", "UNCLEAR")
    
    # IGNORE mode never asks clarification (it ignores)
    if mode == "IGNORE":
        return False
        
    # CONVERSATIONAL logic: LLM is robust, so we allow lower confidence
    if mode == "CONVERSATIONAL" and conf > 0.6:
        return False
        
    # COMMAND/SEARCH logic: Be strict
    if conf < 0.75:
        return True
        
    return False

def get_clarification_prompt(intent: Dict) -> str:
    """Generate smart clarification question."""
    mode = intent.get("mode", "UNCLEAR")
    text = intent.get("params", {}).get("query", "that")
    
    if mode == "SEARCH":
         return f"Do you want me to search the web for '{text}'?"
    if mode == "QUESTION":
         return f"Do you want me to look up '{text}' on Wikipedia?"
    if mode == "COMMAND":
         return f"I'm not sure. Did you want me to {intent.get('action')}?"
         
    return intent.get("clarification", "I didn't quite catch that.")


# Quick test
if __name__ == "__main__":
    test_inputs = [
        "open chrome",
        "open chat gpt",
        "open groom",  # Should ask clarification
        "play eye of the tiger on spotify",
        "what is a banana",
        "search for latest news in israel",
        "volume up",
        "the other side",  # Unclear
        "can you increase the volume?",
    ]
    
    print("Intent Classification Tests:")
    print("=" * 60)
    for text in test_inputs:
        result = classify_intent(text)
        print(f"\n'{text}'")
        print(f"  Mode: {result.get('mode')}")
        print(f"  Confidence: {result.get('confidence', 0):.2f}")
        if result.get('action'):
            print(f"  Action: {result.get('action')}")
        if result.get('params'):
            print(f"  Params: {result.get('params')}")
        if result.get('clarification'):
            print(f"  Clarify: {result.get('clarification')}")
