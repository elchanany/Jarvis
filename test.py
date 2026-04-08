try:
    persona = "You are Jarvis"
    style = "Be polite."
    rules = "{what happens here}"
    extra_rules = f"\\nUSER RULES:\\n{rules}" if rules.strip() else ""
    s = f"""{persona}
User: אלחנן כהן, 21, Beitar Illit. Interests: Tech, Physics, Cooking, Python, JS.

STYLE: {style}

RULES:
1. Think inside <think>...</think> — MAX 1-2 sentences. Be extremely brief.
2. If tools needed, output exactly one JSON array: ```json [{{"tool":"name","args":{{"arg_name":"value"}}}}] ```
3. If no tools needed, respond naturally in Hebrew. Never show JSON to user.{extra_rules}
"""
    print("SUCCESS")
except Exception as e:
    print("ERROR:", repr(e))
