import json
import os

def create_dataset():
    questions = []
    
    # 1. System Ops (Complex)
    system_ops = [
        ("I'm heading out for the day, could you please secure the computer for me?", "system_status", {"action": "lock"}),
        ("It's getting late, just shut everything down and turn off the pc.", "system_status", {"action": "shutdown"}),
        ("Hey Jarvis, my brother is entering the room, lock the screen immediately!", "system_status", {"action": "lock"}),
        ("I think we are done here, you can power off the machine now.", "system_status", {"action": "shutdown"}),
    ]
    
    # 2. Volume & Brightness (Implicit & Conversational)
    hardware_ops = [
        ("My eyes are hurting a bit from the glare, can you lower the screen brightness?", "control_brightness", {"action": "down"}),
        ("It's too dark to read this article, pump up the brightness please.", "control_brightness", {"action": "up"}),
        ("I can barely hear what they're saying in this video, increase the volume of the speakers.", "control_volume", {"action": "up"}),
        ("Someone is calling my phone right now, mute the audio!", "control_volume", {"action": "mute"}),
        ("The music is deafening, turn the sound down a notch.", "control_volume", {"action": "down"}),
    ]
    
    # 3. Media & Spotify (Contextual)
    media_ops = [
        ("I don't really like this track, please skip to the next one.", "control_media", {"action": "next"}),
        ("Wait, I missed that part, go back to the previous song.", "control_media", {"action": "previous"}),
        ("Could you put on that new song by Billie Eilish on Spotify for me?", "spotify_play", {"track_name": "Billie Eilish"}),
        ("I want to listen to some relaxing Jazz, open Spotify and play it.", "spotify_play", {"track_name": "relaxing Jazz"}),
        ("Stop playing the music, I need to focus on my work.", "stop_media", {}),
        ("Pause the playback for a moment.", "stop_media", {}),
    ]
    
    # 4. Telegram Messaging (Multiple Arguments constraint)
    telegram_ops = [
        ("Send a message to John on Telegram saying that I will be 10 minutes late to the meeting.", "telegram_send", {"contact_name": "John", "message": "I will be 10 minutes late to the meeting"}),
        ("Can you text Mom on Telegram and tell her happy birthday?", "telegram_send", {"contact_name": "Mom", "message": "happy birthday"}),
        ("Check if there are any new messages from David on Telegram.", "telegram_read", {"contact_name": "David"}),
        ("Read the latest Telegram text from Sarah.", "telegram_read", {"contact_name": "Sarah"}),
        ("Jarvis, message Boss on Telegram: I have finished the weekly report.", "telegram_send", {"contact_name": "Boss", "message": "I have finished the weekly report"}),
    ]
    
    # 5. Apps / URL
    app_ops = [
        ("I need to do some math right now, open the calculator app.", "launch_app", {"app_name": "calculator"}),
        ("Could you please fire up Chrome so I can browse the web?", "launch_app", {"app_name": "chrome"}),
        ("Open notepad, I need to write down some quick thoughts.", "launch_app", {"app_name": "notepad"}),
        ("Navigate to github.com on the browser.", "open_url", {"url": "https://github.com"}),
        ("I want to check my feed, open the url https://twitter.com for me.", "open_url", {"url": "https://twitter.com"}),
        ("Play a youtube video about how to cook carbonara.", "youtube_play", {"topic": "how to cook carbonara"}),
    ]

    # 6. Smart Research (Abstract Questions)
    research_ops = [
        ("Can you look up the current weather conditions locally in New York City?", "smart_research", {}),
        ("I need to know what the latest stock price of Apple is today.", "smart_research", {}),
        ("Who is the current CEO of Microsoft right now?", "smart_research", {}),
        ("Do a quick search on the internet to find out who won the world cup in 2022.", "smart_research", {}),
        ("What are the main headlines on the news this morning?", "smart_research", {}),
    ]

    # 7. Memory Operations (Crucial intent recognition)
    memory_ops = [
        ("Please remember the fact that my favorite color is dark blue.", "remember_fact", {"fact": "favorite color is dark blue"}),
        ("Store this in your memory: the wifi password is 'Guest2024'.", "remember_fact", {"fact": "wifi password is Guest2024"}),
        ("You know what, forget what I told you earlier about my favorite color.", "forget_fact", {"fact_to_forget": "favorite color"}),
        ("Erase the memory regarding the wifi password from your database.", "forget_fact", {"fact_to_forget": "wifi password"}),
        ("Based on our past conversations, what do you know about me?", "recall_memories", {}),
    ]
    
    # 8. Time / Date / Chatter
    chat_ops = [
        ("Hey man, do you happen to know what time it is right now?", "get_time", {}),
        ("Could you tell me today's exact date?", "get_date", {}),
        ("How are you feeling today?", "none", {}),
        ("You are truly an amazing AI assistant.", "none", {}),
        ("Is it safe to drink ocean water?", "smart_research", {}),
        ("Can you tell me a short joke about a programmer?", "none", {}),
        ("Please just say hello.", "none", {}),
    ]

    all_scenarios = (
        system_ops * 2 + hardware_ops * 2 + media_ops * 2 + 
        telegram_ops * 2 + app_ops * 2 + research_ops * 2 + 
        memory_ops * 2 + chat_ops * 2
    )
    
    # We mix them to make it 100 benchmark items evenly
    # Total so far: ~80 items if we double them. Let's pad dynamically.
    
    base_list = system_ops + hardware_ops + media_ops + telegram_ops + app_ops + research_ops + memory_ops + chat_ops
    import random
    random.seed(42) # Deterministic shuffle for benchmarking
    
    # Duplicate base list to exceed 100
    expanded_list = base_list * 3
    random.shuffle(expanded_list)
    
    # Crop exactly 100
    final_100 = expanded_list[:100]

    for q, expected_tool, expected_params in final_100:
        questions.append({
            "text": q,
            "expected_tool": expected_tool,
            "difficulty": "hard", # These are all conversational now
            "expected_params": expected_params
        })
        
    with open("benchmark_dataset.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(questions)} COMPLEX test questions into benchmark_dataset.json (ADVANCED ENGLISH)")

if __name__ == "__main__":
    create_dataset()
