"""
JARVIS Deep Thinking Research System v2
========================================
Multi-layer reasoning with LLM internal dialogue:

LAYER 1: UNDERSTAND  - "מה המשתמש באמת רוצה לדעת?"
LAYER 2: SUMMARIZE   - "סכם את הכוונה במשפט אחד"
LAYER 3: QUERIES     - "תן 5 שאילתות חיפוש שונות"
LAYER 4: SEARCH      - Execute searches
LAYER 5: FILTER      - "אילו תוצאות רלוונטיות?"
LAYER 6: ANALYZE     - "מה המידע החשוב כאן?"
LAYER 7: FORMULATE   - "נסח תשובה מתאימה"

Each layer has detailed logging with timestamps.
"""

import time
import re
from typing import List, Dict, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


class ThinkingLogger:
    """Detailed logger for thinking process."""
    
    def __init__(self):
        self.start_time = time.time()
        self.layer_times = {}
    
    def log(self, layer: str, message: str, emoji: str = "📝"):
        elapsed = time.time() - self.start_time
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{elapsed:.2f}s] {emoji} [{layer}] {message}")
    
    def start_layer(self, layer: str, description: str):
        self.layer_times[layer] = time.time()
        print(f"\n{'='*70}")
        self.log(layer, f"🚀 START: {description}", "🧠")
        print(f"{'='*70}")
    
    def end_layer(self, layer: str, result_preview: str = ""):
        if layer in self.layer_times:
            duration = time.time() - self.layer_times[layer]
            preview = result_preview[:100] + "..." if len(result_preview) > 100 else result_preview
            self.log(layer, f"✅ DONE ({duration:.2f}s) | Result: {preview}", "✅")
    
    def total_time(self) -> float:
        return time.time() - self.start_time


def extract_queries_from_llm(response: str) -> List[str]:
    """Extract search queries from LLM response."""
    queries = []
    
    # Look for numbered list
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        # Match "1. query" or "1) query" or "- query"
        match = re.match(r'^[\d\.\)\-\*•]+\s*["\']?(.+?)["\']?$', line)
        if match:
            query = match.group(1).strip()
            if len(query) > 5 and len(query) < 150:
                queries.append(query)
    
    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique.append(q)
    
    return unique[:5]


