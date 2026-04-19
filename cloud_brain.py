import os
import json
import re
from typing import List, Dict, Any, Generator, Tuple
from anthropic import Anthropic

def run_cloud_chat_stream(messages: List[Dict[str, Any]], model: str = "claude-3-5-sonnet-20241022", vision_mode: str = "vlm") -> Generator[Dict[str, Any], None, None]:
    """
    Identical generator interface to run_gemma_chat_stream, but uses Anthropic.
    Yields chunks with 'type': 'thinking', 'content', 'error', 'done'
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield {"type": "error", "content": "Anthropic API Key is missing. Please add it in Settings."}
        return

    client = Anthropic(api_key=api_key)
    
    # We load the exact same prompt configuration from gemma_brain
    from gemma_brain import generate_system_prompt
    system_prompt = generate_system_prompt(vision_mode=vision_mode)

    # Convert generic message format to Anthropic format
    anthropic_msgs = []
    for m in messages:
        if m["role"] == "system":
            # Anthropic handles system differently, but we'll inject if needed
            continue
            
        content = []
        if isinstance(m.get("content"), str):
            content.append({
                "type": "text",
                "text": m["content"]
            })
            
        # Add visual inputs if present
        if "images" in m and isinstance(m["images"], list):
            for img_b64 in m["images"]:
                # Default to png or guess
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64
                    }
                })
                
        anthropic_msgs.append({"role": m["role"], "content": content})

    try:
        # Stream response
        with client.messages.stream(
            max_tokens=4000,
            system=system_prompt,
            messages=anthropic_msgs,
            model=model,
            temperature=0.1
        ) as stream:
            full_text = ""
            for text in stream.text_stream:
                full_text += text
                yield {"type": "content", "content": text}
                
            # Send done chunk
            think, json_cmds, conv = parse_cloud_response(full_text)
            
            # Extract anthropic token usage
            final_message = stream.get_final_message()
            in_toks = getattr(final_message.usage, "input_tokens", 0) if hasattr(final_message, "usage") else 0
            out_toks = getattr(final_message.usage, "output_tokens", 0) if hasattr(final_message, "usage") else 0
            
            yield {
                "type": "done",
                "raw": full_text,
                "commands": json_cmds,
                "metrics": {
                    "tps": 0,
                    "provider": "anthropic",
                    "model": model,
                    "input_tokens": in_toks,
                    "output_tokens": out_toks
                }
            }

    except Exception as e:
        yield {"type": "error", "content": f"Cloud API Error: {str(e)}"}

def parse_cloud_response(text: str) -> Tuple[str, List[Dict[str, Any]], str]:
    from gemma_brain import parse_gemma_response
    # We use the exact same parser to ensure compatibility
    return parse_gemma_response(text)
