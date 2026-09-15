import React, { useState, useEffect } from 'react';
import { 
  X, 
  LayoutGrid,
  Mic, 
  Sparkles, 
  Music,
  Cpu,
  Palette,
  Activity,
  Volume2, 
  Trash2,
  ExternalLink,
  Plus,
  Play,
  RotateCcw,
  Copy,
  Check
} from 'lucide-react';
import type { ThemeType, OrbStateType } from './FloatingOrb';

export interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme: ThemeType;
  onSelectTheme: (theme: ThemeType) => void;
  onSpeak?: (text: string) => void;
  assistantName: string;
  onUpdateAssistantName: (newName: string) => void;
  orbState?: OrbStateType;
  onSetOrbState?: (st: OrbStateType) => void;
  onRunVoiceFlow?: (cmd: string, defaultTts: string, isGemini?: boolean) => void;
  isAmbientListening?: boolean;
  onToggleAmbientListening?: () => void;
  onResetPosition?: () => void;
  onOpenDashboard?: () => void;
  appMode?: 'window' | 'floating' | 'dashboard';
  onSetAppMode?: (mode: 'window' | 'floating' | 'dashboard') => void;
}

interface CustomTool {
  name: string;
  description: string;
  type: 'command' | 'http';
  command?: string;
  url?: string;
  method?: string;
  trigger_phrases?: string[];
  enabled: boolean;
}