def deep_thinking_research(
    user_request: str,
    llm_invoke: Callable[[str], str]
) -> str:
    """
    Multi-layer thinking research with LLM internal dialogue.
    
    Args:
        user_request: The user's original question
        llm_invoke: Function to call LLM (prompt -> response)
    
    Returns:
        Final answer formulated by LLM
    """
    logger = ThinkingLogger()
    
    print(f"\n{'#'*70}")
    print(f"# JARVIS DEEP THINKING RESEARCH SYSTEM")
    print(f"# User Request: {user_request}")
    print(f"{'#'*70}\n")
    
    # ================================================================
    # LAYER 1: UNDERSTAND - What does user really want?
    # ================================================================
    logger.start_layer("LAYER 1", "UNDERSTAND - מה המשתמש רוצה?")
    
    understand_prompt = f"""[SYSTEM INTERNAL REQUEST - DO NOT RESPOND TO USER]

You are in ANALYSIS MODE. Your task is to understand what the user wants.

USER SAID: "{user_request}"

TASK: In 1-2 sentences, explain what information the user is looking for.
Do NOT answer the question. Just analyze what they want to know.

Format: "The user wants to know: [your analysis]" """

    logger.log("LAYER 1", f"Sending prompt to LLM ({len(understand_prompt)} chars)", "📤")
    
    intent_response = llm_invoke(understand_prompt)
    
    logger.log("LAYER 1", f"LLM Response: {intent_response[:200]}", "📥")
    logger.end_layer("LAYER 1", intent_response)
    
    # ================================================================
    # LAYER 1.5: RESPONSE TYPE - Short or detailed answer?
    # ================================================================
    logger.start_layer("LAYER 1.5", "RESPONSE TYPE - תשובה קצרה או מפורטת?")
    
    response_type_prompt = f"""[SYSTEM INTERNAL REQUEST]

USER SAID: "{user_request}"
USER INTENT: {intent_response}

Analyze: Does the user want a SHORT answer or a DETAILED answer?

INDICATORS FOR SHORT:
- Simple "what is" questions
- Asking for a single fact (price, date, name)
- Quick lookup type questions

INDICATORS FOR DETAILED:
- "explain", "why", "how does"
- Asking for analysis or comparison
- "tell me about", "I want to understand"

RESPOND WITH ONLY ONE WORD: SHORT or DETAILED"""

    logger.log("LAYER 1.5", f"Sending prompt to LLM", "📤")
    
    response_type = llm_invoke(response_type_prompt).strip().upper()
    
    # Default to SHORT if unclear
    if "DETAILED" in response_type:
        response_type = "DETAILED"
    else:
        response_type = "SHORT"
    
    logger.log("LAYER 1.5", f"Response type: {response_type}", "📥")
    logger.end_layer("LAYER 1.5", response_type)
    
    # ================================================================
    # LAYER 2: SUMMARIZE - Create concise search topic
    # ================================================================
    logger.start_layer("LAYER 2", "SUMMARIZE - סכם את הנושא")
    
    summarize_prompt = f"""[SYSTEM INTERNAL REQUEST]

Based on this analysis:
"{intent_response}"

Create a SHORT (3-5 words) search topic.
Just the topic, nothing else.

Example: "Bitcoin current price USD"
Example: "weather Tel Aviv today"

YOUR TOPIC:"""

    logger.log("LAYER 2", f"Sending prompt to LLM ({len(summarize_prompt)} chars)", "📤")
    
    topic = llm_invoke(summarize_prompt).strip()
    
    logger.log("LAYER 2", f"Topic: {topic}", "📥")
    logger.end_layer("LAYER 2", topic)
    
    # ================================================================
    # LAYER 3: QUERIES - Generate 5 diverse search queries
    # ================================================================
    logger.start_layer("LAYER 3", "QUERIES - יצירת 5 שאילתות חיפוש")
    
    queries_prompt = f"""[SYSTEM INTERNAL REQUEST]

=== CURRENT DATE AND TIME ===
Today is: {datetime.now().strftime("%A, %B %d, %Y")}
Current time: {datetime.now().strftime("%H:%M")}
Year: {datetime.now().year}
=================================

The user wants to search the internet for: "{topic}"

Original request: "{user_request}"

IMPORTANT: When the user says "yesterday", "today", "this week", etc., use the CURRENT DATE above!
- "yesterday" = {datetime.now().strftime("%B %d, %Y")} minus 1 day
- "today" = {datetime.now().strftime("%B %d, %Y")}

YOUR TASK: Generate exactly 5 DIFFERENT search queries for web search.
Make them diverse:
- Some specific, some general
- Include the current year ({datetime.now().year}) in at least 2 queries
- Different keywords and angles

FORMAT (one per line, numbered):
1. [first query]
2. [second query]
3. [third query]
4. [fourth query]
5. [fifth query]

YOUR 5 QUERIES:"""

    logger.log("LAYER 3", f"Sending prompt to LLM ({len(queries_prompt)} chars)", "📤")
    
    queries_response = llm_invoke(queries_prompt)
    
    logger.log("LAYER 3", f"Raw response:\n{queries_response}", "📥")
    
    # Extract queries
    queries = extract_queries_from_llm(queries_response)
    
    # Fallback if extraction failed
    if not queries:
        queries = [topic, f"{topic} latest", f"{topic} news"]
        logger.log("LAYER 3", "⚠️ Extraction failed, using fallback queries", "⚠️")
    
    logger.log("LAYER 3", f"Extracted {len(queries)} queries:", "📋")
    for i, q in enumerate(queries, 1):
        logger.log("LAYER 3", f"  {i}. {q}", "🔍")
    
    logger.end_layer("LAYER 3", f"{len(queries)} queries")
    
    # ================================================================
    # LAYER 4: SEARCH - Execute web searches
    # ================================================================
    logger.start_layer("LAYER 4", "SEARCH - חיפוש באינטרנט")
    
    try:
        # Try new package first
        try:
            from ddgs import DDGS
            logger.log("LAYER 4", "Using ddgs package", "📦")
        except ImportError:
            from duckduckgo_search import DDGS
            logger.log("LAYER 4", "Using duckduckgo_search package", "📦")
        
        bad_domains = ['baidu.com', 'weibo.com', 'qq.com', 'yandex.ru', 
                       'current.com', 'pinterest.com']
        
        all_results = []
        seen_urls = set()
        
        for i, query in enumerate(queries, 1):
            search_start = time.time()
            logger.log("LAYER 4", f"Searching query {i}: '{query}'", "🔍")
            
            try:
                results = DDGS().text(query, max_results=3)
                count = 0
                for r in results:
                    url = r.get('href', '')
                    if url not in seen_urls and not any(bad in url for bad in bad_domains):
                        seen_urls.add(url)
                        all_results.append({
                            'url': url,
                            'title': r.get('title', ''),
                            'snippet': r.get('body', ''),
                            'query': query
                        })
                        count += 1
                
                search_time = time.time() - search_start
                logger.log("LAYER 4", f"  → Found {count} new results ({search_time:.2f}s)", "✅")
                
            except Exception as e:
                logger.log("LAYER 4", f"  → Error: {e}", "❌")
        
        logger.log("LAYER 4", f"Total unique results: {len(all_results)}", "📊")
        
        if not all_results:
            logger.end_layer("LAYER 4", "NO RESULTS")
            return "לא הצלחתי למצוא מידע באינטרנט. נסה לנסח את השאלה אחרת."
        
        logger.end_layer("LAYER 4", f"{len(all_results)} results")
        
    except ImportError as e:
        logger.log("LAYER 4", f"Missing package: {e}", "❌")
        return f"חסרה חבילה: {e}"
    
    # ================================================================
    # LAYER 5: SCRAPE - Fetch content from URLs
    # ================================================================
    logger.start_layer("LAYER 5", "SCRAPE - שליפת תוכן מהאתרים")
    
    try:
        import trafilatura
        
        def scrape_url(result):
            try:
                # Use timeout to prevent hanging
                downloaded = trafilatura.fetch_url(result['url'], no_ssl=True)
                if downloaded:
                    text = trafilatura.extract(downloaded, include_comments=False)
                    if text and len(text) > 100:
                        return {**result, 'content': text[:2000]}
            except:
                pass
            return {**result, 'content': result['snippet']}
        
        scraped = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(scrape_url, r) for r in all_results[:5]]
            # Use timeout - catch TimeoutError properly
            try:
                for future in as_completed(futures, timeout=10):
                    try:
                        result = future.result(timeout=3)
                        if result.get('content'):
                            scraped.append(result)
                            logger.log("LAYER 5", f"✅ Scraped: {result['url'][:40]}...", "🕷️")
                    except Exception as e:
                        logger.log("LAYER 5", f"⚠️ Timeout/error on URL", "⏱️")
            except TimeoutError:
                logger.log("LAYER 5", "⏱️ Global timeout - using what we have", "⏱️")
            except Exception as e:
                logger.log("LAYER 5", f"⚠️ Scraping error: {e}", "⚠️")
        
        if not scraped:
            scraped = all_results[:3]
            logger.log("LAYER 5", "⚠️ Using snippets as fallback", "⚠️")
        
        logger.end_layer("LAYER 5", f"{len(scraped)} sources scraped")
        
    except ImportError:
        scraped = all_results[:3]
        logger.log("LAYER 5", "trafilatura not installed, using snippets", "⚠️")
    except Exception as e:
        scraped = all_results[:3] if all_results else []
        logger.log("LAYER 5", f"⚠️ Error: {e}, using snippets", "⚠️")
    
    # ================================================================
    # LAYER 6: FILTER - Ask LLM to identify relevant content
    # ================================================================
    logger.start_layer("LAYER 6", "FILTER - סינון תוכן רלוונטי")
    
    # Build context
    context = ""
    for i, r in enumerate(scraped, 1):
        content = r.get('content', r.get('snippet', ''))[:500]  # Reduced for speed
        context += f"\n[{i}] {r['title'][:50]}\n{content}\n"
    
    filter_prompt = f"""[SYSTEM INTERNAL REQUEST]

The user asked: "{user_request}"
Search topic: "{topic}"

Here are the search results:
{context[:2500]}

TASK: For each source, rate its relevance (HIGH/MEDIUM/LOW/NONE) and explain briefly.
Identify which sources contain information that answers the user's question.

FORMAT:
[SOURCE 1] RELEVANCE: [rating] - [brief reason]
[SOURCE 2] RELEVANCE: [rating] - [brief reason]
...

YOUR ANALYSIS:"""

    logger.log("LAYER 6", f"Sending {len(filter_prompt)} chars to LLM", "📤")
    
    filter_response = llm_invoke(filter_prompt)
    
    logger.log("LAYER 6", f"Filter analysis:\n{filter_response[:300]}...", "📥")
    logger.end_layer("LAYER 6", "Relevance analyzed")
    
    # ================================================================
    # LAYER 7: ANALYZE - Extract key facts
    # ================================================================
    logger.start_layer("LAYER 7", "ANALYZE - חילוץ עובדות מרכזיות")
    
    analyze_prompt = f"""[SYSTEM INTERNAL REQUEST]

User's question: "{user_request}"

Relevance analysis:
{filter_response}

Raw source content:
{context[:2000]}

TASK: Extract useful information from the sources.
- List key facts as bullet points
- Include names, dates, numbers, events
- If sources are news articles, extract the headlines/main points
- NEVER say "no relevant facts" - there is ALWAYS something to extract
- Even partial information is useful

KEY FACTS FROM SOURCES:"""

    logger.log("LAYER 7", f"Sending {len(analyze_prompt)} chars to LLM", "📤")
    
    facts_response = llm_invoke(analyze_prompt)
    
    logger.log("LAYER 7", f"Facts extracted:\n{facts_response[:300]}...", "📥")
    logger.end_layer("LAYER 7", "Facts extracted")
    
    # ================================================================
    # LAYER 8: FORMULATE - Create answer (respecting response type)
    # ================================================================
    logger.start_layer("LAYER 8", "FORMULATE - ניסוח התשובה")
    
    # Detect language
    is_hebrew = any('\u0590' <= c <= '\u05FF' for c in user_request)
    language = "Hebrew (עברית)" if is_hebrew else "English"
    
    if response_type == "SHORT":
        formulate_prompt = f"""[FINAL RESPONSE - THIS GOES TO THE USER]

You are JARVIS. Give a SHORT, DIRECT answer.

USER'S QUESTION: "{user_request}"

FACTS FOUND:
{facts_response}

RULES FOR SHORT ANSWER:
- Maximum 1-2 sentences
- Just answer the question directly
- Example: "The current Bitcoin price is $90,000"
- Do NOT add extra info, disclaimers, or suggestions
- Do NOT tell user to check other sources

RESPOND IN: {language}

YOUR SHORT ANSWER:"""
    else:
        formulate_prompt = f"""[FINAL RESPONSE - THIS GOES TO THE USER]

You are JARVIS. Give a DETAILED, helpful answer.

USER'S QUESTION: "{user_request}"

FACTS FOUND:
{facts_response}

SOURCES:
{chr(10).join([f"- {r['title']}: {r['url']}" for r in scraped[:3]])}

RULES FOR DETAILED ANSWER:
- Explain the findings thoroughly
- Include context and background
- Mention sources
- Start with "Based on my research..." or "לפי המידע שמצאתי..."

RESPOND IN: {language}

YOUR DETAILED ANSWER:"""

    logger.log("LAYER 8", f"Response type: {response_type}", "📋")
    logger.log("LAYER 8", f"Sending prompt ({len(formulate_prompt)} chars)", "📤")
    
    draft_answer = llm_invoke(formulate_prompt)
    
    logger.log("LAYER 8", f"Draft answer ({len(draft_answer)} chars)", "📥")
    logger.end_layer("LAYER 8", "Draft formulated")
    
    # ================================================================
    # LAYER 9: REFINE - Ensure answer matches expected type
    # ================================================================
    logger.start_layer("LAYER 9", "REFINE - בדיקה וליטוש סופי")
    
    # Only refine SHORT answers that are too long
    if response_type == "SHORT" and len(draft_answer) > 200:
        refine_prompt = f"""[SYSTEM INTERNAL REQUEST]

The user asked a SIMPLE question: "{user_request}"

Your draft answer was TOO LONG:
{draft_answer}

TASK: Shorten this to 1-2 sentences MAXIMUM.
Just give the direct answer. No disclaimers. No "check other sources".

REFINED SHORT ANSWER:"""

        logger.log("LAYER 9", f"Answer too long ({len(draft_answer)} chars), refining...", "✂️")
        
        refined_answer = llm_invoke(refine_prompt)
        
        logger.log("LAYER 9", f"Refined to {len(refined_answer)} chars", "✅")
    else:
        refined_answer = draft_answer
        logger.log("LAYER 9", f"No refinement needed", "✅")
    
    logger.end_layer("LAYER 9", "Refinement done")
    
    # ================================================================
    # LAYER 10: FINAL RESPONSE - Natural conversational answer
    # ================================================================
    logger.start_layer("LAYER 10", "FINAL RESPONSE - תשובה סופית טבעית")
    
    final_prompt = f"""[THIS IS YOUR FINAL ANSWER TO THE USER]

User asked: {intent_response}
Research findings: {refined_answer}

YOUR TASK: Report what you found to the user.

CRITICAL RULES:
- NEVER say "I can't provide" or "I don't have access"
- You DID search and you DID find information
- Just tell them what the research found
- If findings are incomplete, share what you have
- Be informative and factual
- Respond in {language}

Your informative answer:"""

    logger.log("LAYER 10", f"Asking: 'What would you answer?'", "💬")
    
    final_answer = llm_invoke(final_prompt)
    
    logger.log("LAYER 10", f"Final answer: {final_answer[:100]}...", "📥")
    logger.end_layer("LAYER 10", "Done")
    
    # ================================================================
    # SUMMARY
    # ================================================================
    total = logger.total_time()
    print(f"\n{'#'*70}")
    print(f"# DEEP THINKING COMPLETE")
    print(f"# Total time: {total:.2f}s")
    print(f"# Layers executed: 10 (including 1.5)")
    print(f"# Response type: {response_type}")
    print(f"# Sources used: {len(scraped)}")
    print(f"{'#'*70}\n")
    
    return final_answer


