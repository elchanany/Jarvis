# 📋 Project Requirements - Jarvis Offline Voice Assistant

## Core Principles

### 1. 🔒 Offline First (MANDATORY)
- **ALL processing must run locally** - no internet dependency
- Privacy: Voice data never leaves the device
- Speed: No network latency
- Reliability: Works without WiFi/internet connection

### 2. ⚡ Hardware Optimization
- **Primary Target: NPU** (Intel AI Boost)
  - Best power efficiency
  - Similar to Galaxy Buds wake word processing
  - Ideal for always-listening scenarios
- **Secondary: GPU** (Intel Arc Graphics)
- **Fallback: CPU** (only if necessary)

### 3. 🌍 Multilingual Support
- **Hebrew (עברית)** - Primary language
- **English** - Secondary language
- **Auto-detection** - System should detect language automatically

---

## Feature Requirements

### Wake Word Detection
| Word | Language |
|------|----------|
| "Jarvis" | English |
| "Gemini" | English |
| "Hey Jarvis" | English |
| "Hey Gemini" | English |
| "ג'ארביס" | Hebrew |
| "ג'מיני" | Hebrew |
| "היי ג'ארביס" | Hebrew |
| "היי ג'מיני" | Hebrew |

### System Commands
- [ ] Stop/Pause music
- [ ] Volume control (up/down/mute)
- [ ] Open applications
- [ ] Basic system controls

### AI Conversation
- Complex queries → Handover to Gemini AI
- Natural conversation flow
- Context awareness

---

## Technical Requirements

### Speech-to-Text (STT)
- Must run on NPU (preferred) or GPU
- Must support Hebrew + English
- Must work offline
- Latency target: < 500ms for wake word response

### End Goal
- Packaged application for distribution
- Easy installation for end users
- Minimal dependencies

---

## Current Status

### ✅ Completed
- Project structure created
- Virtual environment with dependencies
- Whisper Small (multilingual) model exported to OpenVINO format
- Basic main.py architecture

### ❌ Blocked
- `optimum.intel.openvino` throws `IndexError: tuple index out of range` during `ov_model.generate()`
- Issue persists even on CPU mode
- Compatibility issue between library and export format

### 🔄 Alternatives to Explore
1. **Intel AI Playground STT** - Already working on NPU!
2. **faster-whisper** - CTranslate2 backend, efficient
3. **whisper.cpp** - Native C++ implementation
4. **Direct OpenVINO API** - Skip optimum.intel wrapper

---

*Last Updated: January 5, 2026*
