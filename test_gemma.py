# test_gemma.py
# =============
# Sandbox environment for testing the Gemma 4 multimodal architecture 

import os
import re
from gemma_brain import run_gemma_chat
from tools_registry import ALL_TOOLS
import datetime

# Local mocks
def remember_fact(fact): return f"Saved memory: {fact}"
def recall_memories(): return "Your name is Elchanan (Yehuda) Cohen. Location Beitar Illit."

def execute_parsed_tool(command_dict):
    if not command_dict:
        return None
        
    tool_name = command_dict.get("tool")
    args = command_dict.get("args", {})
    
    if not tool_name:
        return "No tool name provided."
        
    print(f"\n[🔌 SYSTEM] Executing: {tool_name}({args})")
    
    if tool_name == "get_time":
        return datetime.datetime.now().strftime("The current time is %H:%M")
    if tool_name == "remember_fact": return remember_fact(args.get("fact", ""))
    if tool_name == "recall_memories": return recall_memories()
        
    # Find tool map
    for t in ALL_TOOLS:
        if t.name == tool_name:
            try:
                result = t.invoke(args)
                return result
            except Exception as e:
                return f"Error executing {tool_name}: {e}"
                
    return f"Tool {tool_name} not found."

def main():
    print("=" * 60)
    print(" 🧠 GEMMA 4 REASONING ENGINE - STABLE REACT LOOP 🧠 ")
    print("=" * 60)
    print("Type 'exit' to quit.\n")
    
    chat_history = []
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                break
                
            chat_history.append({"role": "user", "content": user_input})
            
            while True:
                result = run_gemma_chat(chat_history)
                
                if "error" in result:
                    print(f"[❌ ERROR] {result['error']}")
                    break
                    
                chat_history.append({"role": "assistant", "content": result["raw"]})
                
                cmds = result.get("commands", [])
                if cmds:
                    tool_results_text = ""
                    for cmd in cmds:
                        exec_result = execute_parsed_tool(cmd)
                        print(f"✅ ACTION RESULT: {exec_result}")
                        tool_results_text += f"Tool '{cmd.get('tool')}' output:\n{exec_result}\n"
                    
                    chat_history.append({
                        "role": "user", 
                        "content": f"[TOOL OBSERVATION]\n{tool_results_text}\nAnswer user gracefully."
                    })
                    print("[🔄 מחזיר למודל להסקת עובדות מתוך הכלים...]")
                else:
                    metrics = result.get("metrics", {})
                    if metrics:
                        print(f"[⏱️ PERFORMANCE] First Token: {metrics.get('ttft', 0):.2f}s | Speed: {metrics.get('tps', 0):.1f} tok/sec")
                        
                    spoken_text = result['response'].strip()
                    if spoken_text:
                        print(f"🗣️ JARVIS SAYS:\n{spoken_text}\n")
                    
                    break
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