# ============================================
# TEST
# ============================================
if __name__ == "__main__":
    def mock_llm(prompt):
        """Mock LLM for testing."""
        print(f"\n[MOCK] LLM received {len(prompt)} chars")
        
        if "understand" in prompt.lower() or "analysis mode" in prompt.lower():
            return "The user wants to know: the current market price of Bitcoin in USD"
        elif "short" in prompt.lower() and "topic" in prompt.lower():
            return "Bitcoin price USD"
        elif "5" in prompt and "queries" in prompt.lower():
            return """1. Bitcoin price today
2. BTC USD exchange rate
3. Bitcoin current value
4. cryptocurrency market Bitcoin
5. what is Bitcoin worth right now"""
        elif "relevance" in prompt.lower():
            return "[SOURCE 1] RELEVANCE: HIGH - Contains current Bitcoin price\n[SOURCE 2] RELEVANCE: MEDIUM - General crypto info"
        elif "key facts" in prompt.lower():
            return "• Bitcoin is currently trading at approximately $42,000 USD\n• 24h change: +2.5%"
        else:
            return "Based on my research, Bitcoin is currently trading at around $42,000 USD, with a 24-hour increase of about 2.5%."
    
    result = deep_thinking_research("What is the current Bitcoin price?", mock_llm)
    print("\n=== FINAL RESULT ===")
    print(result)
