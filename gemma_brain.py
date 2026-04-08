# gemma_brain.py
# ==============
# Dedicated brain architecture for handling Reasoning/Thinking LLMs like Gemma 4

import json
import re
import requests
import sys
from typing import Dict, Any, Tuple, List
from tools_registry import ALL_TOOLS

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

import os
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(PROJECT_DIR, "user_memories.json")

def build_tools_description() -> str:
    """Build a COMPACT tool list - but keep full definitions so LLM knows arguments."""
    desc = []
    for t in ALL_TOOLS:
        # We must keep the full description so the LLM knows available sub-actions (e.g. for computer_action)
        short_desc = t.description.strip().replace('\n', ' ')
        args_str = ""
        if hasattr(t, 'args') and t.args:
            args_str = f" | args: {list(t.args.keys())}"
        desc.append(f"- {t.name}{args_str}: {short_desc}")
    return "\n".join(desc)

def load_memories_snapshot() -> str:
    """Load stored memories from file and return a formatted string for the system prompt."""
    try:
        if not os.path.exists(MEMORY_FILE):
            return ""
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            memories = json.load(f)
        if not memories:
            return ""
        # Only last 15 memories to not bloat the context
        recent = memories[-15:]
        lines = [f"  - {m['fact']} (saved: {m['date']})" for m in recent]
        return "\nSTORED MEMORIES (important facts I know about the user):\n" + "\n".join(lines)
    except Exception:
        return ""

# Configurable prompt settings (modified via UI)
prompt_config = {
    "style": "תענה בעברית, קצר ולעניין. השתמש בכלים שלך כדי למלא בקשות ע\"י פקודות מערכת ואינטרנט.",
    "rules": "- הפעל כלים באופן עצמאי כדי לשרת את המשתמש.\n- אל תתנצל.",
    "persona": "קורים לך Jarvis (ג'ארביס). אתה העוזר האישי הדיגיטלי המושלם שיושב בתוך המחשב של המשתמש. אתה משרת את המשתמש. אתה מדבר בצורה מכבדת וחברית, מתייחס למשתמש כ-'אדוני' ולפעמים כ-'אלחנן'."
}

def generate_system_prompt(vision_mode: str = "vlm") -> str:
    style = prompt_config["style"]
    rules = prompt_config["rules"]
    persona = prompt_config["persona"]
    
    extra_rules = f"\nUSER RULES:\n{rules}" if rules.strip() else ""
    memories_section = load_memories_snapshot()

    
    # Vision mode
    if vision_mode == "vlm":
        vision_text = "VISION: Native VLM mode. You see screenshots directly. Determine coordinates yourself before clicking."
    else:
        vision_text = "VISION: Sub-Agent mode. Use find_element first to get coordinates, then click."

    tools_text = build_tools_description()

    return f"""CRITICAL RULE — READ FIRST:
You MUST NEVER output English reasoning, analysis, or planning text. NEVER write "The user is asking..." or "I should use..." or "Let me check...". Your output is ONLY: a JSON tool call OR a short Hebrew answer. NOTHING ELSE. Violations are UNACCEPTABLE.

IDENTITY: {persona}
USER: אלחנן כהן, 21, ביתר עילית.{memories_section}

STYLE: {style}
{extra_rules}

TOOLS FORMAT:
[{{"narration":"הודעה קצרה","tool":"tool_name","args":{{"key":"val"}}}}]
- "narration" = MANDATORY rich Hebrew sentence explaining what you will do
- "tool" value MUST be a real tool name from the list below. NEVER null, NEVER empty string.
- Output ONLY the JSON array. No text before or after.
- Chain multiple tools: [{{"tool":"a","args":{{}}}},{{"tool":"b","args":{{}}}}]

EXAMPLES:
"מה השעה?" → [{{"narration":"אני בודק את השעה כעת, אדוני.","tool":"get_time","args":{{}}}}]
"תפתח ספוטיפיי" → [{{"narration":"מיד, אדוני. אני פותח את Spotify עבורך.","tool":"launch_app","args":{{"app_name":"spotify"}}}}]
"תנגן Ticket to Ride" → [{{"narration":"בחירה מצוינת, אדוני. אני מנגן את השיר כעת.","tool":"play_song","args":{{"song_name":"Ticket to Ride"}}}}]
"מה מחיר הביטקוין?" → [{{"narration":"אדוני, אני מבצע חיפוש מעמיק באינטרנט כדי להביא לך את מחיר הביטקוין העדכני.","tool":"deep_research","args":{{"query":"bitcoin price USD"}}}}]

TOOL SELECTION RULES:
- Prices / exchange rates / crypto → ALWAYS use deep_research (more accurate, real-time APIs)
- General web questions / news / facts → use search_web
- Telegram news → use read_telegram_news

FORBIDDEN PATTERNS (NEVER output these):
✗ {{"tool": null}} — tool value MUST be a real tool name
✗ "The user is asking..." / "I should use..." / "Let me check..."
✗ English analysis paragraphs
✗ "Self-Correction" / "Response Plan" / numbered steps

RULES:
1. Tool needed? Output JSON ONLY. No text around it.
2. NARRATION IS MANDATORY: Before EVERY tool call, you MUST include a "narration" field in the JSON with a rich, unique, and polite Hebrew sentence explaining what you are about to do. Always address the user respectfully as "אדוני". Do not use repeating, boring templates!
3. No tool needed? Respond in Hebrew ONLY. Short (2-3 sentences).
4. NEVER ask confirmation. Full autonomy.
5. You are Jarvis. NOT Google/OpenAI AI. You CAN control the computer.
6. User shares personal info → call remember_fact.
7. User sends an IMAGE → describe what you see, answer IN HEBREW directly. Do NOT call any tool.
8. Don't know something → call recall_memories or search_web.
9. After tool result arrives, give SHORT Hebrew status. Don't repeat raw output.

{vision_text}

Available Tools:
{tools_text}
"""

