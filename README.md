# 🤖 Jarvis — AI Personal Assistant

A **powerful, locally-hosted AI personal assistant**.  
No cloud, no subscriptions, complete privacy. Powered by [Ollama](https://ollama.com) and Google's Gemma 4 models.

<div align="center">
  <img src="static/logo.png" alt="Jarvis Logo" width="150" />
</div>

---

## ✨ Features

- 🧠 **100% Local AI** — Runs directly on your CPU/GPU. Complete privacy.
- 🛠️ **Smart Hardware Detection** — Automatically analyzes your PC's RAM, CPU, and GPU capabilities to recommend the optimal AI model for your system.
- ⚡ **One-Click Setup Wizard** — A sleek, automated installation process. No terminal needed!
- 🌐 **Deep Research & Web Search** — Real-time abilities to browse the web and pull information.
- 🖥️ **Computer Vision & Control** — Can analyze your screen and control basic desktop applications natively.
- 📰 **Telegram News Briefing** — Connects to your Telegram account to read and summarize your subscribed channels.
- 💬 **Rich Chat Interface** — Beautiful, native desktop UI with markdown, code logic, and responsive design.

---

## ⚡ Quick Start: 1-Click Install

We built the installation process to require **zero technical knowledge**. 

### 1. Download the Project
Clone the repository, or download it as a ZIP file and extract it to a folder on your computer.
```bash
git clone https://github.com/elchanany/Jarvis.git
cd Jarvis
```

### 2. Run the Installer
Double-click on the installation file:
> **`Install_Jarvis.bat`**

### What happens behind the scenes?
1. **Python Check:** Ensures you have Python installed. If not, takes you to the official download page.
2. **Environment Setup:** Creates an isolated environment so it doesn't conflict with your PC.
3. **Hardware Scan:** Detects your RAM and GPU to offer you the best AI model.
4. **Ollama Installation (if missing):** Downloads the optimal AI model directly from Ollama Hub.
5. **Desktop Shortcut:** When finished, creates a sleek `Jarvis AI` icon right on your desktop!

---

## 📁 Repository Structure

```
Jarvis/
├── app.py              # Main Flask Backend / API
├── Jarvis.pyw          # Desktop Window Launcher (pywebview)
├── Install_Jarvis.bat  # ONE-CLICK INSTALLER 🛠️ 
├── run_jarvis.bat      # Runs the app silently without a terminal
├── gemma_brain.py      # AI model interface logic (Ollama streaming)
├── templates/
│   ├── index.html      # Main Chat UI
│   └── setup.html      # Smart Setup Wizard UI
├── static/
│   ├── style.css       # UI Styles and Animations
│   └── logo.png        # System Logo
└── (Other python plugins and AI logic files)
```

---

## 🔧 Manual Setup (For Developers)

If you prefer to set up manually or contribute to the project:

```bash
# Create venv
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python Jarvis.pyw
```

## 📄 License
MIT License. Free to use, modify, and distribute.
