# 🖥️ System Capabilities - Jarvis Project

## Hardware Specifications

### Device
- **Model:** Lenovo IdeaPad Slim 5 16IMH9

### Processor (CPU)
- **Model:** Intel Core Ultra 7 155H
- **Cores:** 16 cores
- **Threads:** 22 threads
- **Cache:** 24 MB
- **NPU:** ✅ Available (Intel AI Boost NPU)

### Memory (RAM)
- **Capacity:** 32 GB
- **Type:** LPDDR5
- **Speed:** 7467 MT/s

### Graphics (GPU)
- **Model:** Intel Arc Graphics (Integrated)
- **Shared VRAM:** 18 GB
- **Clock Speed:** 2250 MHz
- **Driver Version:** 32.0.101.8331 (November 26, 2025)

---

## Processing Units Available for AI

| Unit | Best Use Case | Power Efficiency |
|------|--------------|------------------|
| **CPU** | General tasks, fallback | Low |
| **NPU** | Always-on AI, wake words, STT | ⭐ Highest |
| **GPU** | Heavy inference, parallel tasks | Medium |

### Recommended Strategy
1. **NPU First** - Use for always-listening wake word detection and speech-to-text
2. **GPU Second** - Use for heavier LLM inference if needed
3. **CPU Fallback** - Only when NPU/GPU unavailable

---

## Intel AI Playground Notes

> ⚠️ **Important:** Intel AI Playground is installed on this system and includes a working Speech-to-Text model that runs on NPU successfully!

This suggests:
- The NPU is properly configured and functional
- OpenVINO runtime is working correctly on the system
- The issue is specifically with the `optimum.intel` Whisper integration, not the hardware




---

*Last Updated: January 5, 2026*
