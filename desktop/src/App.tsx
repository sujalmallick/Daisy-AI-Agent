import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Send, 
  Music,
  ChevronRight, 
  Minus,
  X,
  Settings,
  Activity,
  Mic,
} from 'lucide-react';
import { FloatingOrb, type OrbStateType, type ThemeType } from './components/FloatingOrb';
import { CompactPlayer } from './components/CompactPlayer';
import { NowPlayingCard, type PlaybackState } from './components/NowPlayingCard';
import { SettingsModal } from './components/SettingsModal';
import { DashboardView } from './components/DashboardView';
import { ToastGlider } from './components/ToastGlider';
import { 
  resizeWidget, 
  restoreWidgetPosition, 
  saveWidgetPosition, 
  setWidgetOnTop,
  minimizeWindow,
  closeWindow,
  setNativeWindowMode,
  closeApp
} from './utils/windowManager';
import { ttsClient } from './utils/ttsClient';


export function App() {
  const [appMode, setAppMode] = useState<'window' | 'floating' | 'dashboard'>(() => {
    const saved = localStorage.getItem('daisy_app_mode');
    if (saved === 'window' || saved === 'dashboard' || saved === 'floating') {
      return saved;
    }
    return 'window';
  });
  const [orbState, setOrbState] = useState<OrbStateType>('idle');
  const [theme, setTheme] = useState<ThemeType>(() => {
    return (localStorage.getItem('daisy_theme') as ThemeType) || 'glassmorphism';
  });
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [showQuickInput, setShowQuickInput] = useState<boolean>(false);
  const [textCommand, setTextCommand] = useState<string>('');
  const [playerMode, setPlayerMode] = useState<'compact' | 'expanded'>('compact');
  const [isPlayerTucked, setIsPlayerTucked] = useState<boolean>(false);
  const untuckStartXRef = useRef<number | null>(null);
  const [untuckDragOffset, setUntuckDragOffset] = useState<number>(0);

  const [assistantName, setAssistantName] = useState<string>(() => {
    return localStorage.getItem('daisy_assistant_name') || 'Daisy';
  });
  const assistantNameRef = useRef<string>(assistantName);

  const [isAmbientListening, setIsAmbientListening] = useState<boolean>(() => {
    return localStorage.getItem('daisy_ambient_listening') !== 'false';
  });

  // Spotify Playback State
  const [playback, setPlayback] = useState<PlaybackState>({
    isPlaying: false,
    trackTitle: '',
    trackArtist: '',
    artworkUrl: null,
    progressMs: 0,
    durationMs: 0,
    deviceName: 'Spotify',
    volume: 50,
    shuffleState: false,
    repeatState: 'off',
  });
  const [isPlaybackLoading, setIsPlaybackLoading] = useState<boolean>(false);

  // Derive if music is actively present
  const hasActiveTrack = Boolean(
    playback.trackTitle &&
    playback.trackTitle !== 'No Track Playing' &&
    playback.trackTitle !== 'Connecting to Spotify...'
  );

  // State refs for event listeners and speech recognition loops
  const recognitionRef = useRef<any>(null);
  const isAmbientRef = useRef<boolean>(isAmbientListening);
  const isSpeakingRef = useRef<boolean>(false);
  const isProcessingRef = useRef<boolean>(false);
  const isDirectListeningRef = useRef<boolean>(false);
  const volumeDebounceRef = useRef<number | null>(null);

  /**
   * Barge-In refs:
   *  bargeInGraceRef: timestamp when TTS started — 250ms grace to ignore transient mic pops.
   *  bargeInActiveRef: true while Daisy is speaking (mirrors isSpeakingRef but accessible in recognition callbacks).
   */
  const bargeInGraceRef = useRef<number>(0);
  const bargeInActiveRef = useRef<boolean>(false);



  // Toast state
  const [toastMsg, setToastMsg] = useState<string>('Daisy Assistant Ready');
  const [toastMeta, setToastMeta] = useState<string>('Online');
  const [toastVisible, setToastVisible] = useState<boolean>(false);
  const toastTimeoutRef = useRef<number | null>(null);

  const showToast = useCallback((msg: string, meta: string = '0 tokens', duration: number = 3000) => {
    setToastMsg(msg);
    setToastMeta(meta);
    setToastVisible(true);

    if (toastTimeoutRef.current !== null) {
      window.clearTimeout(toastTimeoutRef.current);
    }
    toastTimeoutRef.current = window.setTimeout(() => {
      setToastVisible(false);
    }, duration);
  }, []);

  // Theme synchronization
  useEffect(() => {
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('daisy_theme', theme);
  }, [theme]);

  // Assistant Name synchronization
  useEffect(() => {
    assistantNameRef.current = assistantName;
  }, [assistantName]);

  const handleUpdateAssistantName = async (newName: string) => {
    const clean = newName.trim();
    if (!clean) return;
    setAssistantName(clean);
    localStorage.setItem('daisy_assistant_name', clean);
    showToast(`Assistant name set to "${clean}"`, 'Wake Word Saved', 3000);

    try {
      await fetch('http://127.0.0.1:8000/config/assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: clean }),
      });
    } catch (e) {
      console.warn('Could not sync assistant name to backend:', e);
    }
  };

  // Restore saved window position on startup
  useEffect(() => {
    restoreWidgetPosition();
  }, []);

  // Persist app mode and sync native window mode
  useEffect(() => {
    localStorage.setItem('daisy_app_mode', appMode);
    if (appMode === 'floating') {
      setNativeWindowMode('floating');
    } else if (appMode === 'window') {
      setNativeWindowMode('window');
    }
  }, [appMode]);

  // Dynamic window resizing based on UI mode with mode caching
  const currentWidgetModeRef = useRef<string>('');
  useEffect(() => {
    let targetMode: 'window' | 'dashboard' | 'settings' | 'expanded' | 'compact' | 'orb' = 'window';
    let onTop = false;

    if (appMode === 'window') {
      targetMode = 'window';
      onTop = false;
    } else if (appMode === 'dashboard') {
      targetMode = 'dashboard';
      onTop = false;
    } else if (isSettingsOpen) {
      targetMode = 'settings';
      onTop = true;
    } else if (hasActiveTrack && playerMode === 'expanded') {
      targetMode = 'expanded';
      onTop = true;
    } else if (hasActiveTrack && !isPlayerTucked) {
      targetMode = 'compact';
      onTop = true;
    } else {
      targetMode = 'orb';
      onTop = true;
    }

    if (currentWidgetModeRef.current !== targetMode) {
      currentWidgetModeRef.current = targetMode;
      resizeWidget(targetMode);
      setWidgetOnTop(onTop);
      setNativeWindowMode(appMode === 'window' ? 'window' : 'floating');
    }
  }, [appMode, isSettingsOpen, hasActiveTrack, playerMode, isPlayerTucked]);

  // Sync ambient ref
  useEffect(() => {
    isAmbientRef.current = isAmbientListening;
  }, [isAmbientListening]);

  // Spotify Playback Polling & Control
  const fetchLivePlayback = useCallback(async (silent: boolean = true) => {
    if (!silent) setIsPlaybackLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/playback');
      if (res.ok) {
        const data = await res.json();
        const result = data?.result;
        if (result && result.track) {
          setPlayback({
            isPlaying: !!result.is_playing,
            trackTitle: result.track,
            trackArtist: `${result.artist}${result.album ? ` • ${result.album}` : ''}`,
            artworkUrl: result.artwork_url || null,
            progressMs: result.progress_ms || 0,
            durationMs: result.duration_ms || 0,
            deviceName: result.device_name || 'Active Device',
            volume: result.volume_percent ?? 50,
            shuffleState: !!result.shuffle_state,
            repeatState: result.repeat_state || 'off',
          });
        } else {
          // No track active
          setPlayback((prev) => ({
            ...prev,
            isPlaying: false,
            trackTitle: '',
            trackArtist: '',
            artworkUrl: null,
            progressMs: 0,
            durationMs: 0,
            deviceName: result?.device_name || 'Idle',
            volume: result?.volume_percent ?? prev.volume,
          }));
        }
      }
    } catch (err) {
      console.warn('Playback poll notice:', err);
    } finally {
      if (!silent) setIsPlaybackLoading(false);
    }
  }, []);


  /**
   * speakAloud — Plays text via centralized TTSClient.
   * Replaces the old window.speechSynthesis implementation.
   * Tracks speaking state for barge-in detection.
   */
  const speakAloud = useCallback((text: string, onFinish?: () => void) => {
    if (!text) return;

    // Stop any current speech before starting new one (no overlapping audio)
    ttsClient.stop();

    isSpeakingRef.current = true;
    bargeInActiveRef.current = true;
    bargeInGraceRef.current = Date.now();
    setOrbState('speaking');

    ttsClient.play(text, {
      onStart: () => {
        isSpeakingRef.current = true;
        bargeInActiveRef.current = true;
        setOrbState('speaking');
      },
      onEnd: () => {
        isSpeakingRef.current = false;
        bargeInActiveRef.current = false;
        isProcessingRef.current = false;
        setOrbState('idle');

        if (onFinish) {
          onFinish();
        } else if (isAmbientRef.current) {
          window.setTimeout(() => {
            try {
              recognitionRef.current?.start();
            } catch {}
          }, 350);
        }
      },
      onError: () => {
        isSpeakingRef.current = false;
        bargeInActiveRef.current = false;
        isProcessingRef.current = false;
        setOrbState('idle');
      },
    });
  }, []);



  // Voice command timer management
  const voiceTimersRef = useRef<number[]>([]);
  const clearVoiceTimers = useCallback(() => {
    voiceTimersRef.current.forEach((id) => window.clearTimeout(id));
    voiceTimersRef.current = [];
  }, []);

  const queueVoiceTimer = useCallback((fn: () => void, delayMs: number) => {
    const id = window.setTimeout(fn, delayMs);
    voiceTimersRef.current.push(id);
    return id;
  }, []);

  useEffect(() => {
    return () => {
      clearVoiceTimers();
    };
  }, [clearVoiceTimers]);

  // Voice command flow
  const runVoiceFlow = useCallback(async (cmd: string, defaultTts: string, isGemini: boolean = false) => {
    clearVoiceTimers();
    isProcessingRef.current = true;
    setOrbState('listening');
    showToast(`"${cmd}"`, `Wake: ${assistantNameRef.current}`, 1600);

    queueVoiceTimer(async () => {
      setOrbState('thinking');
      showToast(
        isGemini ? 'Gemini resolving query...' : 'Processing intent...',
        isGemini ? 'Gemini' : 'FastPath',
        1400
      );

      try {
        const res = await fetch('http://127.0.0.1:8000/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: cmd, speak_backend: false, assistant_name: assistantNameRef.current }),
        });

        if (res.ok) {
          const data = await res.json();

          // Check if self-close / exit was triggered ("sayonara daisy", "go home daisy")
          if (data.should_exit) {
            setOrbState('speaking');
            const farewell = data.spoken_reply || "Sayonara! Goodbye!";
            showToast(farewell, 'Sayonara Daisy', 3000);
            speakAloud(farewell);

            // Allow farewell TTS to be spoken aloud before terminating window and backend
            setTimeout(async () => {
              await closeApp();
            }, 2200);
            return;
          }

          // Check if action requires interactive confirmation ("Are you sure you want to close Chrome?")
          if (data.awaiting_confirmation) {
            queueVoiceTimer(() => {
              setOrbState('speaking');
              const question = data.spoken_reply || "Are you sure?";
              showToast(question, 'Confirmation Required', 3500);
              speakAloud(question, () => {
                // When Daisy finishes asking the question, open mic directly for "yes" or "no"
                startListeningDirect();
              });
            }, 450);
            return;
          }

          setOrbState('executing');
          showToast(data.spoken_reply || `Executed: ${data.source}`, assistantNameRef.current, 2000);

          queueVoiceTimer(() => {
            setOrbState('speaking');
            const reply = data.spoken_reply || defaultTts;
            showToast(reply, 'Spoken Reply', 3200);
            speakAloud(reply);
          }, 450);

          // If playback command, refresh immediately
          queueVoiceTimer(() => fetchLivePlayback(true), 600);
          return;
        }
      } catch {
        // Fallback simulation
      }

      queueVoiceTimer(() => {
        setOrbState('executing');
        showToast('Action processed', 'Executing', 1000);

        queueVoiceTimer(() => {
          setOrbState('speaking');
          showToast(defaultTts, `${assistantNameRef.current} Voice`, 2600);
          speakAloud(defaultTts);
        }, 450);
      }, 450);
    }, 450);
  }, [showToast, speakAloud, fetchLivePlayback, clearVoiceTimers, queueVoiceTimer]);

  const startListeningDirect = useCallback(() => {
    isDirectListeningRef.current = true;
    setOrbState('listening');
    showToast('Listening... Speak now', 'Microphone Active', 3500);

    try {
      recognitionRef.current?.start();
    } catch {}
  }, [showToast]);

  // Speech Recognition — Ambient Wake-Word, Direct Mic, and Alexa-Style Barge-In
  useEffect(() => {
    const SpeechRecognition =
      (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API not detected in environment.');
      return;
    }

    let rec: any = null;
    let isExplicitlyUnmounted = false;

    const startRecognitionSafely = () => {
      // NOTE: We allow recognition even while speaking to enable barge-in.
      // We only skip if we are still processing a previous command.
      if (isProcessingRef.current) return;
      try {
        rec.start();
      } catch {
        // Already running — that's fine
      }
    };

    try {
      rec = new SpeechRecognition();
      recognitionRef.current = rec;
      rec.continuous = true;
      // interimResults=true lets us detect speech onset IMMEDIATELY
      // for fastest barge-in — we only act on final results, but interim
      // results tell us speech has started.
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onresult = (event: any) => {
        const results = event.results;
        if (!results || results.length === 0) return;
        const latest = results[results.length - 1];
        if (!latest || !latest[0]) return;

        const isFinal = latest.isFinal;
        const transcript = latest[0].transcript.trim();
        if (!transcript) return;

        const lower = transcript.toLowerCase();
        const customWake = (assistantNameRef.current || 'Daisy').toLowerCase();

        // ── BARGE-IN PATH ─────────────────────────────────────────────────────
        // If Daisy is speaking and we hear something, check if it's a real
        // user command or just echo/self-voice feedback.
        if (bargeInActiveRef.current) {
          // Echo/Self-Interruption Filter:
          // If transcript matches what Daisy is currently saying → ignore (speaker bleed-through).
          const spokenNorm = ttsClient.currentSpokenText.toLowerCase().replace(/[^a-z0-9 ]/g, '');
          const transcriptNorm = lower.replace(/[^a-z0-9 ]/g, '');
          const isEcho =
            spokenNorm.length > 3 &&
            transcriptNorm.length > 0 &&
            (spokenNorm.includes(transcriptNorm) || transcriptNorm.includes(spokenNorm.slice(0, 15)));

          // 250ms grace window: ignore transient mic pops at TTS start
          const elapsedMs = Date.now() - bargeInGraceRef.current;
          const withinGrace = elapsedMs < 250;

          if (!isEcho && !withinGrace && isFinal) {
            // Genuine barge-in detected — stop Daisy immediately
            console.log('[Barge-In] User interrupted Daisy:', transcript);
            ttsClient.stop();
            isSpeakingRef.current = false;
            bargeInActiveRef.current = false;
            isProcessingRef.current = false;

            // Transition: speaking → listening
            setOrbState('listening');
            showToast('Interrupted', assistantNameRef.current, 1200);

            // Process the barge-in command
            const hasWakeWord = lower.includes(customWake) || lower.includes('daisy');
            const isDirect = isDirectListeningRef.current;
            if (hasWakeWord || isDirect) {
              isDirectListeningRef.current = false;
              runVoiceFlow(transcript, "I'm here! How can I help you?");
            } else if (transcript.length > 2) {
              // Any significant speech during barge-in is treated as a command
              runVoiceFlow(transcript, "Got it.");
            }
          }
          return; // Don't process further while speaking
        }

        // ── NORMAL PATH ───────────────────────────────────────────────────────
        // Standard wake-word or direct listening mode (not speaking)
        if (!isFinal) return; // Only act on final results in normal mode
        if (isProcessingRef.current) return;

        console.log(`[${assistantNameRef.current} Voice Input]:`, transcript);
        const hasWakeWord = lower.includes(customWake) || lower.includes('daisy');
        const isDirect = isDirectListeningRef.current;

        if (hasWakeWord || isDirect) {
          isDirectListeningRef.current = false;
          runVoiceFlow(transcript, "I'm right here! How can I help you?");
        }
      };

      rec.onerror = (e: any) => {
        if (e.error === 'no-speech' || e.error === 'audio-capture') {
          return;
        }
        console.warn('SpeechRecognition warning:', e.error);
      };

      rec.onend = () => {
        // Always restart recognition (needed for both ambient and barge-in modes)
        if (!isExplicitlyUnmounted && isAmbientRef.current && !isProcessingRef.current) {
          window.setTimeout(() => {
            startRecognitionSafely();
          }, 200);
        }
      };

      if (isAmbientListening) {
        startRecognitionSafely();
      }
    } catch (err) {
      console.warn('Failed to initialize SpeechRecognition:', err);
    }

    return () => {
      isExplicitlyUnmounted = true;
      try {
        rec?.stop();
      } catch {}
    };
  }, [isAmbientListening, runVoiceFlow, showToast]);



  const toggleAmbientListening = () => {
    setIsAmbientListening((prev) => {
      const next = !prev;
      localStorage.setItem('daisy_ambient_listening', String(next));
      isAmbientRef.current = next;

      if (next) {
        showToast('Ambient Wake: ACTIVE', 'Microphone', 2500);
        try {
          recognitionRef.current?.start();
        } catch {}
      } else {
        showToast('Ambient Wake: PAUSED', 'Microphone Muted', 2000);
        try {
          recognitionRef.current?.stop();
        } catch {}
      }
      return next;
    });
  };

  // Hotkey listener: Ctrl + Space
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey && e.code === 'Space') || (e.code === 'Space' && (e.target as HTMLElement)?.tagName !== 'INPUT')) {
        e.preventDefault();
        startListeningDirect();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [startListeningDirect]);

  // Poll Spotify playback: every 2.5s when active/expanded, every 5s when idle
  useEffect(() => {
    fetchLivePlayback(false);
    const pollIntervalMs = hasActiveTrack || playerMode === 'expanded' ? 2500 : 5000;
    const interval = window.setInterval(() => {
      fetchLivePlayback(true);
    }, pollIntervalMs);
    return () => window.clearInterval(interval);
  }, [hasActiveTrack, playerMode, fetchLivePlayback]);

  // Smooth local progress incrementer
  useEffect(() => {
    if (!playback.isPlaying || playback.durationMs <= 0) return;
    const timer = window.setInterval(() => {
      setPlayback((prev) => {
        if (!prev.isPlaying || prev.progressMs >= prev.durationMs) return prev;
        return { ...prev, progressMs: Math.min(prev.durationMs, prev.progressMs + 1000) };
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [playback.isPlaying, playback.durationMs]);

  const executeAction = async (action: string, value?: any, label?: string) => {
    try {
      let res = await fetch('http://127.0.0.1:8000/playback/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, value }),
      });

      if (!res.ok && res.status === 404) {
        let promptText = action;
        if (action === 'pause') promptText = 'pause';
        else if (action === 'resume' || action === 'play') promptText = 'resume';
        else if (action === 'next') promptText = 'next song';
        else if (action === 'previous') promptText = 'previous song';
        else if (action === 'volume') promptText = `volume ${value}`;

        res = await fetch('http://127.0.0.1:8000/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: promptText, speak_backend: false }),
        });
      }

      if (label) showToast(label, 'Spotify MCP');
      setTimeout(() => fetchLivePlayback(true), 400);
    } catch (err) {
      console.warn(`Action '${action}' failed:`, err);
    }
  };

  const togglePlay = () => {
    const nextState = !playback.isPlaying;
    setPlayback((prev) => ({ ...prev, isPlaying: nextState }));
    executeAction(nextState ? 'resume' : 'pause', null, nextState ? 'Playback Resumed' : 'Playback Paused');
  };

  const handleNext = () => {
    executeAction('next', null, 'Skipped to Next Track');
  };

  const handlePrev = () => {
    executeAction('previous', null, 'Returning to Previous Track');
  };

  const handleVolumeChange = (newVal: number) => {
    setPlayback((prev) => ({ ...prev, volume: newVal }));
    if (volumeDebounceRef.current !== null) {
      window.clearTimeout(volumeDebounceRef.current);
    }
    volumeDebounceRef.current = window.setTimeout(() => {
      executeAction('volume', newVal);
    }, 250);
  };

  const handleResetPosition = () => {
    saveWidgetPosition(100, 100);
    restoreWidgetPosition();
    showToast('Widget position reset', 'Window Manager');
  };

  if (appMode === 'dashboard') {
    return (
      <div className="w-full h-full p-2 select-none overflow-hidden">
        <DashboardView
          onBackToOrb={() => setAppMode('window')}
          onSpeak={(text) => ttsClient.play(text)}
        />
      </div>
    );
  }

  // FULL WINDOW SCREEN MODE (Default startup view: sleek desktop application window matching media_1788984167119.png)
  if (appMode === 'window') {
    return (
      <div className="w-full h-full p-2 select-none overflow-hidden bg-transparent">
        <div className="w-full h-full bg-[#090b11] border border-white/[0.08] rounded-2xl shadow-2xl flex flex-col overflow-hidden backdrop-blur-2xl">
          {/* Custom Draggable Window Titlebar */}
          <div className="pywebview-drag-region flex items-center justify-between px-5 py-3 bg-transparent select-none">
            {/* Left: Subtle brand */}
            <div className="flex items-center gap-2 no-drag opacity-80 hover:opacity-100 transition">
              <span className="text-sm">🌼</span>
              <span className="text-xs font-semibold text-zinc-300 tracking-wide">Daisy AI</span>
            </div>

            {/* Right: Window Controls matching media_1788984167119.png */}
            <div className="flex items-center gap-1.5 no-drag">
              {/* Dashboard / Telemetry Waveform */}
              <button
                onClick={() => setAppMode('dashboard')}
                className="w-8 h-8 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition cursor-pointer"
                title="Dashboard & Telemetry"
              >
                <Activity className="w-4 h-4" />
              </button>

              {/* Settings Gear */}
              <button
                onClick={() => setIsSettingsOpen(true)}
                className="w-8 h-8 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition cursor-pointer"
                title="Settings & Tools"
              >
                <Settings className="w-4 h-4" />
              </button>

              {/* Minimize */}
              <button
                onClick={() => minimizeWindow()}
                className="w-8 h-8 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 flex items-center justify-center transition cursor-pointer"
                title="Minimize"
              >
                <Minus className="w-4 h-4" />
              </button>

              {/* Close */}
              <button
                onClick={() => closeWindow()}
                className="w-8 h-8 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 flex items-center justify-center transition cursor-pointer"
                title="Close Daisy"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Toast Notification Glider (Centered inside window) */}
          <div className="relative">
            <div className="absolute top-1 left-1/2 -translate-x-1/2 z-40 pointer-events-none">
              <ToastGlider message={toastMsg} meta={toastMeta} visible={toastVisible} />
            </div>
          </div>

          {/* Window Body Area - Spacious & Centered matching media_1788984167119.png */}
          <div className="flex-1 relative flex flex-col items-center justify-center px-6 pb-8 overflow-hidden">
            {/* Centered Soft Purple Ambient Glow Aura */}
            <div
              className="absolute w-[460px] h-[460px] rounded-full bg-purple-700/20 blur-[130px] pointer-events-none -z-10"
              style={{ top: '40%', left: '50%', transform: 'translate(-50%, -50%)' }}
            />

            {/* Center Content Stack */}
            <div className="w-full max-w-2xl flex flex-col items-center justify-center z-10">
              {/* 3D Glass Orb with Top Badge and Compact Player Beside It When Active */}
              <div className="mb-2 flex items-center justify-center gap-4">
                <FloatingOrb
                  orbState={orbState}
                  theme={theme}
                  onActivate={startListeningDirect}
                  onOpenSettings={() => setIsSettingsOpen(true)}
                  isAmbientListening={isAmbientListening}
                  assistantName={assistantName}
                  isToastVisible={toastVisible}
                  disableDrag={true}
                />
                {hasActiveTrack && (
                  <div className="shrink-0 animate-in fade-in slide-in-from-left-3 duration-300">
                    <CompactPlayer
                      trackTitle={playback.trackTitle}
                      trackArtist={playback.trackArtist}
                      artworkUrl={playback.artworkUrl}
                      isPlaying={playback.isPlaying}
                      progressMs={playback.progressMs}
                      durationMs={playback.durationMs}
                      onTogglePlay={togglePlay}
                      onNext={handleNext}
                      onPrev={handlePrev}
                      onExpand={() => {}}
                    />
                  </div>
                )}
              </div>

              {/* Typography Prompt & Subtitle */}
              <div className="text-center mt-2 mb-6">
                <h1 className="text-xl md:text-2xl font-semibold text-white tracking-tight">
                  {orbState === 'listening' && <span className="text-sky-400">● Listening... Speak your request</span>}
                  {orbState === 'thinking' && <span className="text-purple-400 animate-pulse">● Thinking with Gemini...</span>}
                  {orbState === 'speaking' && <span className="text-teal-400">● Daisy speaking...</span>}
                  {orbState === 'executing' && <span className="text-orange-400">● Executing action...</span>}
                  {orbState === 'error' && <span className="text-rose-400">● Error encountered</span>}
                  {orbState === 'idle' && (
                    <span>
                      Say <span className="text-[#10b981] font-bold">"Hey {assistantName}"</span> or click to speak
                    </span>
                  )}
                </h1>
                <p className="text-xs text-zinc-400 mt-2 font-normal">
                  Full desktop AI assistant with Spotify control & custom MCP tools
                </p>
              </div>

              {/* Command Input Bar */}
              <div className="w-full max-w-[620px] bg-[#0c0e16]/95 border border-white/10 rounded-full p-1.5 pl-3.5 flex items-center gap-2 shadow-2xl backdrop-blur-xl focus-within:border-emerald-500/50 transition-all">
                <button
                  onClick={startListeningDirect}
                  className={`p-2 rounded-full transition cursor-pointer ${
                    orbState === 'listening'
                      ? 'bg-sky-500/30 text-sky-300 animate-pulse'
                      : 'text-zinc-400 hover:text-white hover:bg-white/5'
                  }`}
                  title="Click to speak (Ctrl+Space)"
                >
                  <Mic className="w-4 h-4" />
                </button>
                <input
                  type="text"
                  value={textCommand}
                  onChange={(e) => setTextCommand(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && textCommand.trim()) {
                      runVoiceFlow(textCommand.trim(), 'Processing command...');
                      setTextCommand('');
                    }
                  }}
                  placeholder="Ask Daisy or command Spotify (e.g. 'play synthwave', 'pause', 'open Chrome')..."
                  className="flex-1 bg-transparent text-xs text-white placeholder-zinc-500 focus:outline-none px-2"
                />
                <button
                  onClick={() => {
                    if (textCommand.trim()) {
                      runVoiceFlow(textCommand.trim(), 'Processing command...');
                      setTextCommand('');
                    }
                  }}
                  className="px-4 py-1.5 rounded-full bg-[#10b981] hover:bg-[#059669] text-black font-semibold text-xs transition cursor-pointer flex items-center gap-1.5 shadow-md hover:scale-[1.02] active:scale-[0.98]"
                >
                  <span>Send</span>
                  <Send className="w-3 h-3" />
                </button>
              </div>

              {/* Quick Suggestion Chips */}
              <div className="flex flex-wrap items-center justify-center gap-2.5 mt-5">
                <button
                  onClick={() => runVoiceFlow('play some synthwave', 'Playing synthwave vibe on Spotify.')}
                  className="px-3.5 py-1.5 rounded-full bg-[#131722]/85 hover:bg-[#1b2234] border border-white/[0.08] text-xs text-zinc-300 hover:text-white transition cursor-pointer flex items-center gap-1.5 shadow-sm"
                >
                  <span>🎵</span>
                  <span>Play Synthwave</span>
                </button>
                <button
                  onClick={() => runVoiceFlow('pause', 'Playback paused.')}
                  className="px-3.5 py-1.5 rounded-full bg-[#131722]/85 hover:bg-[#1b2234] border border-white/[0.08] text-xs text-zinc-300 hover:text-white transition cursor-pointer flex items-center gap-1.5 shadow-sm"
                >
                  <span>⏸</span>
                  <span>Pause Music</span>
                </button>
                <button
                  onClick={() => runVoiceFlow('next track', 'Playing next track.')}
                  className="px-3.5 py-1.5 rounded-full bg-[#131722]/85 hover:bg-[#1b2234] border border-white/[0.08] text-xs text-zinc-300 hover:text-white transition cursor-pointer flex items-center gap-1.5 shadow-sm"
                >
                  <span>⏭</span>
                  <span>Next Track</span>
                </button>
                <button
                  onClick={() => runVoiceFlow("what's the weather today", 'Checking current weather briefing.', true)}
                  className="px-3.5 py-1.5 rounded-full bg-[#131722]/85 hover:bg-[#1b2234] border border-white/[0.08] text-xs text-zinc-300 hover:text-white transition cursor-pointer flex items-center gap-1.5 shadow-sm"
                >
                  <span>🌤</span>
                  <span>Weather Brief</span>
                </button>
              </div>
            </div>

            {/* Circular Dot Floating Button (Switches into Floating Widget Overlay) */}
            <button
              onClick={() => setAppMode('floating')}
              className="absolute bottom-5 right-6 z-30 group flex items-center gap-2 p-2 rounded-full bg-[#0d101a]/95 hover:bg-[#151b2c] border border-white/15 hover:border-emerald-500/50 shadow-[0_8px_25px_rgba(0,0,0,0.8)] hover:shadow-[0_0_20px_rgba(16,185,129,0.35)] transition-all duration-300 cursor-pointer hover:scale-105 active:scale-95"
              title="Switch to Floating Desktop Overlay"
            >
              {/* Circular 3D Glowing Dot */}
              <div className="relative w-6 h-6 rounded-full flex items-center justify-center">
                <span className="absolute -inset-1 rounded-full bg-emerald-500/30 blur-sm group-hover:bg-emerald-400/50 animate-pulse pointer-events-none" />
                <div
                  className="relative w-5 h-5 rounded-full border border-emerald-300/50 shadow-inner flex items-center justify-center"
                  style={{
                    background: 'radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.95) 0%, rgba(16, 185, 129, 0.9) 35%, rgba(6, 78, 59, 0.95) 75%, #021a12 100%)',
                    boxShadow: '0 0 10px rgba(16, 185, 129, 0.5), inset 0 1px 2px rgba(255, 255, 255, 0.8), inset 0 -2px 4px rgba(0, 0, 0, 0.8)'
                  }}
                >
                  <div className="absolute top-0.5 left-1 w-2.5 h-1 rounded-full bg-white/70 blur-[0.3px] -rotate-30" />
                </div>
              </div>

              {/* Smooth Expandable Text Label */}
              <span className="max-w-0 overflow-hidden whitespace-nowrap text-xs font-semibold text-zinc-300 group-hover:max-w-xs group-hover:pr-2 transition-all duration-300 ease-in-out">
                Floating Overlay
              </span>
            </button>
          </div>
        </div>

        {/* Settings Modal (available in window mode) */}
        <SettingsModal
          isOpen={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          currentTheme={theme}
          onSelectTheme={(t) => setTheme(t)}
          onSpeak={(text) => ttsClient.play(text)}
          assistantName={assistantName}
          onUpdateAssistantName={handleUpdateAssistantName}
          orbState={orbState}
          onSetOrbState={(st) => setOrbState(st)}
          onRunVoiceFlow={runVoiceFlow}
          isAmbientListening={isAmbientListening}
          onToggleAmbientListening={toggleAmbientListening}
          onResetPosition={handleResetPosition}
          onOpenDashboard={() => setAppMode('dashboard')}
          appMode={appMode}
          onSetAppMode={(m) => setAppMode(m)}
        />
      </div>
    );
  }

  // FLOATING WIDGET OVERLAY MODE (Pure desktop floating orb + sidecar player)
  const isExpanded = hasActiveTrack && !isPlayerTucked && playerMode === 'expanded';

  return (
    <div className="relative w-full h-full select-none overflow-visible bg-transparent flex justify-start items-center">
      {/* Toast Notification Glider (Centered directly above the Orb anchor) */}
      <div className="absolute top-2 left-[95px] -translate-x-1/2 z-40 pointer-events-none">
        <ToastGlider message={toastMsg} meta={toastMeta} visible={toastVisible} />
      </div>

      {/* Main Floating Assistant Cluster */}
      <div
        className={`relative pl-5 flex ${
          isExpanded ? 'items-start pt-[20px] gap-3.5' : 'items-center gap-3'
        }`}
      >
        {/* Daisy Orb Anchor */}
        <div className={isExpanded ? 'mt-[10px] shrink-0' : 'shrink-0'}>
          <FloatingOrb
            orbState={orbState}
            theme={theme}
            onActivate={startListeningDirect}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onToggleTextInput={() => setShowQuickInput((prev) => !prev)}
            onOpenDashboard={() => setAppMode('dashboard')}
            onOpenWindowMode={() => setAppMode('window')}
            isAmbientListening={isAmbientListening}
            assistantName={assistantName}
            isQuickInputOpen={showQuickInput}
            isToastVisible={toastVisible}
          />
        </div>

        {/* Docked Pull-Out Tab (Shown when music is playing but user swiped player into orb) */}
        {hasActiveTrack && isPlayerTucked && (
          <div
            onPointerDown={(e) => {
              if (e.button !== 0) return;
              untuckStartXRef.current = e.clientX;
            }}
            onPointerMove={(e) => {
              if (untuckStartXRef.current === null) return;
              const dx = e.clientX - untuckStartXRef.current;
              if (dx > 0) {
                setUntuckDragOffset(Math.min(35, dx));
              }
            }}
            onPointerUp={() => {
              if (untuckStartXRef.current !== null && untuckDragOffset > 15) {
                setIsPlayerTucked(false);
              }
              untuckStartXRef.current = null;
              setUntuckDragOffset(0);
            }}
            onPointerCancel={() => {
              untuckStartXRef.current = null;
              setUntuckDragOffset(0);
            }}
            onClick={() => setIsPlayerTucked(false)}
            className="flex items-center justify-center -ml-2 self-center z-20 cursor-pointer group/pill select-none touch-none animate-in fade-in zoom-in-95 duration-200"
            title="Swipe right or click to reveal music player"
            style={{
              transform: `translateX(${untuckDragOffset}px)`,
              transition: untuckDragOffset > 0 ? 'none' : 'transform 0.2s ease',
            }}
          >
            <div className="flex items-center gap-1 py-2 px-2 rounded-r-xl bg-[#0c0f14]/90 hover:bg-[#1a202c]/95 border border-l-0 border-white/15 shadow-xl hover:border-emerald-500/40 transition-all text-zinc-400 group-hover/pill:text-emerald-400">
              <Music className={`w-3.5 h-3.5 ${playback.isPlaying ? 'animate-pulse text-emerald-400' : 'text-zinc-400'}`} />
              <ChevronRight className="w-3.5 h-3.5 -ml-0.5 group-hover/pill:translate-x-0.5 transition-transform" />
            </div>
          </div>
        )}

        {/* Music Player Sidecar (Appears beside the Orb when active and not tucked) */}
        {hasActiveTrack && !isPlayerTucked && (
          <div className="shrink-0 animate-in fade-in slide-in-from-left-2 duration-300">
            {playerMode === 'expanded' ? (
              <NowPlayingCard
                playback={playback}
                onFoldBack={() => setPlayerMode('compact')}
                onToast={showToast}
                onTogglePlay={togglePlay}
                onNext={handleNext}
                onPrev={handlePrev}
                onVolumeChange={handleVolumeChange}
                onRefresh={() => fetchLivePlayback(false)}
                isLoading={isPlaybackLoading}
              />
            ) : (
              <CompactPlayer
                trackTitle={playback.trackTitle}
                trackArtist={playback.trackArtist}
                artworkUrl={playback.artworkUrl}
                isPlaying={playback.isPlaying}
                progressMs={playback.progressMs}
                durationMs={playback.durationMs}
                onTogglePlay={togglePlay}
                onNext={handleNext}
                onPrev={handlePrev}
                onExpand={() => setPlayerMode('expanded')}
                onTuck={() => setIsPlayerTucked(true)}
              />
            )}
          </div>
        )}
      </div>

      {/* Popover Quick Text Command Bar (Centered neatly at bottom of orb) */}
      {showQuickInput && (
        <div className="absolute bottom-2 left-[95px] -translate-x-1/2 z-30 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-black/95 backdrop-blur-xl border border-white/20 shadow-2xl w-[180px]">
          <input
            type="text"
            value={textCommand}
            onChange={(e) => setTextCommand(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && textCommand.trim()) {
                runVoiceFlow(textCommand.trim(), 'Processing command...');
                setTextCommand('');
                setShowQuickInput(false);
              }
            }}
            placeholder="Type command..."
            className="flex-1 bg-transparent text-xs text-white placeholder-zinc-500 focus:outline-none"
            autoFocus
          />
          <button
            onClick={() => {
              if (textCommand.trim()) {
                runVoiceFlow(textCommand.trim(), 'Processing command...');
                setTextCommand('');
                setShowQuickInput(false);
              }
            }}
            className="text-zinc-400 hover:text-white transition cursor-pointer"
          >
            <Send className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Settings & All Controls Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentTheme={theme}
        onSelectTheme={(t) => setTheme(t)}
        onSpeak={(text) => ttsClient.play(text)}
        assistantName={assistantName}
        onUpdateAssistantName={handleUpdateAssistantName}
        orbState={orbState}
        onSetOrbState={(st) => setOrbState(st)}
        onRunVoiceFlow={runVoiceFlow}
        isAmbientListening={isAmbientListening}
        onToggleAmbientListening={toggleAmbientListening}
        onResetPosition={handleResetPosition}
        onOpenDashboard={() => setAppMode('dashboard')}
        appMode={appMode}
        onSetAppMode={(m) => setAppMode(m)}
      />
    </div>
  );
}


export default App;
