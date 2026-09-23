import React, { useEffect, useState } from 'react';
import { Crosshair } from 'lucide-react';

export interface PointerTarget {
  x: number;
  y: number;
  width?: number;
  height?: number;
  label?: string;
  durationMs?: number;
}

interface ScreenPointerOverlayProps {
  target: PointerTarget | null;
  onClear: () => void;
}

export const ScreenPointerOverlay: React.FC<ScreenPointerOverlayProps> = ({ target, onClear }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!target) {
      setVisible(false);
      return;
    }

    setVisible(true);
    const duration = target.durationMs || 5000;
    const timer = setTimeout(() => {
      setVisible(false);
      onClear();
    }, duration);

    return () => clearTimeout(timer);
  }, [target, onClear]);

  if (!target || !visible) return null;

  // Screen percentage calculation or raw pixel fallback
  const isPercent = target.x <= 1000 && target.y <= 1000 && target.x > 0 && target.y > 0 && window.innerWidth > 1000;
  const screenX = isPercent ? (target.x / 1000) * window.innerWidth : target.x;
  const screenY = isPercent ? (target.y / 1000) * window.innerHeight : target.y;

  return (
    <div
      className="fixed inset-0 z-50 pointer-events-none overflow-hidden select-none animate-in fade-in duration-300"
      style={{ isolation: 'isolate' }}
    >
      {/* Semi-translucent dark vignette to gently dim surroundings and focus attention */}
      <div className="absolute inset-0 bg-black/15 transition-opacity" />

      {/* Target Marker Beacon */}
      <div
        className="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-auto cursor-pointer group"
        style={{
          left: `${Math.min(window.innerWidth - 40, Math.max(40, screenX))}px`,
          top: `${Math.min(window.innerHeight - 40, Math.max(40, screenY))}px`,
        }}
        onClick={() => {
          setVisible(false);
          onClear();
        }}
        title="Click to dismiss pointer"
      >
        {/* Sonar Pulse Rings */}
        <span className="absolute -inset-6 rounded-full bg-cyan-400/30 animate-ping duration-1000" />
        <span className="absolute -inset-3 rounded-full bg-cyan-400/50 animate-pulse duration-700" />

        {/* Center Glowing Hub */}
        <div className="relative flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-tr from-cyan-500 to-emerald-400 text-black shadow-[0_0_25px_rgba(6,182,212,0.8)] border-2 border-white transform transition-transform group-hover:scale-110">
          <Crosshair className="w-5 h-5 text-black animate-spin-slow" />
        </div>

        {/* Floating Callout Label */}
        {target.label && (
          <div className="absolute top-12 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-xl bg-black/90 border border-cyan-400/50 backdrop-blur-xl shadow-2xl flex items-center gap-1.5 whitespace-nowrap text-xs font-semibold text-cyan-200">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            <span>{target.label}</span>
          </div>
        )}
      </div>
    </div>
  );
};
