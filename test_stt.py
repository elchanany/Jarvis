"""
🎤 Local STT Test - OpenVINO Whisper (No Downloads!)
Tests speech recognition with detailed timing logs
Shows which device (NPU/CPU/GPU) is used
"""
import os
import sys
import time

# Force OpenVINO DLLs into PATH
try:
    import openvino as ov
    ov_path = os.path.dirname(ov.__file__)
    os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ["PATH"]
except:
    pass

import numpy as np
import speech_recognition as sr

# === PATHS ===
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Priority: Hebrew model (Stateful) > AI Playground
WHISPER_PATHS = [
    os.path.join(PROJECT_DIR, "models", "whisper-small-he-openvino"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\AI Playground\resources\models\STT\OpenVINO---whisper-base-int8-ov"),
]

def find_whisper_model():
    for path in WHISPER_PATHS:
        if os.path.exists(path):
            return path
    return None

def main():
    print("=" * 70)
    print("  🎤 LOCAL STT TEST - OpenVINO Whisper")
    print("  ✅ No additional downloads needed!")
    print("=" * 70)
    
    # Find model
    model_path = find_whisper_model()
    if not model_path:
        print("❌ Whisper model not found!")
        print("   Searched in:")
        for p in WHISPER_PATHS:
            print(f"   - {p}")
        return
    
    print(f"\n📁 Model: {os.path.basename(model_path)}")
    print(f"   Path: {model_path}")
    
    # Load Whisper with OpenVINO
    print("\n⏳ Loading Whisper pipeline...")
    
    try:
        import openvino_genai as ov_genai
    except ImportError:
        print("❌ openvino_genai not installed!")
        print("   Install with: pip install openvino-genai")
        return
    
    whisper_pipeline = None
    device_used = None
    
    # Try devices in order: NPU (fastest for int8), CPU (most compatible)
    for device in ["NPU", "CPU"]:
        try:
            start = time.time()
            whisper_pipeline = ov_genai.WhisperPipeline(model_path, device=device)
            load_time = time.time() - start
            device_used = device
            print(f"   ✅ Loaded on {device} in {load_time:.2f}s")
            break
        except Exception as e:
            print(f"   ⚠️ {device} failed: {str(e)[:50]}...")
    
    if whisper_pipeline is None:
        print("❌ Could not load Whisper on any device!")
        return
    
    # Device info
    print(f"\n📊 Device Information:")
    print(f"   - Active device: {device_used}")
    if device_used == "NPU":
        print(f"   - NPU = Neural Processing Unit (Intel AI Boost)")
        print(f"   - Best for: INT8 models, speech recognition")
        print(f"   - Expected latency: 0.3-0.8s per phrase")
    elif device_used == "CPU":
        print(f"   - CPU = Central Processing Unit")
        print(f"   - Slower than NPU for INT8 models")
        print(f"   - Expected latency: 0.8-2.0s per phrase")
    
    # === LANGUAGE MODE: Hebrew + English only ===
    print("\n🌐 Language mode: Hebrew + English only")
    print("   Will filter out results in other languages (Greek, Korean, etc.)")
    
    # Get generation config (auto-detect, but we'll filter results)
    config = whisper_pipeline.get_generation_config()
    
    # 🔧 FIX for "beam_idx not found" error
    # Force greedy decoding (no beam search)
    config.num_beams = 1
    config.max_new_tokens = 448  # Default limit
    print("   🔧 Configured greedy decoding (num_beams=1)")
    
    def is_hebrew_or_english(text):
        """Check if text contains only Hebrew or English characters."""
        for char in text:
            # Skip spaces and punctuation
            if char.isspace() or char in ".,!?'-\":;()[]{}":
                continue
            # Check if Hebrew (Unicode range)
            if '\u0590' <= char <= '\u05FF':
                continue
            # Check if English (ASCII letters)
            if 'a' <= char.lower() <= 'z':
                continue
            # Check if digit
            if char.isdigit():
                continue
            # Found non-Hebrew, non-English character
            return False
        return True
    
    print("\n" + "-" * 70)
    print("  🎤 READY FOR SPEECH RECOGNITION")
    print("  Speak now - I'll show timing for each step!")
    print("-" * 70 + "\n")
    
    recognizer = sr.Recognizer()
    
    with sr.Microphone(sample_rate=16000) as source:
        print("🔧 Calibrating for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ Ready! Start speaking...\n")
        
        request_count = 0
        total_listen_time = 0
        total_process_time = 0
        
        while True:
            print("🎤 Listening...")
            listen_start = time.time()
            
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
                listen_time = time.time() - listen_start
                total_listen_time += listen_time
                
                print(f"   ⏱️ Listening took: {listen_time:.2f}s")
                print("⏳ Processing with Whisper...")
                
                # Convert to format Whisper expects
                process_start = time.time()
                
                # Get raw audio data
                audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                audio_float = audio_data.astype(np.float32) / 32768.0  # Normalize to [-1, 1]
                
                # Run Whisper with language config
                transcribe_start = time.time()
                result = whisper_pipeline.generate(audio_float, config)
                transcribe_time = time.time() - transcribe_start
                
                process_time = time.time() - process_start
                total_process_time += process_time
                request_count += 1
                
                # Show result
                text = str(result).strip() if result else ""
                
                # Filter: skip if not Hebrew or English
                if text and not is_hebrew_or_english(text):
                    print(f"\n   ⚠️ Detected non-Hebrew/English: '{text[:30]}...'")
                    print("   🔄 Ignoring, speak again...\n")
                    continue
                
                print(f"\n{'=' * 50}")
                print(f"   📝 Result: {text}")
                print(f"   ⏱️ Listening:    {listen_time:.2f}s")
                print(f"   ⏱️ Transcribing: {transcribe_time:.2f}s")
                print(f"   ⏱️ Total:        {listen_time + process_time:.2f}s")
                print(f"   🖥️ Device:       {device_used}")
                print(f"{'=' * 50}\n")
                
            except sr.WaitTimeoutError:
                print("⏱️ No speech detected, listening again...\n")
            except KeyboardInterrupt:
                print("\n\n" + "=" * 50)
                print("  📊 SESSION STATISTICS")
                print("=" * 50)
                if request_count > 0:
                    print(f"   Total requests:     {request_count}")
                    print(f"   Avg listen time:    {total_listen_time/request_count:.2f}s")
                    print(f"   Avg transcribe time: {total_process_time/request_count:.2f}s")
                    print(f"   Device used:        {device_used}")
                print("\n👋 להתראות!")
                break
            except Exception as e:
                print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    main()
