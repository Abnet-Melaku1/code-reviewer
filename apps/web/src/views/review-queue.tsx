import React from "react";
import { type PullRequest } from "../store";

interface ReviewQueueProps {
  activeRepoPrs: PullRequest[];
  setSelectedPrId: (id: number | null) => void;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({
  activeRepoPrs,
  setSelectedPrId,
}) => {
  return (
    <main className="flex-1 pt-8 pb-12 px-margin-page max-w-4xl mx-auto w-full">
      <header className="mb-12">
        <h1 className="font-headline-lg text-headline-lg text-ink-primary mb-2">The Review Queue</h1>
        <p className="font-body-md text-body-md text-ink-muted">Refining code into literature. Select a PR to review.</p>
      </header>

      <div className="flex justify-between items-center mb-6 border-b border-hairline pb-4">
        <div className="flex gap-6">
          <button className="font-label-sm text-label-sm text-primary font-bold uppercase tracking-wider border-b border-primary">All Active PRs</button>
          <button className="font-label-sm text-label-sm text-ink-muted uppercase tracking-wider hover:text-primary">Open</button>
          <button className="font-label-sm text-label-sm text-ink-muted uppercase tracking-wider hover:text-primary">Closed</button>
        </div>
        <span className="font-label-sm text-xs text-ink-muted">{activeRepoPrs.length} manuscripts</span>
      </div>

      {activeRepoPrs.length === 0 ? (
        <div className="bg-surface-raised border border-hairline rounded-lg p-16 text-center text-ink-muted italic">
          No pull requests registered for this repository. Trigger a webhook commit push to see pull requests here.
        </div>
      ) : (
        <div className="flex flex-col border border-hairline rounded-lg bg-surface-raised overflow-hidden divide-y divide-hairline">
          {activeRepoPrs.map((pr) => (
            <div 
              key={pr.id} 
              className="p-6 hover:bg-surface-container-low cursor-pointer transition-all duration-150 flex items-start justify-between gap-6 group"
              onClick={() => setSelectedPrId(pr.id)}
            >
              <div className="flex-grow min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-label-sm text-[10px] text-ink-muted px-2 py-0.5 bg-surface-container rounded-sm truncate">
                    #{pr.number} · {pr.head_sha.substring(0, 7)}
                  </span>
                  <span className="text-[10px] text-ink-muted">•</span>
                  <span className="font-label-sm text-[10px] text-ink-muted">by @{pr.author}</span>
                </div>
                <h3 className="font-headline-md text-base font-semibold text-ink-primary group-hover:text-primary transition-colors leading-tight mb-2 truncate">
                  {pr.title}
                </h3>
                <p className="font-body-md text-xs italic text-ink-muted">
                  Active branch: <code className="bg-surface-container px-1.5 py-0.5 rounded text-[11px]">{pr.head_sha}</code>
                </p>
              </div>

              <div className="flex flex-col items-end justify-between shrink-0 min-h-[50px]">
                <span className={`px-2.5 py-0.5 rounded-full font-label-sm text-[10px] uppercase font-bold tracking-tighter ${pr.state === "open" ? "bg-primary-fixed text-primary" : "bg-surface-container text-ink-muted"}`}>
                  {pr.state}
                </span>
                <span className="font-label-sm text-[10px] text-ink-muted italic">Review details</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
};
