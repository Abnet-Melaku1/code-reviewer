import React from "react";

export const Footer: React.FC = () => {
  return (
    <footer className="bg-background border-t border-hairline py-6 px-margin-page flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-label-sm text-ink-muted mt-auto z-40 select-none">
      <div className="flex items-center gap-6">
        <span className="font-label-md text-label-md text-primary font-bold">CodeReviewer.ai</span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <kbd className="bg-surface-raised px-1.5 py-0.5 rounded border border-hairline">j</kbd> 
            <kbd className="bg-surface-raised px-1.5 py-0.5 rounded border border-hairline">k</kbd> navigate
          </span>
          <span className="flex items-center gap-1">
            <kbd className="bg-surface-raised px-1.5 py-0.5 rounded border border-hairline">Enter</kbd> reply
          </span>
        </div>
      </div>
      <div className="flex items-center gap-6">
        <span>© 2026 CodeReviewer.ai — A Literate Code Experience</span>
        <nav className="flex gap-4">
          <a href="#" className="hover:text-primary transition-colors">Documentation</a>
          <a href="#" className="hover:text-primary transition-colors">Privacy</a>
        </nav>
      </div>
    </footer>
  );
};
