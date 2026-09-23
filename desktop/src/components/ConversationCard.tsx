import React, { useState } from 'react';
import {
  Volume2,
  Copy,
  Check,
  X,
  ExternalLink,
  Sun,
  Cloud,
  CloudRain,
  CloudLightning,
  Snowflake,
  Wind,
  Droplets,
  Search,
  Music,
  Terminal,
  Sparkles,
  Zap,
  PlaySquare,
  Eye,
  Crosshair,
} from 'lucide-react';

export interface ConversationCardData {
  id: string;
  prompt: string;
  source?: string;
  spokenReply?: string;
  displayText?: string;
  cardType?: 'weather' | 'youtube' | 'web' | 'music' | 'tool' | 'answer' | 'vision';
  cardData?: any;
  timestamp: string;
}

interface ConversationCardProps {
  card: ConversationCardData;
  onDismiss: () => void;
  onSpeak?: (text: string) => void;
  onHighlight?: (target: { x: number; y: number; label?: string; width?: number; height?: number }) => void;
  compact?: boolean;
}

export const ConversationCard: React.FC<ConversationCardProps> = ({
  card,
  onDismiss,
  onSpeak,
  onHighlight,
  compact = false,
}) => {
  const [copied, setCopied] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const handleCopy = () => {
    const textToCopy = card.displayText || card.spokenReply || card.prompt;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleReplaySpeak = () => {
    if (onSpeak && card.spokenReply) {
      setIsPlayingAudio(true);
      onSpeak(card.spokenReply);
      setTimeout(() => setIsPlayingAudio(false), 3000);
    }
  };

  const isFastPath = card.source?.includes('FASTPATH');
  const cardType = card.cardType || 'answer';

  // Simple, safe zero-dependency Markdown line formatter
  const renderMarkdown = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n');
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    const elements: React.ReactNode[] = [];

    lines.forEach((line, idx) => {
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          // Close code block
          const codeText = codeBlockContent.join('\n');
          elements.push(
            <div key={`code-${idx}`} className="my-2 p-3 bg-black/40 border border-white/10 rounded-xl overflow-x-auto text-[11px] font-mono text-emerald-300">
              <pre>{codeText}</pre>
            </div>
          );
          codeBlockContent = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        return;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        return;
      }

      const trimmed = line.trim();
      if (!trimmed) {
        elements.push(<div key={`sp-${idx}`} className="h-1.5" />);
        return;
      }

      // Headings
      if (trimmed.startsWith('### ')) {
        elements.push(
          <h4 key={`h3-${idx}`} className="text-xs font-semibold text-white mt-2 mb-1 flex items-center gap-1.5">
            {trimmed.slice(4)}
          </h4>
        );
        return;
      }
      if (trimmed.startsWith('## ')) {
        elements.push(
          <h3 key={`h2-${idx}`} className="text-sm font-bold text-white mt-2.5 mb-1">
            {trimmed.slice(3)}
          </h3>
        );
        return;
      }
      if (trimmed.startsWith('# ')) {
        elements.push(
          <h2 key={`h1-${idx}`} className="text-sm font-bold text-emerald-400 mt-2 mb-1">
            {trimmed.slice(2)}
          </h2>
        );
        return;
      }

      // Bullet points
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const itemContent = trimmed.slice(2);
        elements.push(
          <div key={`li-${idx}`} className="flex items-start gap-2 text-xs text-zinc-300 ml-1.5 my-0.5">
            <span className="text-emerald-400 font-bold mt-0.5">•</span>
            <span>{formatInlineMarkdown(itemContent)}</span>
          </div>
        );
        return;
      }

      // Standard paragraph
      elements.push(
        <p key={`p-${idx}`} className="text-xs text-zinc-300 leading-relaxed my-0.5">
          {formatInlineMarkdown(trimmed)}
        </p>
      );
    });

    return elements;
  };

  // Inline bold and code tag formatter
  const formatInlineMarkdown = (str: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let remaining = str;
    let keyIdx = 0;

    // Split on bold **bold** or inline code `code`
    const regex = /(\*\*.*?\*\*|`.*?`)/g;
    const tokens = remaining.split(regex);

    tokens.forEach((tok) => {
      if (tok.startsWith('**') && tok.endsWith('**')) {
        parts.push(
          <strong key={`b-${keyIdx++}`} className="font-semibold text-white">
            {tok.slice(2, -2)}
          </strong>
        );
      } else if (tok.startsWith('`') && tok.endsWith('`')) {
        parts.push(
          <code key={`c-${keyIdx++}`} className="px-1.5 py-0.5 rounded bg-white/10 text-emerald-300 font-mono text-[10px]">
            {tok.slice(1, -1)}
          </code>
        );
      } else {
        parts.push(tok);
      }
    });

    return parts;
  };

  // Weather Condition Icon selector
  const renderWeatherIcon = (iconName: string) => {
    switch (iconName) {
      case 'rain':
        return <CloudRain className="w-8 h-8 text-sky-400 animate-bounce" />;
      case 'thunderstorm':
        return <CloudLightning className="w-8 h-8 text-amber-400 animate-pulse" />;
      case 'snow':
        return <Snowflake className="w-8 h-8 text-cyan-200" />;
      case 'cloudy':
      case 'partly_cloudy':
        return <Cloud className="w-8 h-8 text-zinc-300" />;
      default:
        return <Sun className="w-8 h-8 text-amber-400 animate-spin-slow" />;
    }
  };

  return (
    <div
      className={`w-full rounded-2xl border transition-all select-text shadow-2xl ${
        compact
          ? 'bg-[#0b0e17]/95 border-white/10 p-3 backdrop-blur-2xl text-xs'
          : 'bg-[#0b0e17]/90 border-white/[0.12] p-4 backdrop-blur-2xl'
      }`}
    >
      {/* Card Header Bar */}
      <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-white/[0.08]">
        <div className="flex items-center gap-2 overflow-hidden">
          {/* Badge: FastPath vs Gemini */}
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center gap-1 shrink-0 ${
              isFastPath
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            }`}
          >
            {isFastPath ? <Zap className="w-2.5 h-2.5" /> : <Sparkles className="w-2.5 h-2.5" />}
            <span>{isFastPath ? 'FastPath (0ms)' : 'Gemini 2.5'}</span>
          </span>

          {/* User query pill */}
          <span className="text-zinc-400 text-[11px] truncate italic">
            "{card.prompt}"
          </span>
        </div>

        {/* Action controls */}
        <div className="flex items-center gap-1.5 shrink-0">
          {card.spokenReply && onSpeak && (
            <button
              onClick={handleReplaySpeak}
              className={`p-1.5 rounded-lg border transition cursor-pointer ${
                isPlayingAudio
                  ? 'bg-emerald-500/30 border-emerald-500 text-emerald-300'
                  : 'bg-white/5 border-white/10 text-zinc-400 hover:text-white hover:bg-white/10'
              }`}
              title="Listen again"
            >
              <Volume2 className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-400 hover:text-white transition cursor-pointer"
            title="Copy answer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={onDismiss}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-red-500/20 border border-white/10 text-zinc-400 hover:text-red-300 transition cursor-pointer"
            title="Dismiss card"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Card Body - Varied by Card Type */}

      {/* 1. Live Weather Widget */}
      {cardType === 'weather' && card.cardData && (
        <div className="p-3.5 rounded-xl bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {renderWeatherIcon(card.cardData.icon)}
              <div>
                <div className="text-2xl font-bold text-white tracking-tight">
                  {card.cardData.temp_c}°C
                  <span className="text-xs font-normal text-zinc-400 ml-2">
                    {card.cardData.temp_f}°F
                  </span>
                </div>
                <div className="text-xs font-medium text-emerald-400">
                  {card.cardData.condition}
                </div>
              </div>
            </div>

            <div className="text-right">
              <div className="text-xs font-semibold text-white">
                {card.cardData.location}
              </div>
              <div className="text-[10px] text-zinc-400">
                {card.cardData.region ? `${card.cardData.region}, ` : ''}{card.cardData.country}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 mt-3 pt-2.5 border-t border-white/10 text-center">
            <div className="p-1.5 rounded-lg bg-black/20">
              <div className="text-[10px] text-zinc-400 flex items-center justify-center gap-1">
                <span>Feels Like</span>
              </div>
              <div className="text-xs font-semibold text-white mt-0.5">
                {card.cardData.feels_like_c}°C
              </div>
            </div>

            <div className="p-1.5 rounded-lg bg-black/20">
              <div className="text-[10px] text-zinc-400 flex items-center justify-center gap-1">
                <Droplets className="w-2.5 h-2.5 text-sky-400" />
                <span>Humidity</span>
              </div>
              <div className="text-xs font-semibold text-white mt-0.5">
                {card.cardData.humidity}%
              </div>
            </div>

            <div className="p-1.5 rounded-lg bg-black/20">
              <div className="text-[10px] text-zinc-400 flex items-center justify-center gap-1">
                <Wind className="w-2.5 h-2.5 text-emerald-400" />
                <span>Wind</span>
              </div>
              <div className="text-xs font-semibold text-white mt-0.5">
                {card.cardData.wind_speed_kmh} km/h
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. YouTube Search Widget */}
      {cardType === 'youtube' && (
        <div className="p-3.5 rounded-xl bg-gradient-to-br from-red-950/20 to-black/40 border border-red-500/20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400">
              <PlaySquare className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                <span>YouTube Search</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 font-mono">Opened</span>
              </div>
              <div className="text-xs text-zinc-300 mt-0.5">
                "{card.cardData?.query || card.prompt}"
              </div>
            </div>
          </div>

          {card.cardData?.url && (
            <a
              href={card.cardData.url}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-200 text-xs font-medium transition flex items-center gap-1.5 cursor-pointer"
            >
              <span>View</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      )}

      {/* 3. Google / Web Search Widget */}
      {cardType === 'web' && (
        <div className="p-3.5 rounded-xl bg-gradient-to-br from-sky-950/20 to-black/40 border border-sky-500/20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <Search className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                <span>Google Web Search</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono">Opened</span>
              </div>
              <div className="text-xs text-zinc-300 mt-0.5">
                "{card.cardData?.query || card.prompt}"
              </div>
            </div>
          </div>

          {card.cardData?.url && (
            <a
              href={card.cardData.url}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/30 text-sky-200 text-xs font-medium transition flex items-center gap-1.5 cursor-pointer"
            >
              <span>View</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      )}

      {/* 4. Spotify Music Widget */}
      {cardType === 'music' && card.cardData && (
        <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-950/20 to-black/40 border border-emerald-500/20 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-900/30 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Music className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-white truncate">
              {card.cardData.track || 'Spotify Playback'}
            </div>
            <div className="text-[11px] text-zinc-400 truncate">
              {card.cardData.artist || 'Active Track'}
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            <span className="w-1 h-3 bg-emerald-400 rounded-full animate-pulse" />
            <span className="w-1 h-4 bg-emerald-400 rounded-full animate-pulse delay-75" />
            <span className="w-1 h-2 bg-emerald-400 rounded-full animate-pulse delay-150" />
          </div>
        </div>
      )}

      {/* 5. Tool Execution Badge */}
      {cardType === 'tool' && (
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10 flex items-center gap-3">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <span className="text-xs text-zinc-200 font-mono">
            {card.displayText || 'Tool command executed successfully.'}
          </span>
        </div>
      )}

      {/* 6. Screen Vision & UI Guidance Widget (HeyClicky style) */}
      {cardType === 'vision' && (
        <div className="space-y-2.5">
          {card.cardData?.preview_url && (
            <div className="relative group rounded-xl overflow-hidden border border-white/15 bg-black/40 shadow-inner max-h-[220px]">
              <img
                src={card.cardData.preview_url}
                alt="Captured Screen"
                className="w-full h-auto object-cover opacity-90 group-hover:opacity-100 transition-opacity"
              />
              <div className="absolute top-2 left-2 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-black/70 backdrop-blur-md border border-white/10 text-[10px] text-zinc-300 font-medium">
                <Eye className="w-3 h-3 text-cyan-400" />
                <span>{card.cardData.active_window || 'Desktop'}</span>
              </div>
              {card.cardData?.pointer_target && (
                <div
                  className="absolute z-10 w-6 h-6 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
                  style={{
                    left: `${Math.min(100, Math.max(0, (card.cardData.pointer_target.x / (card.cardData.width || 1920)) * 100))}%`,
                    top: `${Math.min(100, Math.max(0, (card.cardData.pointer_target.y / (card.cardData.height || 1080)) * 100))}%`,
                  }}
                >
                  <span className="absolute inset-0 rounded-full bg-cyan-400/40 animate-ping" />
                  <span className="relative flex items-center justify-center w-full h-full rounded-full bg-cyan-500 text-black shadow-lg">
                    <Crosshair className="w-3.5 h-3.5" />
                  </span>
                </div>
              )}
            </div>
          )}

          {card.cardData?.pointer_target && onHighlight && (
            <div className="flex items-center justify-between p-2 rounded-xl bg-cyan-950/20 border border-cyan-500/20">
              <div className="flex items-center gap-2">
                <Crosshair className="w-4 h-4 text-cyan-400 animate-pulse" />
                <span className="text-xs text-cyan-200 font-medium">
                  {card.cardData.label || 'Target Located'} ({card.cardData.pointer_target.x}, {card.cardData.pointer_target.y})
                </span>
              </div>
              <button
                onClick={() => onHighlight(card.cardData.pointer_target)}
                className="px-2.5 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-200 text-[11px] font-semibold transition cursor-pointer flex items-center gap-1"
              >
                <span>Point on Screen</span>
              </button>
            </div>
          )}

          {/* Analysis Markdown Content */}
          <div className="mt-1 space-y-1 max-h-[220px] overflow-y-auto pr-1 select-text">
            {renderMarkdown(card.displayText || card.spokenReply || '')}
          </div>
        </div>
      )}

      {/* 7. General Markdown Content */}
      {cardType === 'answer' && (
        <div className="mt-1 space-y-1 max-h-[280px] overflow-y-auto pr-1 select-text">
          {renderMarkdown(card.displayText || card.spokenReply || '')}
        </div>
      )}

      {/* Footer Timestamp */}
      <div className="mt-2.5 pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-zinc-500">
        <span>Daisy Desktop Assistant</span>
        <span>{card.timestamp}</span>
      </div>
    </div>
  );
};