def parse_gemma_response(text: str) -> Tuple[str, List[Dict[str, Any]], str]:
    """
    Safely dissects output into: reasoning, JSON commands, and conversational response.
    """
    thinking = ""
    tool_commands = []
    conversation = text

    # Extract Thinking
    think_match = re.search(r'<think>(.*?)</think>', text, re.DOTALL | re.IGNORECASE)
    if think_match:
        thinking = think_match.group(1).strip()
        conversation = text.replace(think_match.group(0), "").strip()

    # Extract JSON Command Array - try multiple patterns (with or without markdown fences)
    json_match = re.search(r'```json\s*(\[.*?\]|\{.*?\})\s*```', conversation, re.DOTALL | re.IGNORECASE)
    if not json_match:
        json_match = re.search(r'```\n*(\[.*?\]|\{.*?\})\n*```', conversation, re.DOTALL | re.IGNORECASE)
    if not json_match:
        # Try raw JSON array at start of content (no fences) - our preferred format
        json_match = re.search(r'^\s*(\[\s*\{.*?\}\s*\])', conversation, re.DOTALL)
    if not json_match:
        # Try raw JSON object at start (single tool call without array wrapper)
        json_match = re.search(r'^\s*(\{\s*"tool".*?\})', conversation, re.DOTALL)

    if json_match:
        raw_json = json_match.group(1)
        # Fix common model mistake: {"tool":"name":{}} → {"tool":"name","args":{}}
        # Pattern: "tool_name_value":{  where :{  is not preceded by ","
        raw_json = re.sub(
            r'("tool"\s*:\s*"[^"]+"\s*)(:\s*\{)',
            r'\1,"args":{',
            raw_json
        )
        # Also fix: [{"tool":"foo":{"a":1}}] → [{"tool":"foo","args":{"a":1}}]
        raw_json = re.sub(
            r'(":\s*"[^"]+")(\s*:\s*\{)',
            lambda m: m.group(1) + ',"args":{' if '"tool"' in raw_json[:raw_json.find(m.group(0))+10] else m.group(0),
            raw_json
        )
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, dict):
                tool_commands = [parsed]
            elif isinstance(parsed, list):
                tool_commands = parsed
            conversation = conversation.replace(json_match.group(0), "").strip()
        except json.JSONDecodeError:
            pass
            
    # Purge any leaked think tags
    conversation = re.sub(r'</?think>', '', conversation, flags=re.IGNORECASE).strip()
    return thinking, tool_commands, conversation


