import React, { useEffect, useRef } from "react";

interface WebSocketConsoleProps {
  showLogs: boolean;
  setShowLogs: (show: boolean) => void;
  isReviewing: boolean;
  wsLogs: Array<{ type: "info" | "success" | "error"; text: string }>;
}

export const WebSocketConsole: React.FC<WebSocketConsoleProps> = ({
  showLogs,
  setShowLogs,
  isReviewing,
  wsLogs,
}) => {
  const consoleEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (showLogs && consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [wsLogs, showLogs]);

  if (!showLogs) return null;

  return (
    <div className="fixed right-6 bottom-6 w-96 z-50 bg-background border border-hairline rounded-lg shadow-xl manuscript-shadow flex flex-col overflow-hidden animate-slide-up">
      <div className="bg-paper-base px-4 py-2.5 border-b border-hairline flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${isReviewing ? "bg-primary animate-pulse" : "bg-ink-muted"}`}></span>
          <span className="font-label-sm text-xs text-ink-primary font-bold uppercase tracking-wider">Agent websocket logs</span>
        </div>
        <button 
          onClick={() => setShowLogs(false)}
          className="material-symbols-outlined text-ink-muted hover:text-primary transition-colors text-sm select-none cursor-pointer"
        >
          close
        </button>
      </div>
      
      <div className="p-4 h-64 bg-[#1e1c18] font-code-md text-[11px] leading-snug overflow-y-auto custom-scrollbar flex flex-col gap-2 select-all">
        {wsLogs.map((log, idx) => (
          <div
            key={idx}
            className={
              log.type === "success"
                ? "text-[#a0d1be]"
                : log.type === "error"
                ? "text-severity-must-fix"
                : "text-[#ede1d1]"
            }
          >
            {log.text}
          </div>
        ))}
        <div ref={consoleEndRef} />
      </div>
    </div>
  );
};
