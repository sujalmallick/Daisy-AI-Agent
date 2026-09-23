# Daisy 🌼 — Autonomous Windows Desktop AI Voice Assistant

Daisy is an open-source **Windows desktop AI voice assistant** living natively on your screen as a **floating glass orb widget**. Built on the **Model Context Protocol (MCP)**, Daisy combines a **0-token local Alexa intent engine**, an **autonomous multi-step ReAct agent**, a **local Desktop RAG pipeline**, and a **Human-in-the-Loop (HITL) safety system**.

---

## 🌟 Key Features

- 🔮 **Dual-Form Desktop UI (Tauri 2.0 / PyWebView)**:
  - **Compact Floating Glass Orb**: Lives frameless and transparent on your desktop with levitation physics, prismatic shine highlights, and live state color shifting.
  - **Spotify Now Playing Card**: Double-clicking the orb smoothly expands it into a full Spotify player card (vinyl disc, `● LIVE` badge, scrubber, transport row, and volume slider).
  - **HITL Confirmation Glider**: Interactive approval cards for sensitive desktop actions.

- 🎯 **0-Token Local Alexa Intent Grammar**:
  - Uses an Alexa Skills Kit–inspired pattern matcher to evaluate routine playback, volume, app management, and dialog confirmations in **< 10ms with 0 tokens consumed**.
  - Local state machine for `AMAZON.YesIntent` / `AMAZON.NoIntent` conversational confirmations.

- 📚 **Desktop RAG (Retrieval-Augmented Generation)**:
  - Ask Daisy about any document on your machine: *"Daisy, what does my resume say about Python?"* or *"Daisy, summarize project_plan on my desktop"*.
  - **Dynamic Cross-Platform Path Resolution**: Scans `~/Desktop`, `~/Documents`, `~/Downloads`, and custom `DAISY_SEARCH_PATHS`.
  - **File Support**: Reads `.pdf` (via `pypdf`), `.docx`, `.txt`, and `.md`.
  - **Zero-Token Local Retrieval**: Indexes document chunks into a lightweight local BM25 vector cache, feeding only the top 2–3 relevant snippets to Gemini (**95%+ token savings** vs passing raw files).
  - **Security Sandboxing**: Strictly prevents path traversal into system directories (`System32`, `Windows`, `.ssh`, `.aws`, `.env`, credentials).

- 🛡️ **Human-in-the-Loop (HITL) Safety Engine**:
  - **3-Tier Risk Classifier**:
    - `Tier 1 (Safe)`: Playback, volume, document reading -> Auto-executes.
    - `Tier 2 (Ambiguous)`: Multiple candidate files found -> Prompts user to choose.
    - `Tier 3 (Destructive)`: Closing running apps, deleting files, system shutdown -> Pauses execution and requires explicit human approval.
  - **Dual-Modality Approval**: Approve or cancel via voice (*"Yes, do it"* / *"Cancel that"*, **0 tokens**) or via the visual desktop card.

- 🧠 **Token-Optimized Agentic ReAct Brain (Gemini 2.5 Flash)**:
  - **Dynamic Tool Pruning**: Automatically filters tool schemas by query domain (`media`, `rag`, `desktop`), slashing prompt tokens by **60%–75%**.
  - **Bounded ReAct Loop**: Up to 3-step autonomous reasoning, tool execution, observation feedback, and voice synthesis.
  - **Strict Voice Budget**: Enforces concise, single-sentence responses (< 15 words) normalized for text-to-speech.

- ⚡ **Universal Hardware Acceleration**:
  - **Tier 1 (NVIDIA CUDA)**: Runs `faster-whisper` in `float16` for sub-150ms transcription with 0% CPU strain.
  - **Tier 2 (DirectML)**: Offloads speech recognition on AMD/Intel graphics.
  - **Tier 3 (CPU-Quantized)**: 8-bit quantized whisper running with low RAM (< 250MB).

- 🗣️ **Two-Way Voice (TTS)**:
  - Listens to speech (wake word *"Daisy"* or `Ctrl+Space`) and speaks replies aloud (Edge-TTS) with radiant orb waveforms.

