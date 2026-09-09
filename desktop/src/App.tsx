import { useState, useRef, useEffect } from 'react';
import { Settings, Mic, Send } from 'lucide-react';
import { FloatingOrb, type OrbStateType, type ThemeType } from './components/FloatingOrb';
import { NowPlayingCard } from './components/NowPlayingCard';
import { SettingsModal } from './components/SettingsModal';
import { ToastGlider } from './components/ToastGlider';

export function App() {
  const [viewMode, setViewMode] = useState<'orb' | 'card'>('orb');
  const [orbState, setOrbState] = useState<OrbStateType>('idle');
  const [theme, setTheme] = useState<ThemeType>('glassmorphism');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [textCommand, setTextCommand] = useState<string>('');
  const [isAmbientListening, setIsAmbientListening] = useState<boolean>(() => {
    return localStorage.getItem('daisy_ambient_listening') !== 'false';
  });

  // State refs for event listeners and speech recognition loops
  const recognitionRef = useRef<any>(null);
  const isAmbientRef = useRef<boolean>(isAmbientListening);
  const isSpeakingRef = useRef<boolean>(false);
  const isProcessingRef = useRef<boolean>(false);
  const isDirectListeningRef = useRef<boolean>(false);

  // Toast state
  const [toastMsg, setToastMsg] = useState<string>('Daisy Voice Assistant Ready');
  const [toastMeta, setToastMeta] = useState<string>('Hands-free Active');
  const [toastVisible, setToastVisible] = useState<boolean>(false);
  const toastTimeoutRef = useRef<number | null>(null);

  const showToast = (msg: string, meta: string = '0 tokens', duration: number = 3000) => {
    setToastMsg(msg);
    setToastMeta(meta);
    setToastVisible(true);

    if (toastTimeoutRef.current !== null) {
      window.clearTimeout(toastTimeoutRef.current);
    }
    toastTimeoutRef.current = window.setTimeout(() => {
      setToastVisible(false);
    }, duration);
  };

  // Sync ambient ref
  useEffect(() => {
    isAmbientRef.current = isAmbientListening;
  }, [isAmbientListening]);

  // Continuous Ambient Wake-Word Engine
  useEffect(() => {
    const SpeechRecognition = (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API not detected in environment.');
      return;
    }

    let rec: any = null;
    let isExplicitlyUnmounted = false;

    const startRecognitionSafely = () => {
      if (isSpeakingRef.current || isProcessingRef.current) return;
      try {
        rec.start();
      } catch {
        // Already active or starting
      }
    };

    try {
      rec = new SpeechRecognition();
      recognitionRef.current = rec;
      rec.continuous = true;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onresult = (event: any) => {
        if (isSpeakingRef.current || isProcessingRef.current) return;

        const results = event.results;
        if (!results || results.length === 0) return;
        const latest = results[results.length - 1];
        if (!latest || !latest[0]) return;

        const transcript = latest[0].transcript.trim();
        if (!transcript) return;

        console.log('[Daisy Voice Input]:', transcript);
        const lower = transcript.toLowerCase();

        // Check if wake-word 'daisy' was spoken OR direct mic button was clicked
        const hasWakeWord = lower.includes('daisy');
        const isDirect = isDirectListeningRef.current;

        if (hasWakeWord || isDirect) {
          isDirectListeningRef.current = false;
          runVoiceFlow(transcript, "I'm right here! How can I help you?");
        }
      };

      rec.onerror = (e: any) => {
        if (e.error === 'no-speech' || e.error === 'audio-capture') {
          return; // Expected background silence
        }
        console.warn('SpeechRecognition warning:', e.error);
      };

      rec.onend = () => {
        // Auto-restart continuous listening unless unmounted, speaking, or processing
        if (!isExplicitlyUnmounted && isAmbientRef.current && !isSpeakingRef.current && !isProcessingRef.current) {
          window.setTimeout(() => {
            startRecognitionSafely();
          }, 250);
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
  }, []);

  const toggleAmbientListening = () => {
    setIsAmbientListening((prev) => {
      const next = !prev;
      localStorage.setItem('daisy_ambient_listening', String(next));
      isAmbientRef.current = next;

      if (next) {
        showToast('Ambient Wake: ACTIVE (Listening for "Daisy")', 'Microphone', 3000);
        try {
          recognitionRef.current?.start();
        } catch {}
      } else {
        showToast('Ambient Wake: PAUSED', 'Microphone Muted', 2500);
        try {
          recognitionRef.current?.stop();
        } catch {}
      }
      return next;
    });
  };

  const startListeningDirect = () => {
    isDirectListeningRef.current = true;
    setOrbState('listening');
    showToast('Listening... Speak now', 'Microphone Active', 3500);

    try {
      recognitionRef.current?.start();
    } catch {
      // already active
    }
  };

  // Hotkey listener: Ctrl + Space or Space on body
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey && e.code === 'Space') || (e.code === 'Space' && (e.target as HTMLElement)?.tagName !== 'INPUT')) {
        e.preventDefault();
        startListeningDirect();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSingleClickOrb = () => {
    startListeningDirect();
  };

  const handleDoubleClickOrb = () => {
    setViewMode('card');
    showToast('Expanded to Spotify Player', 'Double-click');
  };

  const handleFoldBack = () => {
    setViewMode('orb');
    showToast('Folded back to Floating Orb', 'Double-click');
  };

  const speakAloud = (text: string) => {
    if (!text || typeof window === 'undefined') return;
    try {
      window.speechSynthesis.cancel();
      const clean = text.replace(/https?:\/\/\S+/g, '').replace(/[*_#`]/g, '').trim();
      if (!clean) return;

      isSpeakingRef.current = true;
      // Temporarily pause mic to prevent Daisy hearing her own output
      try {
        recognitionRef.current?.stop();
      } catch {}

      const utt = new SpeechSynthesisUtterance(clean);
      utt.rate = 1.05;
      utt.pitch = 1.02;

      const voices = window.speechSynthesis.getVoices();
      const naturalVoice = voices.find(v =>
        v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Jenny') || v.name.includes('Zira') || v.name.includes('Google') || v.name.includes('Aria') || v.name.includes('Female'))
      ) || voices.find(v => v.lang.startsWith('en'));

      if (naturalVoice) utt.voice = naturalVoice;

      const resumeAfterSpeech = () => {
        isSpeakingRef.current = false;
        isProcessingRef.current = false;
        setOrbState('idle');

        // Automatically resume hands-free listening
        if (isAmbientRef.current) {
          window.setTimeout(() => {
            try {
              recognitionRef.current?.start();
            } catch {}
          }, 350);
        }
      };

      utt.onend = resumeAfterSpeech;
      utt.onerror = resumeAfterSpeech;

      window.speechSynthesis.speak(utt);
    } catch (e) {
      console.warn('SpeechSynthesis error:', e);
      isSpeakingRef.current = false;
      isProcessingRef.current = false;
      setOrbState('idle');
    }
  };

  const runVoiceFlow = async (cmd: string, defaultTts: string, isGemini: boolean = false) => {
    isProcessingRef.current = true;
    setOrbState('listening');
    showToast(`"${cmd}"`, 'Wake: Daisy', 1600);

    setTimeout(async () => {
      setOrbState('thinking');
      showToast(
        isGemini ? 'Gemini resolving query...' : 'Processing intent...',
        isGemini ? 'Gemini' : '0 tokens',
        1400
      );

      try {
        const res = await fetch('http://127.0.0.1:8000/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: cmd, speak_backend: false }),
        });

        if (res.ok) {
          const data = await res.json();
          setOrbState('executing');
          showToast(data.spoken_reply || `Executed: ${data.source}`, 'Daisy', 2000);

          setTimeout(() => {
            setOrbState('speaking');
            const reply = data.spoken_reply || defaultTts;
            showToast(reply, 'Spoken Reply', 3200);
            speakAloud(reply);
          }, 500);
          return;
        }
      } catch {
        // Fallback simulation
      }

      setTimeout(() => {
        setOrbState('executing');
        showToast('Action processed', 'Executing', 1000);

        setTimeout(() => {
          setOrbState('speaking');
          showToast(defaultTts, 'Daisy Voice', 2600);
          speakAloud(defaultTts);
        }, 500);
      }, 500);
    }, 500);
  };

  const applyTheme = (newTheme: ThemeType) => {
    setTheme(newTheme);
    document.body.setAttribute('data-theme', newTheme);
    showToast(`Applied ${newTheme.toUpperCase()} Theme`, 'Theme Engine');
  };

  return (
    <div className="min-h-screen flex flex-col justify-between p-6 select-none overflow-hidden">
      {/* Top Bar */}
      <header className="w-full max-w-4xl mx-auto flex items-center justify-between pb-3 border-b border-white/[0.05]">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]" />
          <h1 className="text-sm font-semibold tracking-tight text-white flex items-center gap-2">
            Daisy
            <span className="text-xs font-normal text-zinc-400">• Windows AI Voice Assistant</span>
          </h1>
        </div>

        <div className="flex items-center gap-3 text-xs">
          {/* Hands-Free Ambient Wake Toggle */}
          <button
            onClick={toggleAmbientListening}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border transition cursor-pointer text-xs ${
              isAmbientListening
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20'
                : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-zinc-200'
            }`}
            title={
              isAmbientListening
                ? 'Hands-free ambient listening active. Say "Daisy" to wake anytime. Click to mute.'
                : 'Hands-free wake paused. Click to enable ambient listening.'
            }
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isAmbientListening ? 'bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse' : 'bg-zinc-500'
              }`}
            />
            <span className="font-medium">
              {isAmbientListening ? 'Wake: "Daisy"' : 'Wake: Paused'}
            </span>
          </button>

          <div className="hidden sm:flex items-center gap-2 text-zinc-400" title="Local Whisper STT on NVIDIA RTX 3050">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>RTX 3050 • CUDA</span>
          </div>

          <button
            onClick={() => setIsSettingsOpen(true)}
            className="action-btn px-3 py-1.5 text-xs text-zinc-300 hover:text-white flex items-center gap-1.5 cursor-pointer"
          >
            <Settings className="w-3.5 h-3.5 text-zinc-400" />
            <span>Settings & Logs</span>
          </button>
        </div>
      </header>

      {/* Main Stage */}
      <main className="w-full max-w-4xl mx-auto flex-1 flex flex-col items-center justify-center my-2 relative">
        <ToastGlider message={toastMsg} meta={toastMeta} visible={toastVisible} />

        {viewMode === 'orb' ? (
          <FloatingOrb
            orbState={orbState}
            theme={theme}
            onSingleClick={handleSingleClickOrb}
            onDoubleClick={handleDoubleClickOrb}
          />
        ) : (
          <NowPlayingCard onFoldBack={handleFoldBack} onToast={showToast} />
        )}
      </main>

      {/* Quick Command Input Bar */}
      <div className="w-full max-w-md mx-auto my-1 flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/10 backdrop-blur-md shadow-lg">
        <button
          onClick={startListeningDirect}
          title="Click to speak (Ctrl+Space)"
          className="p-1.5 rounded-full text-zinc-400 hover:text-emerald-400 hover:bg-white/10 transition cursor-pointer"
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
          placeholder="Speak or type... (e.g. 'Daisy', 'pause', 'play Starboy')"
          className="flex-1 bg-transparent text-xs text-white placeholder-zinc-500 focus:outline-none"
        />
        <button
          onClick={() => {
            if (textCommand.trim()) {
              runVoiceFlow(textCommand.trim(), 'Processing command...');
              setTextCommand('');
            }
          }}
          className="p-1.5 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 transition cursor-pointer"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Bottom Controls */}
      <footer className="w-full max-w-4xl mx-auto pt-3 border-t border-white/[0.05] flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* State Simulator */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-normal mr-1">Orb State:</span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {(['idle', 'listening', 'thinking', 'executing', 'speaking', 'error'] as OrbStateType[]).map((st) => (
              <button
                key={st}
                onClick={() => {
                  setOrbState(st);
                  showToast(`State: ${st.toUpperCase()}`, 'Manual State Trigger');
                }}
                className={`action-btn px-3 py-1.5 text-xs capitalize cursor-pointer transition ${
                  orbState === st ? 'text-white bg-white/10' : 'text-zinc-400 hover:text-white'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Quick Voice Intent Simulator */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-normal mr-1">Test Intent:</span>
          <button
            onClick={() => runVoiceFlow('Daisy', "I'm listening! How can I help you?")}
            className="action-btn px-3 py-1.5 text-xs text-emerald-300 border-emerald-500/30 cursor-pointer"
          >
            "Daisy"
          </button>
          <button
            onClick={() => runVoiceFlow('pause playback', 'Playback paused.')}
            className="action-btn px-3 py-1.5 text-xs text-zinc-200 cursor-pointer"
          >
            "pause"
          </button>
          <button
            onClick={() => runVoiceFlow('next song', 'Playing next track.')}
            className="action-btn px-3 py-1.5 text-xs text-zinc-200 cursor-pointer"
          >
            "next"
          </button>
          <button
            onClick={() => runVoiceFlow('volume 80', 'Volume set to 80%.')}
            className="action-btn px-3 py-1.5 text-xs text-zinc-200 cursor-pointer"
          >
            "volume 80"
          </button>
          <button
            onClick={() =>
              runVoiceFlow('play some late night synthwave', 'Starting synthwave vibe session.', true)
            }
            className="action-btn px-3 py-1.5 text-xs text-purple-300 border-purple-500/30 cursor-pointer"
          >
            "synthwave" (Gemini)
          </button>
        </div>
      </footer>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentTheme={theme}
        onSelectTheme={applyTheme}
        onSpeak={speakAloud}
      />
    </div>
  );
}

export default App;
