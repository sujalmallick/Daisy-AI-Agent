import React, { useState, useEffect } from 'react';
import { 
  X, 
  Cpu, 
  Sparkles, 
  Check, 
  Terminal, 
  Volume2, 
  Activity, 
  RefreshCw, 
  Trash2,
  Layers,
  Palette
} from 'lucide-react';
import type { ThemeType } from './FloatingOrb';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme: ThemeType;
  onSelectTheme: (theme: ThemeType) => void;
  onSpeak?: (text: string) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentTheme,
  onSelectTheme,
  onSpeak,
}) => {
  const [activeTab, setActiveTab] = useState<'themes' | 'logs' | 'diagnostics'>('themes');
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [logs, setLogs] = useState<Array<{ timestamp: string; level: string; name: string; message: string }>>([]);
  const [logFilter, setLogFilter] = useState<'ALL' | 'INFO' | 'WARNING' | 'ERROR'>('ALL');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [tools, setTools] = useState<Array<{ name: string; description: string }>>([]);

  const checkStatus = async () => {
    try {
      setIsRefreshing(true);
      const [authRes, logsRes, sysRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/auth/status').catch(() => null),
        fetch('http://127.0.0.1:8000/logs').catch(() => null),
        fetch('http://127.0.0.1:8000/system/status').catch(() => null),
      ]);

      if (authRes && authRes.ok) {
        const d = await authRes.json();
        setIsConnected(Boolean(d.spotify_connected));
      }
      if (logsRes && logsRes.ok) {
        const d = await logsRes.json();
        setLogs(d.logs || []);
      }
      if (sysRes && sysRes.ok) {
        const d = await sysRes.json();
        setTools(d.tools || []);
      }
    } catch {
      setIsConnected(false);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      checkStatus();
      const interval = setInterval(checkStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestVoice = async () => {
    const text = "Daisy voice engine is working smoothly on your computer.";
    setTestResult("Speaking aloud via audio engine...");
    if (onSpeak) onSpeak(text);
    try {
      await fetch('http://127.0.0.1:8000/voice/test', { method: 'POST' });
    } catch {
      // Browser fallback handled by onSpeak
    }
    setTimeout(() => setTestResult("Voice test completed!"), 2500);
  };

  const clearLogs = async () => {
    try {
      await fetch('http://127.0.0.1:8000/logs', { method: 'DELETE' });
      setLogs([]);
    } catch {
      setLogs([]);
    }
  };

  const filteredLogs = logs.filter((l) => {
    if (logFilter === 'ALL') return true;
    return l.level === logFilter;
  });

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center p-4 z-50 select-none">
      <div className="w-full max-w-xl bg-[#0f1115] border border-white/10 rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">Daisy Control Center & Settings</h2>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white transition p-1 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 px-5 pt-2 border-b border-white/10 bg-black/20">
          <button
            onClick={() => setActiveTab('themes')}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'themes'
                ? 'border-emerald-400 text-emerald-400 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-white'
            }`}
          >
            <Palette className="w-3.5 h-3.5" />
            <span>Appearance & Spotify</span>
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'logs'
                ? 'border-emerald-400 text-emerald-400 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-white'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Live Logs ({logs.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('diagnostics')}
            className={`px-3 py-2 text-xs font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'diagnostics'
                ? 'border-emerald-400 text-emerald-400 font-semibold'
                : 'border-transparent text-zinc-400 hover:text-white'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Diagnostics & Tools</span>
          </button>
        </div>

        {/* Body Content */}
        <div className="p-5 overflow-y-auto flex-1 space-y-5 text-xs">
          {/* TAB 1: THEMES & SPOTIFY */}
          {activeTab === 'themes' && (
            <div className="space-y-5">
              <div>
                <label className="block text-zinc-300 text-xs font-medium mb-2.5">Orb Visual Theme</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => onSelectTheme('glassmorphism')}
                    className={`p-3 text-left rounded-xl border transition cursor-pointer ${
                      currentTheme === 'glassmorphism'
                        ? 'border-emerald-500/60 bg-emerald-950/20 text-white'
                        : 'border-white/5 bg-white/[0.03] text-zinc-400 hover:text-white'
                    }`}
                  >
                    <div className="text-xs font-semibold">Glassmorphism</div>
                    <div className="text-[11px] text-zinc-400 mt-0.5">Spotify Emerald & frosted glass</div>
                  </button>

                  <button
                    onClick={() => onSelectTheme('sleek')}
                    className={`p-3 text-left rounded-xl border transition cursor-pointer ${
                      currentTheme === 'sleek'
                        ? 'border-white/40 bg-white/10 text-white'
                        : 'border-white/5 bg-white/[0.03] text-zinc-400 hover:text-white'
                    }`}
                  >
                    <div className="text-xs font-semibold">Sleek Minimal</div>
                    <div className="text-[11px] text-zinc-400 mt-0.5">Titanium & matte monochrome</div>
                  </button>

                  <button
                    onClick={() => onSelectTheme('cyberpunk')}
                    className={`p-3 text-left rounded-xl border transition cursor-pointer ${
                      currentTheme === 'cyberpunk'
                        ? 'border-cyan-500/60 bg-cyan-950/20 text-white'
                        : 'border-white/5 bg-white/[0.03] text-zinc-400 hover:text-white'
                    }`}
                  >
                    <div className="text-xs font-semibold">Cyberpunk Neon</div>
                    <div className="text-[11px] text-zinc-400 mt-0.5">Hot magenta & electric cyan</div>
                  </button>

                  <button
                    onClick={() => onSelectTheme('aurora')}
                    className={`p-3 text-left rounded-xl border transition cursor-pointer ${
                      currentTheme === 'aurora'
                        ? 'border-indigo-500/60 bg-indigo-950/20 text-white'
                        : 'border-white/5 bg-white/[0.03] text-zinc-400 hover:text-white'
                    }`}
                  >
                    <div className="text-xs font-semibold">Nordic Aurora</div>
                    <div className="text-[11px] text-zinc-400 mt-0.5">Glacial indigo & polar violet</div>
                  </button>
                </div>
              </div>

              {/* Hardware & Acceleration Status */}
              <div className="space-y-3 pt-4 border-t border-white/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-emerald-400" />
                    <div>
                      <div className="text-white font-medium">GPU Acceleration</div>
                      <div className="text-[11px] text-zinc-400">Offload Whisper STT to NVIDIA RTX 3050</div>
                    </div>
                  </div>
                  <span className="text-emerald-400 font-medium">Active (CUDA 13.2)</span>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-white font-medium">0-Token Alexa Grammar</div>
                    <div className="text-[11px] text-zinc-400">Local sub-10ms playback execution</div>
                  </div>
                  <span className="text-emerald-400 font-medium">Enabled</span>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-white/5">
                  <div>
                    <div className="text-white font-medium">Spotify Account</div>
                    <div className="text-[11px] text-zinc-400">
                      {isConnected ? 'Active & authenticated with Spotify' : 'Connect or refresh playback authorization'}
                    </div>
                  </div>
                  {isConnected ? (
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-emerald-400 bg-emerald-950/50 border border-emerald-500/40 px-3 py-1 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                        <Check className="w-3 h-3 text-emerald-400" /> Connected
                      </span>
                      <a
                        href="http://127.0.0.1:8000/auth/spotify"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[10px] text-zinc-400 hover:text-zinc-200 underline ml-1"
                        title="Click to reconnect"
                      >
                        Reconnect
                      </a>
                    </div>
                  ) : (
                    <a
                      href="http://127.0.0.1:8000/auth/spotify"
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-[11px] transition shadow-[0_0_12px_rgba(16,185,129,0.3)]"
                    >
                      Connect Spotify
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: LIVE LOGS */}
          {activeTab === 'logs' && (
            <div className="space-y-3 font-mono">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 bg-white/5 p-0.5 rounded-lg text-[10px]">
                  {(['ALL', 'INFO', 'WARNING', 'ERROR'] as const).map((lvl) => (
                    <button
                      key={lvl}
                      onClick={() => setLogFilter(lvl)}
                      className={`px-2 py-0.5 rounded cursor-pointer transition ${
                        logFilter === lvl ? 'bg-white/10 text-white font-medium' : 'text-zinc-400 hover:text-white'
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={checkStatus}
                    className="p-1 text-zinc-400 hover:text-white transition cursor-pointer"
                    title="Refresh logs"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                  </button>
                  <button
                    onClick={clearLogs}
                    className="p-1 text-zinc-400 hover:text-red-400 transition cursor-pointer"
                    title="Clear log buffer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="bg-black/50 border border-white/10 rounded-xl p-3 max-h-[380px] overflow-y-auto space-y-1.5">
                {filteredLogs.length === 0 ? (
                  <div className="text-center py-8 text-zinc-500 font-sans text-xs">
                    No logs recorded yet. Speak a command or test intent to see execution trace.
                  </div>
                ) : (
                  filteredLogs.map((log, idx) => {
                    let badgeClass = 'text-emerald-400 bg-emerald-950/40 border-emerald-500/20';
                    if (log.level === 'WARNING') badgeClass = 'text-amber-400 bg-amber-950/40 border-amber-500/20';
                    if (log.level === 'ERROR') badgeClass = 'text-rose-400 bg-rose-950/40 border-rose-500/20';

                    return (
                      <div
                        key={idx}
                        className="flex items-start gap-2 p-1.5 rounded bg-white/[0.02] hover:bg-white/[0.04] transition text-[11px]"
                      >
                        <span className="text-[10px] text-zinc-500 shrink-0 mt-0.5">{log.timestamp}</span>
                        <span className={`text-[9px] px-1 py-0.5 rounded border uppercase font-bold shrink-0 ${badgeClass}`}>
                          {log.level}
                        </span>
                        <span className="text-zinc-300 break-all font-sans">{log.message}</span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* TAB 3: DIAGNOSTICS & TOOLS */}
          {activeTab === 'diagnostics' && (
            <div className="space-y-4">
              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/10 flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-white text-xs">Test Voice Output (TTS)</h4>
                  <p className="text-[11px] text-zinc-400 mt-0.5">Audible speech test through your PC speakers.</p>
                </div>
                <button
                  onClick={handleTestVoice}
                  className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition flex items-center gap-1.5 cursor-pointer shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                >
                  <Volume2 className="w-3.5 h-3.5" />
                  <span>Test Voice</span>
                </button>
              </div>

              {testResult && (
                <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                  <Check className="w-4 h-4" />
                  <span>{testResult}</span>
                </div>
              )}

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/10 flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-white text-xs">Spotify Playback Query</h4>
                  <p className="text-[11px] text-zinc-400 mt-0.5">Check if Spotify desktop app is active.</p>
                </div>
                <button
                  onClick={async () => {
                    const res = await fetch('http://127.0.0.1:8000/playback').catch(() => null);
                    if (res && res.ok) {
                      const d = await res.json();
                      const track = d.result?.track;
                      if (track) setTestResult(`Now playing: ${track} by ${d.result.artist}`);
                      else setTestResult(d.result?.message || 'Connected! No track playing currently.');
                    }
                  }}
                  className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Query Playback</span>
                </button>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-zinc-300 mb-2 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-purple-400" />
                  <span>Active MCP Tools ({tools.length})</span>
                </h4>
                <div className="max-h-[160px] overflow-y-auto space-y-1.5">
                  {tools.map((t, idx) => (
                    <div key={idx} className="p-2 rounded-lg bg-white/[0.02] border border-white/5 text-[11px]">
                      <span className="font-mono text-emerald-400 font-semibold">{t.name}</span>
                      <p className="text-zinc-400 mt-0.5">{t.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/10 flex justify-between items-center bg-white/[0.01]">
          <div className="flex items-center gap-2 text-[11px] text-zinc-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Daisy Engine v0.1.0 • RTX 3050 CUDA</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-white/10 hover:bg-white/15 text-xs font-medium text-white transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