// Modern Smooth Purple Toggle Switch matching screenshot
function ToggleSwitch({
  checked,
  onChange,
  disabled = false,
}: {
  checked: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
        checked ? 'bg-[#8b5cf6]' : 'bg-zinc-800'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  );
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentTheme,
  onSelectTheme,
  onSpeak,
  assistantName,
  onUpdateAssistantName,
  isAmbientListening = true,
  onToggleAmbientListening,
  onResetPosition,
  onOpenDashboard,
  appMode = 'floating',
  onSetAppMode,
}) => {
  type TabType = 'general' | 'voice' | 'ai' | 'spotify' | 'mcp' | 'appearance' | 'diagnostics';
  const [activeTab, setActiveTab] = useState<TabType>('general');

  // General Settings State
  const [launchAtStartup, setLaunchAtStartup] = useState<boolean>(() => {
    return localStorage.getItem('daisy_launch_startup') === 'true';
  });
  const [alwaysOnTop, setAlwaysOnTop] = useState<boolean>(() => {
    return localStorage.getItem('daisy_always_on_top') !== 'false';
  });
  const [globalHotkey, setGlobalHotkey] = useState<boolean>(() => {
    return localStorage.getItem('daisy_global_hotkey') !== 'false';
  });

  // Assistant Name State
  const [tempName, setTempName] = useState<string>(assistantName);
  const [nameSavedToast, setNameSavedToast] = useState<boolean>(false);

  // Status & Telemetry State
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [activeDevice, setActiveDevice] = useState<string>('Spotify Desktop');

  // Voice configuration state
  const [voiceProvider, setVoiceProvider] = useState<string>('edge-tts');
  const [voiceSelected, setVoiceSelected] = useState<string>('en-US-JennyNeural');
  const [edgeVoices, setEdgeVoices] = useState<Array<{ name: string; label: string }>>([]);
  const [windowsVoiceSelected, setWindowsVoiceSelected] = useState<string>('Microsoft Zira Desktop');
  const [windowsVoices, setWindowsVoices] = useState<Array<{ name: string; label: string }>>([]);
  const [isSavingVoice, setIsSavingVoice] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  // AI Configuration State
  const [aiModel, setAiModel] = useState<string>('gemini-2.0-flash');
  const [streamAudio, setStreamAudio] = useState<boolean>(true);
  const [fastpathEnabled, setFastpathEnabled] = useState<boolean>(true);

  // Custom Tools State
  const [customTools, setCustomTools] = useState<CustomTool[]>([]);
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [newToolName, setNewToolName] = useState<string>('');
  const [newToolType, setNewToolType] = useState<'command' | 'http'>('command');
  const [newToolTarget, setNewToolTarget] = useState<string>('');
  const [newToolDesc, setNewToolDesc] = useState<string>('');
  const [newToolTriggers, setNewToolTriggers] = useState<string>('');
  const [toolError, setToolError] = useState<string | null>(null);
  const [testingToolName, setTestingToolName] = useState<string | null>(null);
  const [customTestOutput, setCustomTestOutput] = useState<{ name: string; output: any; latency?: number } | null>(null);

  // Logs State
  const [logs, setLogs] = useState<Array<{ timestamp: string; level: string; name: string; message: string }>>([]);
  const [copiedLogs, setCopiedLogs] = useState<boolean>(false);

  const handleCopyLogs = () => {
    if (!logs || logs.length === 0) {
      navigator.clipboard.writeText("[DAISY] System idle and healthy. No recent error logs.");
    } else {
      const text = logs
        .map(
          (l) =>
            `[${l.timestamp || new Date().toISOString()}] [${l.level || 'INFO'}] ${l.name ? `[${l.name}] ` : ''}${l.message}`
        )
        .join('\n');
      navigator.clipboard.writeText(text);
    }
    setCopiedLogs(true);
    setTimeout(() => setCopiedLogs(false), 2000);
  };

  const [prevAssistantName, setPrevAssistantName] = useState(assistantName);
  if (assistantName !== prevAssistantName) {
    setPrevAssistantName(assistantName);
    setTempName(assistantName);
  }

  const handleSaveName = () => {
    const trimmed = tempName.trim();
    if (trimmed) {
      onUpdateAssistantName(trimmed);
      setNameSavedToast(true);
      setTimeout(() => setNameSavedToast(false), 2500);
    }
  };

  const handleToggleStartup = () => {
    const next = !launchAtStartup;
    setLaunchAtStartup(next);
    localStorage.setItem('daisy_launch_startup', String(next));
  };

  const handleToggleAlwaysOnTop = () => {
    const next = !alwaysOnTop;
    setAlwaysOnTop(next);
    localStorage.setItem('daisy_always_on_top', String(next));
  };

  const handleToggleGlobalHotkey = () => {
    const next = !globalHotkey;
    setGlobalHotkey(next);
    localStorage.setItem('daisy_global_hotkey', String(next));
  };

  const fetchCustomTools = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/mcp/custom');
      if (res.ok) {
        const data = await res.json();
        setCustomTools(data.tools || []);
      }
    } catch (e) {
      console.warn('Could not fetch custom tools:', e);
    }
  };

  const checkStatus = async () => {
    try {
      const [authRes, logsRes, voiceCfgRes, pbRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/auth/status').catch(() => null),
        fetch('http://127.0.0.1:8000/logs').catch(() => null),
        fetch('http://127.0.0.1:8000/voice/config').catch(() => null),
        fetch('http://127.0.0.1:8000/playback').catch(() => null),
      ]);

      if (authRes && authRes.ok) {
        const d = await authRes.json();
        setIsConnected(Boolean(d.spotify_connected));
      }
      if (pbRes && pbRes.ok) {
        const pb = await pbRes.json();
        if (pb?.result?.device_name) {
          setActiveDevice(pb.result.device_name);
        }
      }
      if (logsRes && logsRes.ok) {
        const d = await logsRes.json();
        setLogs(d.logs || []);
      }
      if (voiceCfgRes && voiceCfgRes.ok) {
        const d = await voiceCfgRes.json();
        setVoiceProvider(d.provider || 'edge-tts');
        setVoiceSelected(d.voice || 'en-US-JennyNeural');
        setWindowsVoiceSelected(d.windows_voice || 'Microsoft Zira Desktop');
        setEdgeVoices(d.edge_voices || []);
        setWindowsVoices(d.windows_voices || []);
      }
      await fetchCustomTools();
    } catch {
      setIsConnected(false);
    }
  };

  const saveVoiceConfig = async (updates: Record<string, string>) => {
    setIsSavingVoice(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/voice/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const d = await res.json();
        setVoiceProvider(d.provider || voiceProvider);
        setVoiceSelected(d.voice || voiceSelected);
        setWindowsVoiceSelected(d.windows_voice || windowsVoiceSelected);
      }
    } catch (e) {
      console.warn('Failed saving voice config:', e);
    } finally {
      setIsSavingVoice(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    const initialTimer = window.setTimeout(() => {
      checkStatus();
    }, 0);
    const interval = window.setInterval(checkStatus, 3500);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(interval);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestVoice = async () => {
    const text = "Hi! I'm Daisy, your desktop voice assistant. Everything sounds great!";
    setTestResult("Testing voice...");
    if (onSpeak) {
      onSpeak(text);
      setTimeout(() => setTestResult("Voice test played!"), 3000);
    } else {
      setTestResult("No voice client available.");
    }
  };

  const handleAddCustomTool = async (e: React.FormEvent) => {
    e.preventDefault();
    setToolError(null);
    const name = newToolName.trim().toLowerCase().replace(/\s+/g, '_');
    if (!name) {
      setToolError('Tool name is required.');
      return;
    }
    if (!newToolTarget.trim()) {
      setToolError(newToolType === 'command' ? 'Command string is required.' : 'URL is required.');
      return;
    }
    const triggers = newToolTriggers
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const payload: CustomTool = {
      name,
      description: newToolDesc.trim() || `Custom tool ${name}`,
      type: newToolType,
      command: newToolType === 'command' ? newToolTarget.trim() : undefined,
      url: newToolType === 'http' ? newToolTarget.trim() : undefined,
      method: newToolType === 'http' ? 'GET' : undefined,
      trigger_phrases: triggers,
      enabled: true,
    };

    try {
      const res = await fetch('http://127.0.0.1:8000/mcp/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setNewToolName('');
        setNewToolTarget('');
        setNewToolDesc('');
        setNewToolTriggers('');
        setShowAddForm(false);
        fetchCustomTools();
      } else {
        const data = await res.json();
        setToolError(data.detail || 'Failed to save tool.');
      }
    } catch {
      setToolError('Network error connecting to backend.');
    }
  };

  const handleDeleteCustomTool = async (name: string) => {
    try {
      await fetch(`http://127.0.0.1:8000/mcp/custom/${name}`, { method: 'DELETE' });
      fetchCustomTools();
    } catch (err) {
      console.warn('Failed to delete custom tool:', err);
    }
  };

  const handleTestCustomTool = async (name: string) => {
    setTestingToolName(name);
    setCustomTestOutput(null);
    try {
      const res = await fetch('http://127.0.0.1:8000/mcp/custom/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, args: {} }),
      });
      const data = await res.json();
      const output = data.result?.output ?? data.result ?? data.error ?? 'Executed';
      const latency = data.result?.latency_ms;
      setCustomTestOutput({ name, output, latency });
    } catch (err: any) {
      setCustomTestOutput({ name, output: err.message || 'Connection failed.' });
    } finally {
      setTestingToolName(null);
    }
  };

  const NAV_ITEMS = [
    { id: 'general' as TabType, label: 'General', icon: LayoutGrid },
    { id: 'voice' as TabType, label: 'Voice', icon: Mic },
    { id: 'ai' as TabType, label: 'AI', icon: Sparkles },
    { id: 'spotify' as TabType, label: 'Spotify', icon: Music },
    { id: 'mcp' as TabType, label: 'MCP', icon: Cpu },
    { id: 'appearance' as TabType, label: 'Appearance', icon: Palette },
    { id: 'diagnostics' as TabType, label: 'Diagnostics', icon: Activity },
  ];

  return (
    <div className="fixed inset-0 flex items-center justify-center p-4 z-50 select-none bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      
      {/* Exact Card from Screenshot: Rounded-3xl, Dark Obsidian, Crisp Border */}
      <div 
        className="w-[580px] max-w-[95vw] h-[440px] max-h-[90vh] bg-[#0c0e15]/98 border border-white/[0.08] rounded-3xl overflow-hidden shadow-2xl flex flex-col"
        style={{
          boxShadow: '0 24px 60px -12px rgba(0, 0, 0, 0.95), 0 0 0 1px rgba(255, 255, 255, 0.05)',
        }}
      >
        
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-white/[0.01]">
          <div className="flex items-center gap-3">
            {/* 3D Glowing Purple Mini Orb Icon */}
            <div className="relative w-6 h-6 rounded-full flex items-center justify-center">
              <div className="absolute -inset-1 rounded-full bg-purple-500/40 blur-sm pointer-events-none" />
              <div 
                className="relative w-6 h-6 rounded-full border border-purple-300/40 shadow-inner"
                style={{
                  background: 'radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.9) 0%, rgba(139, 92, 246, 0.9) 35%, rgba(76, 29, 149, 0.95) 75%, #0e0720 100%)',
                  boxShadow: '0 0 10px rgba(139, 92, 246, 0.5), inset 0 1px 2px rgba(255, 255, 255, 0.8), inset 0 -3px 6px rgba(0, 0, 0, 0.7)'
                }}
              >
                <div className="absolute top-0.5 left-1 w-3.5 h-1.5 rounded-full bg-white/70 blur-[0.3px] -rotate-30" />
              </div>
            </div>
            <h2 className="text-base font-semibold text-white tracking-tight">Settings</h2>
          </div>

          {/* Circular Dark Close Button */}
          <button 
            onClick={onClose} 
            className="w-7 h-7 rounded-full bg-white/[0.06] hover:bg-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition cursor-pointer"
            title="Close Settings"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Body: Left Sidebar + Right Settings Panel */}
        <div className="flex flex-1 min-h-0 overflow-hidden">
          
          {/* Left Navigation Sidebar */}
          <div className="w-[170px] shrink-0 border-r border-white/[0.06] py-3 flex flex-col justify-between bg-black/20">
            <nav className="space-y-0.5">
              {NAV_ITEMS.map((item) => {
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`relative w-full px-4 py-2.5 flex items-center gap-3 text-xs text-left transition cursor-pointer ${
                      isActive 
                        ? 'text-white font-semibold' 
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    {/* Purple active indicator bar on left edge */}
                    {isActive && (
                      <span className="absolute left-0 top-1 bottom-1 w-1 bg-[#8b5cf6] rounded-r" />
                    )}
                    <item.icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-zinc-400'}`} />
                    <span className="tracking-tight">{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Right Content Panel */}
          <div className="flex-1 p-6 overflow-y-auto space-y-4">
            
            {/* ================= TAB 1: GENERAL (Exact User Screenshot) ================= */}
            {activeTab === 'general' && (
              <div className="space-y-1">
                {/* Row 1: Launch at startup */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Launch at startup</div>
                    <div className="text-xs text-zinc-400 font-normal">Start Daisy when Windows boots</div>
                  </div>
                  <ToggleSwitch checked={launchAtStartup} onChange={handleToggleStartup} />
                </div>

                {/* Row 2: Always on top */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Always on top</div>
                    <div className="text-xs text-zinc-400 font-normal">Float above all other windows</div>
                  </div>
                  <ToggleSwitch checked={alwaysOnTop} onChange={handleToggleAlwaysOnTop} />
                </div>

                {/* Row 3: Global hotkey */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Global hotkey</div>
                    <div className="text-xs text-zinc-400 font-normal">Press Ctrl+Shift+D to activate Daisy</div>
                  </div>
                  <ToggleSwitch checked={globalHotkey} onChange={handleToggleGlobalHotkey} />
                </div>

                {/* Row 4: Floating Desktop Overlay Mode */}
                {onSetAppMode && (
                  <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                    <div className="space-y-0.5 pr-4">
                      <div className="text-sm font-semibold text-white tracking-tight">Floating mode</div>
                      <div className="text-xs text-zinc-400 font-normal">Compact transparent orb on your desktop</div>
                    </div>
                    <ToggleSwitch
                      checked={appMode === 'floating'}
                      onChange={() => onSetAppMode(appMode === 'floating' ? 'window' : 'floating')}
                    />
                  </div>
                )}

                {/* Row 5: Version (Cyan/Teal Monospace Text from Screenshot) */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Version</div>
                    <div className="text-xs text-zinc-400 font-normal">Update available</div>
                  </div>
                  <div className="font-mono text-xs font-semibold text-[#22d3ee] tracking-wide">
                    v0.9.2 → v1.0.0
                  </div>
                </div>

                {/* Row 5: Reset Window Position */}
                {onResetPosition && (
                  <div className="flex items-center justify-between py-3">
                    <div className="space-y-0.5 pr-4">
                      <div className="text-sm font-semibold text-white tracking-tight">Reset window position</div>
                      <div className="text-xs text-zinc-400 font-normal">Snap widget to primary screen center</div>
                    </div>
                    <button
                      onClick={onResetPosition}
                      className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-300 text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
                    >
                      <RotateCcw className="w-3 h-3 text-zinc-400" />
                      <span>Reset</span>
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ================= TAB 2: VOICE ================= */}
            {activeTab === 'voice' && (
              <div className="space-y-1">
                {/* Assistant Wake Word */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Wake word name</div>
                    <div className="text-xs text-zinc-400 font-normal">Call your assistant hands-free</div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      value={tempName}
                      onChange={(e) => setTempName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveName()}
                      placeholder="e.g. Daisy"
                      className="w-24 bg-black/40 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-white font-medium focus:outline-none focus:border-[#8b5cf6]"
                    />
                    <button
                      onClick={handleSaveName}
                      className="px-2.5 py-1 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white font-semibold rounded-lg text-xs transition cursor-pointer"
                    >
                      {nameSavedToast ? 'Saved!' : 'Save'}
                    </button>
                  </div>
                </div>

                {/* Ambient Listening */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Ambient listening</div>
                    <div className="text-xs text-zinc-400 font-normal">Continuously listen for "Hey {assistantName}"</div>
                  </div>
                  <ToggleSwitch 
                    checked={isAmbientListening} 
                    onChange={() => onToggleAmbientListening && onToggleAmbientListening()} 
                  />
                </div>

                {/* Speech Provider */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
                      <span>Speech engine</span>
                      {isSavingVoice && <span className="text-[10px] text-[#a78bfa] animate-pulse">Saving...</span>}
                    </div>
                    <div className="text-xs text-zinc-400 font-normal">Neural Text-to-Speech synthesis</div>
                  </div>
                  <select
                    value={voiceProvider}
                    onChange={(e) => saveVoiceConfig({ provider: e.target.value })}
                    className="bg-black/50 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-zinc-200 focus:outline-none"
                  >
                    <option value="edge-tts">Edge-TTS (Online Neural)</option>
                    <option value="windows">Windows Native (SAPI Offline)</option>
                  </select>
                </div>

                {/* Voice Model */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Voice model</div>
                    <div className="text-xs text-zinc-400 font-normal">Select accent and personality</div>
                  </div>
                  <select
                    value={voiceProvider === 'edge-tts' ? voiceSelected : windowsVoiceSelected}
                    onChange={(e) => {
                      if (voiceProvider === 'edge-tts') {
                        saveVoiceConfig({ voice: e.target.value });
                      } else {
                        saveVoiceConfig({ windows_voice: e.target.value });
                      }
                    }}
                    className="bg-black/50 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-zinc-200 focus:outline-none max-w-[180px] truncate"
                  >
                    {voiceProvider === 'edge-tts' ? (
                      edgeVoices.length > 0 ? (
                        edgeVoices.map((v) => <option key={v.name} value={v.name}>{v.label}</option>)
                      ) : (
                        <option value="en-US-JennyNeural">Jenny (Natural US)</option>
                      )
                    ) : (
                      windowsVoices.length > 0 ? (
                        windowsVoices.map((v) => <option key={v.name} value={v.name}>{v.label}</option>)
                      ) : (
                        <option value="Microsoft Zira Desktop">Zira Desktop</option>
                      )
                    )}
                  </select>
                </div>

                {/* Test Voice */}
                <div className="flex items-center justify-between py-3">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Test voice output</div>
                    <div className="text-xs text-zinc-400 font-normal">{testResult || "Listen to a sample phrase"}</div>
                  </div>
                  <button
                    onClick={handleTestVoice}
                    className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white text-xs font-medium transition cursor-pointer flex items-center gap-1.5"
                  >
                    <Volume2 className="w-3.5 h-3.5 text-[#a78bfa]" />
                    <span>Play Sample</span>
                  </button>
                </div>
              </div>
            )}

            {/* ================= TAB 3: AI ================= */}
            {activeTab === 'ai' && (
              <div className="space-y-1">
                {/* AI Model */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Agent model</div>
                    <div className="text-xs text-zinc-400 font-normal">Gemini multimodal intelligence</div>
                  </div>
                  <select
                    value={aiModel}
                    onChange={(e) => setAiModel(e.target.value)}
                    className="bg-black/50 border border-white/15 rounded-lg px-2.5 py-1 text-xs text-zinc-200 focus:outline-none"
                  >
                    <option value="gemini-2.0-flash">Gemini 2.0 Flash (Fastest)</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep reasoning)</option>
                  </select>
                </div>

                {/* Streaming Audio */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Streaming audio response</div>
                    <div className="text-xs text-zinc-400 font-normal">Synthesize voice as text generates</div>
                  </div>
                  <ToggleSwitch checked={streamAudio} onChange={() => setStreamAudio(!streamAudio)} />
                </div>

                {/* Fastpath Intent Grammar */}
                <div className="flex items-center justify-between py-3">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Fastpath intent execution</div>
                    <div className="text-xs text-zinc-400 font-normal">Zero-latency local Spotify & system grammar</div>
                  </div>
                  <ToggleSwitch checked={fastpathEnabled} onChange={() => setFastpathEnabled(!fastpathEnabled)} />
                </div>
              </div>
            )}

            {/* ================= TAB 4: SPOTIFY ================= */}
            {activeTab === 'spotify' && (
              <div className="space-y-1">
                {/* Connection Status */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Spotify connection</div>
                    <div className="text-xs text-zinc-400 font-normal">
                      {isConnected ? 'Authorized and connected to Spotify Web API' : 'Not connected'}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-[11px] text-emerald-400 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>{isConnected ? 'Connected' : 'Offline'}</span>
                  </div>
                </div>

                {/* Active Device */}
                <div className="flex items-center justify-between py-3 border-b border-white/[0.04]">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Active playback device</div>
                    <div className="text-xs text-zinc-400 font-normal">Destination for music playback</div>
                  </div>
                  <span className="text-xs font-mono text-zinc-300 bg-white/5 px-2 py-1 rounded-lg border border-white/10">
                    {activeDevice}
                  </span>
                </div>

                {/* Reconnect / Authenticate */}
                <div className="flex items-center justify-between py-3">
                  <div className="space-y-0.5 pr-4">
                    <div className="text-sm font-semibold text-white tracking-tight">Authorize Spotify</div>
                    <div className="text-xs text-zinc-400 font-normal">Refresh OAuth token credentials</div>
                  </div>
                  <button
                    onClick={() => window.open('http://127.0.0.1:8000/auth/login', '_blank')}
                    className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-semibold transition cursor-pointer flex items-center gap-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Login</span>
                  </button>
                </div>
              </div>
            )}

            {/* ================= TAB 5: MCP ================= */}
            {activeTab === 'mcp' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-white tracking-tight">Custom MCP Tools</div>
                    <div className="text-xs text-zinc-400 font-normal">Extend Daisy with custom scripts and webhooks</div>
                  </div>
                  <button
                    onClick={() => setShowAddForm(!showAddForm)}
                    className="px-2.5 py-1 rounded-lg bg-[#8b5cf6]/20 hover:bg-[#8b5cf6]/30 text-[#c4b5fd] border border-[#8b5cf6]/30 text-xs font-semibold transition cursor-pointer flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Tool</span>
                  </button>
                </div>

                {showAddForm && (
                  <form onSubmit={handleAddCustomTool} className="p-3.5 rounded-xl bg-black/40 border border-white/10 space-y-2.5 text-xs">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Tool Name (e.g. open_terminal)"
                        value={newToolName}
                        onChange={(e) => setNewToolName(e.target.value)}
                        className="flex-1 bg-black/50 border border-white/15 rounded-lg px-2.5 py-1 text-white placeholder-zinc-500 focus:outline-none"
                      />
                      <select
                        value={newToolType}
                        onChange={(e) => setNewToolType(e.target.value as any)}
                        className="bg-black/50 border border-white/15 rounded-lg px-2 text-zinc-200 focus:outline-none"
                      >
                        <option value="command">Shell Command</option>
                        <option value="http">HTTP Webhook</option>
                      </select>
                    </div>
                    <input
                      type="text"
                      placeholder={newToolType === 'command' ? 'Command (e.g. wt.exe)' : 'URL (e.g. http://localhost:5000/hook)'}
                      value={newToolTarget}
                      onChange={(e) => setNewToolTarget(e.target.value)}
                      className="w-full bg-black/50 border border-white/15 rounded-lg px-2.5 py-1 text-white placeholder-zinc-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Trigger phrases (e.g. launch terminal, open console)"
                      value={newToolTriggers}
                      onChange={(e) => setNewToolTriggers(e.target.value)}
                      className="w-full bg-black/50 border border-white/15 rounded-lg px-2.5 py-1 text-white placeholder-zinc-500 focus:outline-none"
                    />
                    {toolError && <p className="text-rose-400 text-[11px]">{toolError}</p>}
                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => setShowAddForm(false)}
                        className="px-2.5 py-1 rounded-lg text-zinc-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-3 py-1 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white font-semibold rounded-lg"
                      >
                        Save Tool
                      </button>
                    </div>
                  </form>
                )}

                {/* Tool List */}
                <div className="space-y-2">
                  {customTools.length > 0 ? (
                    customTools.map((tool) => (
                      <div key={tool.name} className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/10 text-xs">
                        <div>
                          <div className="font-semibold text-white flex items-center gap-1.5">
                            <span>{tool.name}</span>
                            <span className="font-mono text-[9px] bg-white/10 px-1.5 py-0.5 rounded text-zinc-300">{tool.type}</span>
                          </div>
                          <div className="text-[11px] text-zinc-400 mt-0.5">{tool.description}</div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleTestCustomTool(tool.name)}
                            disabled={testingToolName === tool.name}
                            className="p-1 text-zinc-400 hover:text-emerald-400 transition cursor-pointer"
                            title="Test Tool"
                          >
                            <Play className={`w-3.5 h-3.5 ${testingToolName === tool.name ? 'animate-pulse text-[#a78bfa]' : ''}`} />
                          </button>
                          <button
                            onClick={() => handleDeleteCustomTool(tool.name)}
                            className="p-1 text-zinc-400 hover:text-rose-400 transition cursor-pointer"
                            title="Delete Tool"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-4 rounded-xl border border-dashed border-white/10 text-center text-xs text-zinc-500">
                      No custom MCP tools added yet
                    </div>
                  )}
                </div>

                {/* Test Output Box */}
                {customTestOutput && (
                  <div className="p-3 rounded-xl bg-black/60 border border-purple-500/30 text-xs space-y-1">
                    <div className="flex items-center justify-between text-[#a78bfa] font-semibold">
                      <span>Test Output: {customTestOutput.name}</span>
                      {customTestOutput.latency !== undefined && (
                        <span className="text-[10px] text-zinc-400 font-mono">{customTestOutput.latency}ms</span>
                      )}
                    </div>
                    <pre className="text-[11px] text-zinc-300 font-mono overflow-x-auto whitespace-pre-wrap">
                      {typeof customTestOutput.output === 'object' 
                        ? JSON.stringify(customTestOutput.output, null, 2)
                        : String(customTestOutput.output)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* ================= TAB 6: APPEARANCE ================= */}
            {activeTab === 'appearance' && (
              <div className="space-y-4">
                <div>
                  <div className="text-sm font-semibold text-white tracking-tight mb-2">Visual Theme</div>
                  <div className="grid grid-cols-2 gap-2.5">
                    {/* Glassmorphism */}
                    <div
                      onClick={() => onSelectTheme('glassmorphism')}
                      className={`p-3 rounded-2xl border cursor-pointer transition flex flex-col gap-1.5 ${
                        currentTheme === 'glassmorphism'
                          ? 'border-[#1db954] bg-[#1db954]/10 shadow-[0_0_12px_rgba(29,185,84,0.25)]'
                          : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Glassmorphism</span>
                        <span className="w-2.5 h-2.5 rounded-full bg-[#1db954]" />
                      </div>
                      <span className="text-[11px] text-zinc-400">Spotify neon green & glass</span>
                    </div>

                    {/* Sleek */}
                    <div
                      onClick={() => onSelectTheme('sleek')}
                      className={`p-3 rounded-2xl border cursor-pointer transition flex flex-col gap-1.5 ${
                        currentTheme === 'sleek'
                          ? 'border-white bg-white/10 shadow-[0_0_12px_rgba(255,255,255,0.25)]'
                          : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Sleek</span>
                        <span className="w-2.5 h-2.5 rounded-full bg-zinc-200" />
                      </div>
                      <span className="text-[11px] text-zinc-400">Monochrome white & obsidian</span>
                    </div>

                    {/* Cyberpunk */}
                    <div
                      onClick={() => onSelectTheme('cyberpunk')}
                      className={`p-3 rounded-2xl border cursor-pointer transition flex flex-col gap-1.5 ${
                        currentTheme === 'cyberpunk'
                          ? 'border-[#ec4899] bg-[#ec4899]/10 shadow-[0_0_12px_rgba(236,72,153,0.25)]'
                          : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Cyberpunk</span>
                        <span className="w-2.5 h-2.5 rounded-full bg-[#ec4899]" />
                      </div>
                      <span className="text-[11px] text-zinc-400">Neon cyan & laser magenta</span>
                    </div>

                    {/* Aurora */}
                    <div
                      onClick={() => onSelectTheme('aurora')}
                      className={`p-3 rounded-2xl border cursor-pointer transition flex flex-col gap-1.5 ${
                        currentTheme === 'aurora'
                          ? 'border-[#a78bfa] bg-[#a78bfa]/10 shadow-[0_0_12px_rgba(167,139,250,0.25)]'
                          : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white">Aurora</span>
                        <span className="w-2.5 h-2.5 rounded-full bg-[#a78bfa]" />
                      </div>
                      <span className="text-[11px] text-zinc-400">Northern lights deep indigo</span>
                    </div>
                  </div>
                </div>

                {/* Display Mode */}
                {onSetAppMode && (
                  <div className="flex items-center justify-between py-3 border-t border-white/[0.04]">
                    <div className="space-y-0.5 pr-4">
                      <div className="text-sm font-semibold text-white tracking-tight">Display mode</div>
                      <div className="text-xs text-zinc-400 font-normal">Switch between window and desktop overlay</div>
                    </div>
                    <div className="flex items-center gap-1 bg-black/40 p-1 rounded-xl border border-white/10">
                      <button
                        onClick={() => onSetAppMode('floating')}
                        className={`px-3 py-1 rounded-lg text-xs font-medium transition cursor-pointer ${
                          appMode === 'floating'
                            ? 'bg-[#8b5cf6] text-white font-semibold'
                            : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                        Floating
                      </button>
                      <button
                        onClick={() => onSetAppMode('window')}
                        className={`px-3 py-1 rounded-lg text-xs font-medium transition cursor-pointer ${
                          appMode === 'window'
                            ? 'bg-[#8b5cf6] text-white font-semibold'
                            : 'text-zinc-400 hover:text-white'
                        }`}
                      >
                        Window
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ================= TAB 7: DIAGNOSTICS ================= */}
            {activeTab === 'diagnostics' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-white/[0.04]">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-white tracking-tight">Hardware Acceleration</div>
                    <div className="text-xs text-zinc-400">NVIDIA CUDA GPU • CTranslate2 float16</div>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-[10px] text-emerald-400 font-mono">
                    ONLINE
                  </span>
                </div>

                <div className="flex items-center justify-between py-2 border-b border-white/[0.04]">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-white tracking-tight">Full Telemetry Dashboard</div>
                    <div className="text-xs text-zinc-400">Live logs, audio waveforms, and MCP inspection</div>
                  </div>
                  {onOpenDashboard && (
                    <button
                      onClick={() => {
                        onClose();
                        onOpenDashboard();
                      }}
                      className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-zinc-200 text-xs font-medium transition cursor-pointer"
                    >
                      Open Dashboard
                    </button>
                  )}
                </div>

                {/* Quick Log Console */}
                <div className="space-y-2 pt-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">Recent Events</span>
                    <button
                      onClick={handleCopyLogs}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] text-zinc-300 hover:text-white transition cursor-pointer"
                      title="Copy all logs to clipboard"
                    >
                      {copiedLogs ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400 font-medium">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 text-zinc-400" />
                          <span>Copy Logs</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="w-full h-28 bg-black/60 rounded-xl border border-white/10 p-2.5 font-mono text-[10px] text-zinc-300 space-y-1.5 overflow-y-auto select-text cursor-text">
                    {logs.length > 0 ? (
                      logs.slice(-15).map((l, i) => (
                        <div key={i} className="leading-relaxed select-text">
                          <span className="text-zinc-500">[{l.timestamp?.split('T')[1]?.slice(0, 8) || 'LOG'}]</span>{' '}
                          <span className={l.level === 'ERROR' ? 'text-rose-400 font-semibold' : l.level === 'WARNING' ? 'text-amber-400 font-semibold' : 'text-emerald-400 font-semibold'}>
                            [{l.level || 'INFO'}]
                          </span>{' '}
                          <span className="text-zinc-300 select-text">{l.message}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-zinc-500 italic py-3 text-center select-none">
                        No recent log events. Daisy backend is running smoothly.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>

      </div>
    </div>
  );
};

export default SettingsModal;
