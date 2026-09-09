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
      className={`transition-all duration-300 pointer-events-none z-40 ${
        visible ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 -translate-y-2 scale-95'
      }`}
    >
      <div className="px-2.5 py-1 rounded-full bg-black/90 border border-white/15 backdrop-blur-xl flex items-center gap-1.5 text-[11px] text-white shadow-xl max-w-[200px]">
        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 animate-pulse" style={{ background: accentColor }} />
        <span className="font-medium tracking-tight truncate flex-1">{message}</span>
        {meta && (
          <span className="text-[10px] text-zinc-400 pl-1.5 border-l border-white/10 flex-shrink-0 font-mono">
            {meta}
          </span>
        )}
      </div>
    </div>
  );
};
