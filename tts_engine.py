"""
Jarvis TTS Engine — Kokoro (English only) + pyttsx3 fallback
Uses the pre-trained Kokoro model at models/kokoro-intel/
"""
import os
import io
import base64
import warnings
warnings.filterwarnings("ignore")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
KOKORO_MODEL_PATH = os.path.join(PROJECT_DIR, "models", "kokoro-intel", "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(PROJECT_DIR, "models", "kokoro-intel", "voices-v1.0.bin")

_kokoro_engine = None
_kokoro_loaded = False

def _ensure_kokoro():
    """Lazy-load Kokoro on first use."""
    global _kokoro_engine, _kokoro_loaded
    if _kokoro_loaded:
        return _kokoro_engine is not None
    
    _kokoro_loaded = True
    
    if not os.path.exists(KOKORO_MODEL_PATH):
        print(f"[TTS] ⚠️ Kokoro model not found at {KOKORO_MODEL_PATH}")
        return False
    
    try:
        from kokoro_onnx import Kokoro
        import time
        
        print("[TTS] 🔊 Loading Kokoro TTS...")
        start = time.time()
        _kokoro_engine = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        elapsed = time.time() - start
        print(f"[TTS] ✅ Kokoro loaded in {elapsed:.1f}s")
        
        # Warmup
        _kokoro_engine.create("Hello", voice="bm_daniel", speed=1.0)
        print("[TTS] ✅ Warmup complete")
        return True
    except Exception as e:
        print(f"[TTS] ❌ Kokoro failed: {e}")
        return False

def generate_speech_b64(text, engine_type="kokoro"):
    """
    Generate speech from text. Returns base64-encoded WAV audio.
    
    engine_type:
      - 'kokoro': Kokoro TTS (English only, high quality)
      - 'system': Windows built-in TTS (any language, robotic)
      - 'none': No TTS
    """
    if not text.strip() or engine_type == "none":
        return None

    try:
        if engine_type == "kokoro":
            if not _ensure_kokoro():
                print("[TTS] Kokoro unavailable, falling back to system")
                return _generate_system_tts(text)
            
            import numpy as np
            import soundfile as sf
            
            # Kokoro works best with English. Use 'bm_daniel' (British male)
            samples, sample_rate = _kokoro_engine.create(
                text, voice="bm_daniel", speed=1.1, lang="en-gb"
            )
            
            if samples is None or len(samples) == 0:
                return None
            
            buffer = io.BytesIO()
            sf.write(buffer, samples, sample_rate, format='WAV')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        elif engine_type == "system":
            return _generate_system_tts(text)
        
        else:
            return None

    except Exception as e:
        print(f"[TTS Error] {e}")
        return None

def _generate_system_tts(text):
    """Use Windows built-in System.Speech for any language (including Hebrew)."""
    try:
        import subprocess
        import tempfile
        
        # Use a temp file for the WAV output
        tmp = os.path.join(tempfile.gettempdir(), "jarvis_tts_tmp.wav")
        
        # PowerShell command to generate speech via System.Speech
        ps_script = f'''
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile("{tmp}")
$synth.Speak("{text.replace('"', "'")}")
$synth.Dispose()
'''
        subprocess.run(["powershell", "-Command", ps_script], 
                       capture_output=True, timeout=30)
        
        if os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
            with open(tmp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            os.remove(tmp)
            return b64
    except Exception as e:
        print(f"[TTS System] Error: {e}")
    return None
