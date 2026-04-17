"""
Jarvis Local STT Engine — Whisper-HE via OpenVINO
Uses the pre-trained Hebrew Whisper model located at models/whisper-small-he-openvino
100% offline, no internet required.
"""
import os
import io
import time
import base64
import numpy as np
import warnings
warnings.filterwarnings("ignore")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_PATH = os.path.join(PROJECT_DIR, "models", "whisper-small-he-openvino")

_whisper_pipeline = None
_whisper_loaded = False

def _ensure_loaded():
    """Lazy-load the Whisper pipeline on first use."""
    global _whisper_pipeline, _whisper_loaded
    if _whisper_loaded:
        return _whisper_pipeline is not None
    
    _whisper_loaded = True  # Don't retry on failure
    
    if not os.path.exists(WHISPER_PATH):
        print(f"[STT] ❌ Whisper model not found at {WHISPER_PATH}")
        return False
    
    try:
        # Force OpenVINO DLLs into PATH
        try:
            import openvino as ov
            ov_path = os.path.dirname(ov.__file__)
            os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ.get("PATH", "")
        except ImportError:
            pass
        
        import openvino_genai as ov_genai
        
        print("[STT] 🎤 Loading Whisper-HE (OpenVINO)...")
        start = time.time()
        
        # Try NPU first (Intel AI Boost), fallback to CPU
        for device in ["NPU", "CPU"]:
            try:
                _whisper_pipeline = ov_genai.WhisperPipeline(WHISPER_PATH, device=device)
                elapsed = time.time() - start
                print(f"[STT] ✅ Whisper loaded on {device} in {elapsed:.1f}s")
                return True
            except Exception as e:
                print(f"[STT] {device} failed: {str(e)[:60]}")
        
        print("[STT] ❌ All devices failed")
        return False
    except Exception as e:
        print(f"[STT] ❌ Failed to load: {e}")
        return False

def transcribe_audio_b64(audio_b64: str, language: str = "he") -> str:
    """
    Transcribe base64-encoded audio using local Whisper-HE.
    
    Args:
        audio_b64: Base64-encoded audio data (webm, wav, etc.)
        language: Language code ('he' for Hebrew, 'en' for English)
    
    Returns:
        Transcribed text string, or empty string on failure.
    """
    if not _ensure_loaded():
        return ""
    
    try:
        start = time.time()
        audio_bytes = base64.b64decode(audio_b64)
        
        # Convert audio to raw float32 PCM at 16kHz
        audio_array = _decode_audio_to_pcm(audio_bytes)
        
        if audio_array is None or len(audio_array) < 1600:  # Less than 0.1s
            return ""
        
        # Check if audio is silent
        if np.max(np.abs(audio_array)) < 0.01:
            return ""
        
        # Transcribe
        lang_tag = f"<|{language}|>"
        result = _whisper_pipeline.generate(audio_array, language=lang_tag)
        
        # Extract text from result
        text = ""
        if hasattr(result, 'texts') and result.texts:
            text = result.texts[0]
        elif hasattr(result, 'text'):
            text = result.text
        else:
            text = str(result)
        
        elapsed = time.time() - start
        clean = text.strip()
        if clean:
            print(f"[STT] 📝 Transcribed ({elapsed:.1f}s): {clean[:80]}")
        
        return clean
    except Exception as e:
        print(f"[STT] ❌ Transcription error: {e}")
        return ""

def _decode_audio_to_pcm(audio_bytes: bytes) -> np.ndarray:
    """Convert raw audio bytes (webm/ogg/wav) to 16kHz float32 PCM."""
    try:
        # Try soundfile first (handles WAV, FLAC, OGG)
        import soundfile as sf
        audio_buf = io.BytesIO(audio_bytes)
        try:
            audio_array, sr = sf.read(audio_buf, dtype='float32')
            if len(audio_array.shape) > 1:
                audio_array = audio_array.mean(axis=1)
            # Resample to 16kHz if needed
            if sr != 16000:
                audio_array = _resample(audio_array, sr, 16000)
            return audio_array
        except Exception:
            pass
        
        # Try pydub for webm/ogg (MediaRecorder format)
        try:
            from pydub import AudioSegment
            audio_buf = io.BytesIO(audio_bytes)
            audio = AudioSegment.from_file(audio_buf)
            audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            raw = np.frombuffer(audio.raw_data, dtype=np.int16).astype(np.float32) / 32768.0
            return raw
        except Exception:
            pass
        
        # Last resort: try treating as raw PCM
        raw = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return raw
    except Exception as e:
        print(f"[STT] Audio decode error: {e}")
        return None

def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Simple linear interpolation resampling."""
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    new_length = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, new_length)
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
