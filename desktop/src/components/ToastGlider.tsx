import React from 'react';

interface ToastGliderProps {
  message: string;
  meta: string;
  visible: boolean;
  accentColor?: string;
}

export const ToastGlider: React.FC<ToastGliderProps> = ({
  message,
  meta,
  visible,
  accentColor = '#1db954',
}) => {
  return (
    <div
      className={`mb-4 transition-all duration-300 pointer-events-none z-30 ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2'
      }`}
    >
      <div className="px-4 py-2 rounded-xl bg-zinc-900/90 border border-white/10 backdrop-blur-xl flex items-center gap-2.5 text-xs text-white shadow-xl">
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: accentColor }} />
        <span className="font-medium tracking-tight truncate max-w-xs">{message}</span>
        <span className="text-[11px] text-zinc-400 pl-2 border-l border-white/10 flex-shrink-0 font-mono">
          {meta}
        </span>
      </div>
    </div>
  );
};
