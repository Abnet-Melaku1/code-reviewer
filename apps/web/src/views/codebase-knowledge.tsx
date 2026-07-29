import React from "react";
import { type Repository, type Convention } from "../store";
import { RepoSidebar } from "../components/repo-sidebar";

interface CodebaseKnowledgeProps {
  activeRepo: Repository | undefined;
  activeRepoConventions: Convention[];
  toggleConvention: (id: number) => void;
  togglePostingEnabled: (id: number) => void;
  repos: Repository[];
  activeRepoId: number;
  onRepoSelect: (id: number) => void;
  newRepoOwner: string;
  setNewRepoOwner: (owner: string) => void;
  newRepoName: string;
  setNewRepoName: (name: string) => void;
  newRepoBranch: string;
  setNewRepoBranch: (branch: string) => void;
  handleAddRepo: (e: React.FormEvent) => void;
}

export const CodebaseKnowledge: React.FC<CodebaseKnowledgeProps> = ({
  activeRepo,
  activeRepoConventions,
  toggleConvention,
  togglePostingEnabled,
  repos,
  activeRepoId,
  onRepoSelect,
  newRepoOwner,
  setNewRepoOwner,
  newRepoName,
  setNewRepoName,
  newRepoBranch,
  setNewRepoBranch,
  handleAddRepo,
}) => {
  return (
    <div className="flex-grow flex flex-col md:flex-row w-full">
      {/* Left Sidebar */}
      <RepoSidebar
        repos={repos}
        activeRepoId={activeRepoId}
        onRepoSelect={onRepoSelect}
        newRepoOwner={newRepoOwner}
        setNewRepoOwner={setNewRepoOwner}
        newRepoName={newRepoName}
        setNewRepoName={setNewRepoName}
        newRepoBranch={newRepoBranch}
        setNewRepoBranch={setNewRepoBranch}
        handleAddRepo={handleAddRepo}
      />

      {/* Main Content Area */}
      <main className="flex-1 p-margin-page max-w-5xl mx-auto overflow-y-auto custom-scrollbar">
        {activeRepo ? (
          <>
            <header className="mb-12 flex justify-between items-start gap-4">
              <div>
                <h1 className="font-headline-lg text-headline-lg italic mb-2">
                  What I've learned about {activeRepo.name}.
                </h1>
                <p className="font-body-lg text-body-lg text-ink-muted leading-relaxed">
                  I've indexed the codebase and compiled mined rules into active grounding conventions.
                </p>
              </div>

              <div className="flex items-center gap-2 px-4 py-2 border border-hairline bg-paper-base rounded shrink-0">
                <span className="font-label-sm text-[11px] text-ink-muted uppercase tracking-wider">GitHub posting:</span>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={activeRepo.posting_enabled}
                    onChange={() => togglePostingEnabled(activeRepo.id)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* Bento Grid: Active Conventions */}
              <div className="lg:col-span-8 space-y-6">
                <div className="flex items-center justify-between border-b border-hairline pb-3">
                  <h3 className="font-headline-md text-headline-md font-semibold">Mined Grounding Conventions</h3>
                  <span className="font-label-sm text-xs text-ink-muted">{activeRepoConventions.length} active</span>
                </div>

                {activeRepoConventions.length === 0 ? (
                  <div className="bg-surface-raised border border-hairline rounded-lg p-12 text-center text-ink-muted italic">
                    No conventions mined for this repository yet. Click "House Style" to add your own, or open a pull request to trigger automatic mining.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {activeRepoConventions.map((conv) => (
                      <div key={conv.id} className="bg-surface-raised border border-hairline rounded-lg p-5 manuscript-shadow flex flex-col gap-4">
                        <div className="flex justify-between items-start gap-2">
                          <h4 className="font-label-md text-sm font-bold text-ink-primary leading-tight">{conv.name}</h4>
                          <label className="toggle-switch">
                            <input
                              type="checkbox"
                              checked={conv.is_active}
                              onChange={() => toggleConvention(conv.id)}
                            />
                            <span className="slider"></span>
                          </label>
                        </div>
                        <p className="font-body-md text-xs text-ink-muted flex-grow italic leading-relaxed">
                          "{conv.description}"
                        </p>
                        <div className="flex justify-between items-center text-[10px] text-ink-muted border-t border-hairline/30 pt-3">
                          <span className={`px-2 py-0.5 rounded font-bold uppercase ${conv.severity === "must-fix" ? "bg-error-container text-severity-must-fix" : conv.severity === "suggestion" ? "bg-secondary-fixed text-primary" : "bg-surface-container text-ink-muted"}`}>
                            {conv.severity}
                          </span>
                          <span>Confidence: <strong>{Math.round(conv.confidence * 100)}%</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Right side stats/details */}
              <div className="lg:col-span-4 space-y-6">
                <div className="p-6 border border-hairline bg-surface-warm rounded-lg">
                  <h4 className="font-label-sm text-ink-muted uppercase tracking-widest mb-4">Indexing Health</h4>
                  <div className="space-y-3">
                    <div className="flex justify-between items-end border-b border-hairline pb-2">
                      <span className="font-body-md text-ink-muted text-sm italic">Coverage</span>
                      <span className="font-label-md text-primary font-bold">98.2%</span>
                    </div>
                    <div className="flex justify-between items-end border-b border-hairline pb-2">
                      <span className="font-body-md text-ink-muted text-sm italic">Conflict Rate</span>
                      <span className="font-label-md text-severity-must-fix font-bold">1.4%</span>
                    </div>
                    <div className="flex justify-between items-end border-b border-hairline pb-2">
                      <span className="font-body-md text-ink-muted text-sm italic">Default branch</span>
                      <span className="font-code-md text-xs text-primary font-semibold">{activeRepo.default_branch}</span>
                    </div>
                  </div>
                </div>

                <div className="p-6 border border-hairline border-dashed rounded-lg bg-surface-raised relative overflow-hidden">
                  <h4 className="font-label-sm text-ink-muted uppercase tracking-widest mb-3">Recent Discovery</h4>
                  <p className="font-body-md text-sm italic text-ink-primary leading-relaxed">
                    "Your team consistently prefers explicit error wrapping in HTTP controller catch blocks rather than silent swallows."
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col justify-center items-center py-24 text-ink-muted italic bg-surface-raised border border-hairline rounded-lg">
            Please register a repository to view codebase knowledge
          </div>
        )}
      </main>
    </div>
  );
};