- 🧩 **Modular MCP Architecture**:
  - Built-in **Spotify**, **Filesystem**, **Desktop RAG**, and **App Launcher** MCP servers.

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
│   ├── main.py               # FastAPI backend, HITL routes & WebSocket dispatcher
│   ├── hardware.py           # Auto-detects CUDA / DirectML / CPU tiers
│   ├── voice/                # Adaptive STT (faster-whisper) & TTS (Edge-TTS)
│   ├── agent/                # FastPath, Alexa 0-token grammar & ReAct planner
│   │   ├── alexa_grammar.py  # Local Alexa-style intent & slot parser
│   │   ├── fastpath.py       # Deterministic execution (< 10ms, 0 tokens)
│   │   └── planner.py        # Gemini Flash ReAct multi-step planner
│   ├── rag/                  # Desktop RAG Subsystem
│   │   ├── path_resolver.py  # Dynamic path discovery & security sandboxing
│   │   ├── loader.py         # Ingestion for PDF, DOCX, TXT, MD
│   │   ├── chunker.py        # Sentence-aware chunker with overlap
│   │   ├── vector_store.py   # Local BM25 vector index (.daisy_cache/)
│   │   └── retriever.py      # Semantic top-k search coordinator
│   ├── hitl/                 # Human-In-The-Loop Safety Engine
│   │   └── manager.py        # 3-tier risk matrix, breakpoints & confirmation store
│   └── mcp/                  # Model Context Protocol Manager & Servers
│       └── servers/
│           ├── spotify/      # Spotify playback control
│           ├── filesystem/   # Local file browsing
│           ├── app_launcher/ # Windows application management
│           └── rag/          # Desktop document semantic search tools
├── tests/                    # Automated unit & integration test suite
│   └── test_agentic_system.py
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
Configure your credentials in `.env`:
- `SPOTIPY_CLIENT_ID` & `SPOTIPY_CLIENT_SECRET` (from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard))
- `SPOTIPY_REDIRECT_URI=http://localhost:8888/callback`
- `GEMINI_API_KEY` (from [Google AI Studio](https://aistudio.google.com/))
- `DAISY_SEARCH_PATHS` *(Optional)*: Additional custom directories to index for RAG (e.g. `~/Projects,D:/MyNotes`)

### 2. Install Dependencies
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Automated Tests
Verify that all subsystems (Alexa Grammar, RAG, HITL, MCP Pruning) are operational:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 4. Run the Python Backend
```bash
python backend/main.py
```
Backend starts on `http://127.0.0.1:8000`.

### 5. Run the Desktop Application
```bash
# Web/Desktop GUI (PyWebView or Tauri)
python daisy_app.py

# Or via Tauri dev server:
cd desktop
npm install
npm run dev
```

---

## 💡 Voice Commands & Examples

### 🎯 Instant Local Commands (0 Tokens, < 10ms)
- *"Daisy, pause"* / *"Daisy, resume"*
- *"Daisy, next track"* / *"Daisy, previous song"*
- *"Daisy, volume 80"* / *"Daisy, mute"*
- *"Daisy, play Starboy by The Weeknd"*
- *"Daisy, open Chrome"* / *"Daisy, launch VS Code"*

### 📚 Desktop RAG Queries (Token-Efficient Semantic Search)
- *"Daisy, what does my resume say about Python?"*
- *"Daisy, summarize project_plan on my desktop"*
- *"Daisy, what is the deadline in notes.txt?"*
- *"Daisy, search my tax report for total expenses"*

### 🛡️ Human-In-The-Loop (HITL) Safety Confirmations
- **You**: *"Daisy, close Google Chrome"*
- **Daisy**: *"Are you sure you want to close Google Chrome?"*
- **You**: *"Yes, do it"* *(or click `[Approve]` on screen — **0 tokens consumed**)*
- **Daisy**: *"Closed Google Chrome."*

### 🧠 Agentic Multi-Step Reasoning
- *"Daisy, pause the music and find what time my meeting is in notes.txt"*
- *"Daisy, play some late-night synthwave for deep coding"*