def run_gemma_chat_stream(messages: List[Dict[str, str]], model: str = "gemma4:e4b", vision_mode: str = "vlm"):
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": generate_system_prompt(vision_mode)})
        
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.2,
            "num_ctx": 4096,       # Lowered from 8192 for MUCH faster TTFT
            "num_predict": 1024,   # Lowered from 2048 to save memory
        },
        "keep_alive": "30m"
    }
    
    try:
        # connect timeout=10s, read timeout=300s (model loading can take 60s+)
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=(10, 300))
        yield {"type": "status", "content": "connected"}
        if response.status_code == 200:
            full_text = ""
            content_buf = ""
            in_think = False
            think_via_channel = False  # True if thinking came via dedicated "thinking" field
            sent_think_end = False
            
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    try:
                        chunk = json.loads(decoded)
                        msg = chunk.get("message", {})
                        
                        think_tok = msg.get("thinking", "")
                        content_tok = msg.get("content", "")
                        
                        # === Dedicated thinking channel ===
                        if think_tok:
                            if not in_think:
                                full_text += "<think>"
                                in_think = True
                                think_via_channel = True
                            full_text += think_tok
                            yield {"type": "thinking", "content": think_tok}
                        
                        # === Content channel ===
                        if content_tok:
                            # KEY FIX: If thinking came via dedicated channel,
                            # the first content token means thinking is DONE.
                            if think_via_channel and in_think:
                                full_text += "</think>"
                                in_think = False
                                think_via_channel = False
                                sent_think_end = True
                                yield {"type": "think_end"}
                                
                            full_text += content_tok
                            
                            # Otherwise, handle <think> tags in content channel
                            content_buf += content_tok
                            
                            while content_buf:
                                if not in_think:
                                    idx = content_buf.find("<think>")
                                    if idx >= 0:
                                        before = content_buf[:idx]
                                        if before.strip():
                                            yield {"type": "content", "content": before}
                                        content_buf = content_buf[idx + 7:]
                                        in_think = True
                                        continue
                                    
                                    if len(content_buf) > 7 and "<" in content_buf[-7:]:
                                        safe = content_buf[:-7]
                                        content_buf = content_buf[-7:]
                                        if safe:
                                            yield {"type": "content", "content": safe}
                                        break
                                    
                                    # Detect if full buffer starts with a "Thinking Process:" block
                                    # We will strip the Thinking Process: block safely
                                    if 'Thinking Process:' in content_buf and '\n\n' in content_buf:
                                        content_buf = re.sub(r'Thinking Process:.*?\n\n', '', content_buf, flags=re.DOTALL | re.IGNORECASE)
                                        # Strip numbered steps that are common in deepseek outputs
                                        content_buf = re.sub(r'(?:^\d+\.\s+\*\*.*?\*\*[^\n]*\n)+', '', content_buf, flags=re.MULTILINE)
                                        
                                    if content_buf:
                                        yield {"type": "content", "content": content_buf}
                                        
                                    content_buf = ""
                                    break
                                
                                else:
                                    idx = content_buf.find("</think>")
                                    if idx < 0:
                                        idx = content_buf.find("\n\n1.") # Fallback for Deepseek if it outputs a numbered list
                                        
                                    if idx >= 0:
                                        before = content_buf[:idx]
                                        if before.strip():
                                            yield {"type": "thinking", "content": before}
                                        
                                        content_buf = content_buf[idx + 8:]
                                        in_think = False
                                        sent_think_end = True
                                        yield {"type": "think_end"}
                                        continue
                                    
                                    if len(content_buf) > 8 and "<" in content_buf[-8:]:
                                        safe = content_buf[:-8]
                                        content_buf = content_buf[-8:]
                                        if safe:
                                            yield {"type": "thinking", "content": safe}
                                        break
                                    
                                    yield {"type": "thinking", "content": content_buf}
                                    content_buf = ""
                                    break
                            
                        if chunk.get("done"):
                            if content_buf.strip():
                                if in_think:
                                    yield {"type": "thinking", "content": content_buf}
                                else:
                                    yield {"type": "content", "content": content_buf}
                                content_buf = ""
                            
                            if in_think and not sent_think_end:
                                yield {"type": "think_end"}
                            
                            eval_count = chunk.get("eval_count", 0)
                            eval_duration = chunk.get("eval_duration", 0) / 1e9
                            tps = eval_count / eval_duration if eval_duration > 0 else 0
                            
                            think, json_cmds, conv = parse_gemma_response(full_text)
                            yield {
                                "type": "done",
                                "raw": full_text,
                                "commands": json_cmds,
                                "metrics": {"tps": tps}
                            }
                    except json.JSONDecodeError:
                        continue
        else:
            yield {"type": "error", "content": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        yield {"type": "error", "content": str(e)}

def run_gemma_chat(messages: List[Dict[str, str]], model: str = "gemma4:e4b") -> Dict[str, Any]:
    # Keeping the old function for terminal compatibility, just wrapping the generator
    full_text = ""
    json_cmds = []
    metrics = {}
    
    print("\n[🧠 ג'ארביס חושב...]\n")
    for chunk in run_gemma_chat_stream(messages, model):
        if chunk["type"] == "thinking":
            sys.stdout.write(chunk["content"])
            sys.stdout.flush()
        elif chunk["type"] == "think_end":
            sys.stdout.write("\n</think>\n")
        elif chunk["type"] == "content":
            sys.stdout.write(chunk["content"])
            sys.stdout.flush()
        elif chunk["type"] == "done":
            print("\n")
            think, json_cmds, conv = parse_gemma_response(chunk["raw"])
            return {
                "raw": chunk["raw"],
                "thinking": think,
                "commands": chunk["commands"],
                "response": conv,
                "metrics": chunk["metrics"]
            }
        elif chunk["type"] == "error":
            return {"error": chunk["content"]}
            
    return {"error": "Stream ended unexpectedly"}
