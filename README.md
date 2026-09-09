# Daisy 🌼 — Windows Desktop AI Voice Assistant

Daisy is an open-source **Windows desktop AI voice assistant** living natively on your screen as a **floating glass orb widget**. Built on the **Model Context Protocol (MCP)**, it offers friction-free natural voice control over Spotify, desktop files, and future tools.

---

## 🌟 Key Features

- 🔮 **Dual-Form Desktop UI (Tauri 2.0)**:
  - **Compact Floating Glass Orb**: Lives frameless and transparent on your desktop with organic levitation physics, prismatic shine highlights, and live state color shifting.
  - **Spotify Now Playing Card**: Double-clicking the orb smoothly expands it into a full Spotify player card (vinyl disc peeking out, `● LIVE` badge, scrubber, transport row, and volume slider). Double-clicking again folds it back into the orb.
- ⚡ **Universal Hardware Acceleration**:
  - **Tier 1 (NVIDIA CUDA)**: Auto-detects NVIDIA GPUs (e.g. RTX 3050) to run `faster-whisper` in `float16` for sub-150ms transcription with 0% CPU strain.
  - **Tier 2 (DirectML)**: Offloads speech recognition on AMD/Intel graphics.
  - **Tier 3 (CPU-Quantized)**: 8-bit quantized whisper running with low RAM (<250MB) on budget PCs.
- 🎯 **0-Token Local Intent Engine**:
  - Uses an Alexa-style local grammar to evaluate routine playback commands (`pause`, `resume`, `next`, `volume 80`, `repeat`, `shuffle`) in **< 10ms with 0 tokens consumed**.
- 🧠 **Google Gemini 2.5 Flash Fallback**:
  - Engaged exclusively for semantic vibe generation, mood playlists, and agentic multi-step goals.
- 🗣️ **Two-Way Voice (TTS)**:
  - Listens to speech (wake word *"Daisy"* or `Ctrl+Space`) and speaks replies aloud (Edge-TTS) while the orb glows in radiant teal with audio waveforms.
- 🧩 **Modular MCP Architecture**:
  - Implements the Model Context Protocol (`MCP_INTEGRATION.md`) with built-in **Spotify** and **Filesystem** MCP servers, decoupled from the UI.
- 🎨 **4 Live Visual Themes**:
  - **Glassmorphism**, **Sleek Minimal**, **Cyberpunk Neon**, and **Nordic Aurora** configurable live in Settings.

---

## 🛠️ Project Structure

```
Daisy-AI-Agent/
├── desktop/                  # Tauri 2.0 / React + TypeScript Frontend
│   ├── src-tauri/            # Rust Tauri shell configuration & window handling
│   ├── src/
│   │   ├── components/       # FloatingOrb, NowPlayingCard, SettingsModal, ToastGlider
│   │   ├── App.tsx           # Dual-view router & state management
│   │   └── index.css         # Theme engine & glassmorphic styling
│   └── package.json
├── backend/                  # Python Core Service
│   ├── main.py               # FastAPI backend & WebSocket dispatcher
│   ├── hardware.py           # Auto-detects CUDA / DirectML / CPU tiers
│   ├── voice/                # Adaptive STT (faster-whisper) & TTS (Edge-TTS)
│   ├── agent/                # FastPath, Alexa 0-token grammar & Gemini planner
│   └── mcp/                  # MCP Manager & built-in servers (Spotify, Filesystem)
├── .env.example              # Environment variables template
└── requirements.txt          # Python dependencies
```

---

## 🚀 Quickstart

### 1. Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```
Add your credentials in `.env`:
- `SPOTIPY_CLIENT_ID` & `SPOTIPY_CLIENT_SECRET` (from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard))
- `SPOTIPY_REDIRECT_URI=http://localhost:8888/callback`
- `GEMINI_API_KEY` (from [Google AI Studio](https://aistudio.google.com/))

### 2. Run the Python Backend
```bash
python backend/main.py
```
Backend starts on `http://127.0.0.1:8000`.

### 3. Run the Desktop Application
```bash
cd desktop
npm run dev
```
Open the local URL or launch via Tauri.

---

## 💡 Voice Commands & Shortcuts

- **Single-Click Orb** or **`Ctrl + Space`**: Activates voice listening.
- **Double-Click Orb**: Expands into the Spotify **Now Playing** card.
- **Double-Click Card**: Folds back into the compact floating orb.
- **Instant Local Commands (0 Tokens)**:
  - *"Daisy, pause"*
  - *"Daisy, resume"*
  - *"Daisy, next track"*
  - *"Daisy, volume 80"*
  - *"Daisy, play Starboy"*
- **Gemini Semantic Prompts**:
  - *"Daisy, play some late-night synthwave for coding"*
  - *"Daisy, what song is this?"*
  - *"Daisy, pause music and search for my notes"* (Multi-MCP Agentic execution)
