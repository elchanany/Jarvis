"""
Kokoro Voice Explorer - Test all available voices
Run this script to hear all voices and choose your favorite
"""
import os
from kokoro_onnx import Kokoro
import sounddevice as sd
import numpy as np
import time

MODEL_PATH = "models/kokoro-intel/kokoro-v0_19.onnx"
VOICES_PATH = "models/kokoro-intel/voices-v1.0.bin"

def main():
    print("🎤 Loading Kokoro TTS Engine...")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    
    voices = kokoro.get_voices()
    
    # Categorize voices
    male_am = sorted([v for v in voices if v.startswith("am_")])
    male_bm = sorted([v for v in voices if v.startswith("bm_")])
    female_af = sorted([v for v in voices if v.startswith("af_")])
    female_bf = sorted([v for v in voices if v.startswith("bf_")])
    
    print(f"\n📋 Available Voices ({len(voices)} total):\n")
    
    print("🧔 American Male (am_):")
    for v in male_am:
        print(f"   • {v}")
    
    print("\n🧔 British Male (bm_):")
    for v in male_bm:
        print(f"   • {v}")
    
    print("\n👩 American Female (af_):")
    for v in female_af:
        print(f"   • {v}")
    
    print("\n👩 British Female (bf_):")
    for v in female_bf:
        print(f"   • {v}")
    
    print("\n" + "="*60)
    print("🎧 VOICE TESTER")
    print("="*60)
    print("\nOptions:")
    print("  • Type a voice name (e.g. 'bm_daniel') to hear it")
    print("  • Type 'all' to hear all male voices")
    print("  • Type 'exit' to quit")
    print()
    
    default_text = "Hello, I am Jarvis, your personal AI assistant. How can I help you today?"
    
    while True:
        choice = input("🎤 Enter voice name (or 'all'/'exit'): ").strip().lower()
        
        if choice == 'exit':
            break
        
        if choice == 'all':
            # Play all male voices
            text = input("📝 Enter test sentence (or press Enter for default): ").strip()
            if not text:
                text = default_text
            
            all_male = male_am + male_bm
            print(f"\n🔊 Playing {len(all_male)} male voices...\n")
            
            for i, voice in enumerate(all_male):
                print(f"   [{i+1}/{len(all_male)}] {voice}...", end=" ", flush=True)
                audio, sr = kokoro.create(text, voice=voice, speed=1.1)
                
                padding = np.zeros(int(sr * 0.2), dtype=audio.dtype)
                audio_padded = np.concatenate([padding, audio, padding])
                
                sd.play(audio_padded, samplerate=sr)
                sd.wait()
                print("✓")
            
            print("\n✅ Done playing all voices!")
            continue
        
        if choice in voices:
            text = input("📝 Enter test sentence (or press Enter for default): ").strip()
            if not text:
                text = default_text
            
            print(f"   🔊 Playing {choice}...")
            audio, sr = kokoro.create(text, voice=choice, speed=1.1)
            
            padding = np.zeros(int(sr * 0.3), dtype=audio.dtype)
            audio_padded = np.concatenate([padding, audio, padding])
            
            sd.play(audio_padded, samplerate=sr)
            sd.wait()
            print("   ✓ Done")
        else:
            print(f"   ❌ Voice '{choice}' not found")
    
    print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
