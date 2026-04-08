# 🤖 Jarvis — AI Personal Assistant

A **local AI personal assistant** that runs entirely on your machine.  
No cloud, no subscriptions. Powered by [Ollama](https://ollama.com).

---

## ✨ Features

- 🧠 **Local AI** — runs on your GPU/CPU via Ollama
- 🌐 **Web + Deep Research** — real-time prices, news, and search
- 📺 **Telegram News Briefing** — reads your subscribed channels
- 🎵 **System Control** — Spotify, volume, brightness, apps
- 🖥️ **Computer Vision** — screenshot analysis and agentic control
- 💬 **Markdown Rendering** — bold, tables, code blocks, citations
- 🔧 **First-Run Setup Wizard** — installs everything automatically

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/jarvis.git
cd jarvis
```

### 2. Run the launcher
**Windows:**
```
start.bat
```

The launcher will automatically:
- Create a Python virtual environment
- Install all dependencies
- Launch the setup wizard (first run only)
- Open Jarvis as a **native desktop window**

---

## 🛠️ Manual Setup

```bash
# Create venv
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Ollama: https://ollama.com

# Run
python app.py
```

---

## 📁 Project Structure

```
jarvis/
├── app.py              # Flask backend
├── gemma_brain.py      # AI model interface (Ollama)
├── tools_registry.py   # All available tools
├── templates/
│   ├── index.html      # Main chat UI
│   └── setup.html      # First-run setup wizard
├── static/
│   ├── app.js          # Frontend logic
│   ├── style.css       # UI styles
│   └── logo.png        # ← Place your logo here
├── launcher.py         # Native window launcher
├── start.bat           # Windows launcher script
└── requirements.txt    # Python dependencies
```

---

## 🖼️ Logo

Place your logo at `static/logo.png` — it will automatically appear in the setup wizard and (optionally) the taskbar.

---

## 🔧 Configuration

Edit `jarvis_config.json` to customize the assistant persona and behavior.

---

## 📦 Tech Stack

- **Backend:** Python / Flask
- **AI Engine:** Ollama (local models)
- **Frontend:** Vanilla JS + CSS
- **Markdown:** marked.js
- **Native Window:** pywebview

---

## 📄 License

MIT License — free to use and modify.
