import React, { useState, useRef } from 'react';
import { Play, Pause, SkipForward, Music, Maximize2, ChevronLeft } from 'lucide-react';

export interface CompactPlayerProps {
  trackTitle: string;
  trackArtist: string;
  artworkUrl: string | null;
  isPlaying: boolean;
  progressMs: number;
  durationMs: number;
  onTogglePlay: (e: React.MouseEvent) => void;
  onNext: (e: React.MouseEvent) => void;
  onExpand: () => void;
  onTuck: () => void;
}

export const CompactPlayer: React.FC<CompactPlayerProps> = ({
  trackTitle,
  trackArtist,
  artworkUrl,
  isPlaying,
  progressMs,
  durationMs,
  onTogglePlay,
  onNext,
  onExpand,
  onTuck,
}) => {
  const [dragOffset, setDragOffset] = useState<number>(0);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const startXRef = useRef<number | null>(null);
  const hasDraggedRef = useRef<boolean>(false);

  const progressPercent = durationMs > 0
    ? Math.min(100, Math.max(0, (progressMs / durationMs) * 100))
    : 0;

  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    startXRef.current = e.clientX;
    hasDraggedRef.current = false;
    setIsDragging(true);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (startXRef.current === null) return;
    const dx = e.clientX - startXRef.current;
    if (Math.abs(dx) > 6) {
      hasDraggedRef.current = true;
    }
    // Only allow swiping left (towards the orb)
    if (dx < 0) {
      setDragOffset(Math.max(-100, dx));
    } else {
      setDragOffset(Math.min(15, dx * 0.2));
    }
  };

  const handlePointerUp = () => {
    if (startXRef.current !== null) {
      if (dragOffset < -35) {
        onTuck();
      }
    }
    startXRef.current = null;
    setIsDragging(false);
    setDragOffset(0);
  };

  const handleContainerClick = () => {
    if (hasDraggedRef.current) {
      hasDraggedRef.current = false;
      return;
    }
    onExpand();
  };

  return (
    <div
      onClick={handleContainerClick}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      className="group relative flex items-center gap-3 px-3 py-2.5 rounded-2xl cursor-pointer select-none shadow-2xl backdrop-blur-2xl bg-[#0c0f14]/85 border border-white/10 hover:border-white/20 w-[275px] h-[68px] overflow-hidden touch-none"
      title="Swipe left towards Orb to tuck, or click to expand"
      style={{
        boxShadow: '0 16px 36px -8px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.08), inset 0 1px 1px rgba(255, 255, 255, 0.15)',
        transform: `translateX(${dragOffset}px)`,
        opacity: Math.max(0.2, 1 - Math.abs(dragOffset) / 90),
        transition: isDragging ? 'none' : 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease',
      }}
    >
      {/* Quick Tuck Arrow (visible on hover) */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onTuck();
        }}
        className="opacity-0 group-hover:opacity-100 -ml-1 w-5 h-8 flex items-center justify-center text-zinc-400 hover:text-emerald-400 transition-opacity cursor-pointer shrink-0"
        title="Tuck into Orb"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {/* Dynamic Ambient Blur Glow behind Album Art */}
      {artworkUrl && (
        <div
          className="absolute -left-4 -top-4 w-20 h-20 rounded-full blur-xl opacity-40 pointer-events-none transition-opacity group-hover:opacity-60"
          style={{
            backgroundImage: `url(${artworkUrl})`,
            backgroundSize: 'cover',
          }}
        />
      )}

      {/* Album Artwork Thumbnail */}
      <div className="relative w-11 h-11 rounded-xl overflow-hidden shrink-0 border border-white/10 bg-zinc-900 shadow-md flex items-center justify-center">
        {artworkUrl ? (
          <img
            src={artworkUrl}
            alt={trackTitle}
            className="w-full h-full object-cover"
            loading="eager"
          />
        ) : (
          <Music className="w-5 h-5 text-emerald-400/60" />
        )}

        {/* Live Audio Waves Indicator */}
        {isPlaying && (
          <div className="absolute inset-0 bg-black/40 flex items-center justify-center gap-0.5 pointer-events-none">
            <span className="w-0.5 bg-emerald-400 rounded-full animate-pulse h-2.5" />
            <span className="w-0.5 bg-emerald-400 rounded-full animate-pulse h-4 delay-75" />
            <span className="w-0.5 bg-emerald-400 rounded-full animate-pulse h-2 delay-150" />
          </div>
        )}
      </div>

      {/* Track & Artist Info */}
      <div className="flex-1 min-w-0 pr-1">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-white truncate tracking-tight" title={trackTitle}>
            {trackTitle}
          </span>
        </div>
        <p className="text-[11px] text-zinc-400 truncate mt-0.5" title={trackArtist}>
          {trackArtist}
        </p>
      </div>

      {/* Inline Quick Action Controls */}
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onTogglePlay(e);
          }}
          className="w-8 h-8 rounded-full bg-white/10 hover:bg-emerald-500 hover:text-black text-white flex items-center justify-center transition-all cursor-pointer shadow-sm active:scale-90"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <Pause className="w-3.5 h-3.5 fill-current" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
          )}
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onNext(e);
          }}
          className="w-7 h-7 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 flex items-center justify-center transition-all cursor-pointer active:scale-90"
          title="Next track"
        >
          <SkipForward className="w-3.5 h-3.5 fill-current" />
        </button>

        <div className="text-zinc-500 group-hover:text-zinc-300 transition-colors pl-0.5" title="Expand player">
          <Maximize2 className="w-3 h-3 opacity-60 group-hover:opacity-100" />
        </div>
      </div>

      {/* Mini Progress Bar Line at Bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-white/[0.06] overflow-hidden">
        <div
          className="h-full bg-emerald-400 transition-all duration-300 shadow-[0_0_8px_#34d399]"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
};

export default CompactPlayer;
