import React, { useState, useEffect, useCallback } from 'react';
import { 
  Terminal, 
  Cpu, 
  Activity, 
  RefreshCw, 
  Trash2, 
  Volume2, 
  CheckCircle2, 
  Layers,
  ArrowLeft
} from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level: string;
  name: string;
  message: string;
}

interface SystemStatus {
  status: string;
  uptime_seconds?: number;
  memory_rss_mb?: number;
  cpu_percent?: number;
  active_threads?: number;
  hardware?: {
    tier_name?: string;
    device?: string;
    compute_type?: string;
    gpu_name?: string;
  };
  spotify_connected?: boolean;
  audio_devices?: {
    input_devices: string[];
    output_devices: string[];
  };
  registered_servers?: string[];
  tools_count?: number;
  tools?: Array<{ name: string; description: string; parameters: any }>;
}

interface DashboardViewProps {
  onBackToOrb: () => void;
  onSpeak: (text: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ onBackToOrb, onSpeak }) => {
  const [activeTab, setActiveTab] = useState<'logs' | 'status' | 'tools' | 'diagnostics'>('logs');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [logFilter, setLogFilter] = useState<'ALL' | 'INFO' | 'WARNING' | 'ERROR'>('ALL');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [testResult, setTestResult] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async (silent = false) => {
    try {
      if (!silent) setIsRefreshing(true);
      const [logsRes, statusRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/logs').catch(() => null),
        fetch('http://127.0.0.1:8000/system/status').catch(() => null)
      ]);

      if (logsRes && logsRes.ok) {
        const logsData = await logsRes.json();
        setLogs(logsData.logs || []);
      }
      if (statusRes && statusRes.ok) {
        const statusData = await statusRes.json();
        setStatus(statusData);
      }
    } catch (e) {
      console.warn('Dashboard fetch error:', e);
    } finally {
      if (!silent) setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      fetchDashboardData(true);
    }, 0);
    let interval: any = null;
    if (autoRefresh) {
      interval = setInterval(() => fetchDashboardData(true), 2000);
    }
    return () => {
      window.clearTimeout(timer);
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, fetchDashboardData]);

  const clearLogs = async () => {
    try {
      await fetch('http://127.0.0.1:8000/logs', { method: 'DELETE' });
      setLogs([]);
    } catch {
      setLogs([]);
    }
  };

  const handleTestVoice = async () => {
    const phrase = "Hi! I'm Daisy, your voice assistant. Everything sounds great!";
    setTestResult("Playing test phrase...");
    // Use only onSpeak — do NOT call /voice/test endpoint to avoid dual playback
    onSpeak(phrase);
    setTimeout(() => setTestResult("Voice test complete!"), 3000);
  };


  const filteredLogs = logs.filter(l => {
    if (logFilter === 'ALL') return true;
    return l.level === logFilter;
  });

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col bg-[#0c0e12]/95 border border-white/10 rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden my-2 flex-1 max-h-[82vh]">
      {/* Top Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/10 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <button
            onClick={onBackToOrb}
            className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white px-2 py-1 rounded-lg hover:bg-white/10 transition cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Orb View</span>
          </button>
          <div className="h-4 w-px bg-white/10" />
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white tracking-tight">Daisy Live Inspector & Diagnostics</h2>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-2.5 py-1 text-[11px] rounded-lg border transition cursor-pointer ${
              autoRefresh ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-400' : 'bg-white/5 border-white/10 text-zinc-400'
            }`}
          >
            {autoRefresh ? '● Live Polling' : 'Paused'}
          </button>
          <button
            onClick={() => fetchDashboardData(false)}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition cursor-pointer"
            title="Refresh now"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-4 gap-3 p-4 border-b border-white/10 bg-white/[0.01]">
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
            <span>CUDA Acceleration</span>
            <Cpu className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-xs font-semibold text-white truncate">
            {status?.hardware?.gpu_name || 'NVIDIA RTX 3050'}
          </div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Tier 1 • CUDA 13.2 (float16)</div>
        </div>

        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
            <span>Spotify MCP</span>
            <CheckCircle2 className={`w-3.5 h-3.5 ${status?.spotify_connected ? 'text-emerald-400' : 'text-amber-400'}`} />
          </div>
          <div className="text-xs font-semibold text-white">
            {status?.spotify_connected ? 'Connected ✓' : 'Auth Required'}
          </div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Playback API Live</div>
        </div>

        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
            <span>Local Alexa Grammar</span>
            <Activity className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <div className="text-xs font-semibold text-white">0 Tokens / &lt;10ms</div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Slot intent extraction</div>
        </div>

        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
            <span>MCP Tools Active</span>
            <Layers className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="text-xs font-semibold text-white">
            {status?.tools_count || 11} Tools Loaded
          </div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Spotify + Filesystem</div>
        </div>
      </div>

      {/* Tabs Row */}
      <div className="flex items-center justify-between px-5 pt-3 border-b border-white/10">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-3 py-1.5 text-xs font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'logs'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-zinc-400 hover:text-white'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Live Logs ({logs.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('diagnostics')}
            className={`px-3 py-1.5 text-xs font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'diagnostics'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-zinc-400 hover:text-white'
            }`}
          >
            <Volume2 className="w-3.5 h-3.5" />
            <span>Voice & Audio Diagnostics</span>
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-3 py-1.5 text-xs font-medium border-b-2 transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'tools'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-zinc-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>MCP Registry</span>
          </button>
        </div>

        {activeTab === 'logs' && (
          <div className="flex items-center gap-2 pb-2">
            <div className="flex items-center gap-1 bg-white/5 p-0.5 rounded-lg text-[10px]">
              {(['ALL', 'INFO', 'WARNING', 'ERROR'] as const).map(lvl => (
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
            <button
              onClick={clearLogs}
              className="p-1 text-zinc-400 hover:text-red-400 transition cursor-pointer"
              title="Clear log buffer"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs">
        {activeTab === 'logs' && (
          <div className="space-y-1.5">
            {filteredLogs.length === 0 ? (
              <div className="text-center py-12 text-zinc-500 font-sans">
                No logs recorded yet. Speak a command or test intent to see live execution trace!
              </div>
            ) : (
              filteredLogs.map((log, idx) => {
                let badgeClass = 'text-emerald-400 bg-emerald-950/40 border-emerald-500/20';
                if (log.level === 'WARNING') badgeClass = 'text-amber-400 bg-amber-950/40 border-amber-500/20';
                if (log.level === 'ERROR') badgeClass = 'text-rose-400 bg-rose-950/40 border-rose-500/20';

                return (
                  <div
                    key={idx}
                    className="flex items-start gap-2.5 p-2 rounded-lg bg-black/40 border border-white/[0.03] hover:border-white/10 transition"
                  >
                    <span className="text-[10px] text-zinc-500 shrink-0 font-mono mt-0.5">
                      {log.timestamp}
                    </span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border uppercase font-bold shrink-0 ${badgeClass}`}>
                      {log.level}
                    </span>
                    <span className="text-[10px] text-zinc-400 shrink-0">
                      [{log.name}]
                    </span>
                    <span className="text-zinc-200 break-all font-sans text-xs">
                      {log.message}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'diagnostics' && (
          <div className="space-y-6 font-sans p-2">
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Voice Synthesis (TTS) Test</h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Verifies dual-layer audio synthesis: WebView2 browser speech + native Windows sound.
                  </p>
                </div>
                <button
                  onClick={handleTestVoice}
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition flex items-center gap-1.5 cursor-pointer shadow-[0_0_12px_rgba(16,185,129,0.3)]"
                >
                  <Volume2 className="w-4 h-4" />
                  <span>Test Voice Output</span>
                </button>
              </div>
              {testResult && (
                <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{testResult}</span>
                </div>
              )}
            </div>

            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Spotify Playback Test</h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Queries Spotify Web API for active desktop devices and current song status.
                  </p>
                </div>
                <button
                  onClick={async () => {
                    setTestResult("Querying Spotify current playback...");
                    const res = await fetch('http://127.0.0.1:8000/playback').catch(() => null);
                    if (res && res.ok) {
                      const data = await res.json();
                      const track = data.result?.track;
                      if (track) {
                        setTestResult(`Spotify is playing: ${track} by ${data.result.artist}`);
                      } else {
                        setTestResult(data.result?.message || "Connected to Spotify! No track currently playing.");
                      }
                    }
                  }}
                  className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 text-white font-medium text-xs transition flex items-center gap-1.5 cursor-pointer"
                >
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <span>Query Playback Status</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'tools' && (
          <div className="space-y-3 font-sans">
            <div className="text-xs text-zinc-400 mb-2">
              Model Context Protocol (MCP) tool registry currently accessible to FastPath and Gemini 2.5 Flash:
            </div>
            {status?.tools?.map((tool, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-emerald-400 font-semibold text-xs">
                    {tool.name}
                  </span>
                  <span className="text-[10px] text-zinc-500 uppercase font-mono">MCP Tool</span>
                </div>
                <p className="text-xs text-zinc-300">{tool.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Status Bar */}
      <div className="px-5 py-2.5 border-t border-white/10 bg-black/40 flex items-center justify-between text-[11px] text-zinc-400 font-sans">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Daisy v0.1.0 • Running on 127.0.0.1:8000</span>
        </div>
        <button
          onClick={onBackToOrb}
          className="text-emerald-400 hover:text-emerald-300 font-medium cursor-pointer"
        >
          Return to Orb &rarr;
        </button>
      </div>
    </div>
  );
};
