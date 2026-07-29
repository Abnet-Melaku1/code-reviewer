import React from "react";

interface HouseStyleProps {
  newConventionText: string;
  setNewConventionText: (text: string) => void;
  handleApplyConvention: () => void;
}

export const HouseStyle: React.FC<HouseStyleProps> = ({
  newConventionText,
  setNewConventionText,
  handleApplyConvention,
}) => {
  return (
    <main className="flex-1 bg-background max-w-5xl mx-auto px-margin-page py-12 overflow-y-auto custom-scrollbar">
      <header className="mb-12">
        <h1 className="font-headline-lg text-headline-lg text-ink-primary mb-2">Teaching Your Conventions</h1>
        <p className="font-body-lg text-body-lg text-ink-muted">Type a rule in plain language, and I'll learn to look for it.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        {/* Left Writing Canvas */}
        <div className="lg:col-span-7">
          <section className="bg-surface-raised border border-hairline manuscript-shadow rounded-lg p-8 min-h-[400px] flex flex-col relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-primary/20"></div>
            
            <div className="flex justify-between items-center mb-6">
              <span className="font-label-sm text-xs text-ink-muted uppercase tracking-widest">The Manuscript</span>
              <span className="text-[10px] text-primary bg-primary/10 px-2 py-0.5 rounded uppercase font-bold">Rule Editor</span>
            </div>

            <textarea
              className="flex-1 w-full bg-transparent border-none focus:ring-0 font-body-lg text-body-lg text-ink-primary rule-input resize-none outline-none"
              placeholder="E.g., All async functions should have a try/catch block with explicit logging..."
              value={newConventionText}
              onChange={(e) => setNewConventionText(e.target.value)}
            />

            <div className="mt-6 flex justify-between items-center pt-6 border-t border-hairline">
              <span className="font-label-sm text-[11px] text-ink-muted italic">Type to codify rule contextually</span>
              <button 
                onClick={handleApplyConvention}
                className="bg-primary text-on-primary px-6 py-2 rounded font-label-md text-sm hover:opacity-90 transition-all shadow-sm cursor-pointer"
              >
                Apply Convention
              </button>
            </div>
          </section>
        </div>

        {/* Right Side: Live preview */}
        <div className="lg:col-span-5 space-y-6">
          <h3 className="font-label-sm text-xs text-ink-muted uppercase tracking-wider mb-2">Live Preview Demonstration</h3>
          
          <div className="relative">
            <div className="bg-surface-raised border border-hairline rounded-lg overflow-hidden manuscript-shadow">
              <div className="bg-paper-base px-4 py-2 border-b border-hairline flex items-center justify-between text-xs text-ink-muted font-code-md">
                <span>src/components/Header.tsx</span>
                <span className="material-symbols-outlined text-sm select-none">close</span>
              </div>

              <div className="p-4 font-code-md text-xs leading-relaxed">
                <div className="flex">
                  <span className="text-ink-muted mr-4 select-none opacity-40">01</span>
                  <span>import React from 'react';</span>
                </div>
                <div className="flex">
                  <span className="text-ink-muted mr-4 select-none opacity-40">02</span>
                  <span></span>
                </div>
                <div className="flex bg-severity-must-fix/10">
                  <span className="text-severity-must-fix mr-4 select-none">03</span>
                  <span>export default function Header() &#123;</span>
                </div>
                <div className="flex">
                  <span className="text-ink-muted mr-4 select-none opacity-40">04</span>
                  <span>  return &lt;header /&gt;;</span>
                </div>
                <div className="flex">
                  <span className="text-ink-muted mr-4 select-none opacity-40">05</span>
                  <span>&#125;</span>
                </div>
              </div>
            </div>

            {/* Connected mock comment */}
            <div className="mt-4 pl-6 border-l-2 border-severity-must-fix/30 relative">
              <div className="absolute -left-[9px] top-4 w-2 h-px bg-severity-must-fix/30"></div>
              <div className="bg-paper-base border border-hairline p-4 rounded-lg manuscript-shadow flex flex-col gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-severity-must-fix"></span>
                  <span className="font-label-sm text-[10px] text-severity-must-fix uppercase font-bold tracking-tighter">Convention Violated</span>
                  <span className="ml-auto text-[10px] bg-error-container text-severity-must-fix px-1.5 py-0.5 rounded font-bold">MUST-FIX</span>
                </div>
                <p className="font-body-md text-xs text-ink-primary leading-relaxed">
                  You've used a <span className="italic">default export</span>. Per the new rule text, please use named exports to ensure IDE auto-imports remain predictable.
                </p>
                <div className="mt-2 flex items-center gap-3 text-xs font-label-md text-primary select-none">
                  <button className="hover:underline cursor-pointer">Apply fix</button>
                  <span className="text-hairline">|</span>
                  <button className="text-ink-muted hover:text-ink-primary cursor-pointer">Ignore</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};
