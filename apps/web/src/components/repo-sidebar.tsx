import React from "react";
import { type Repository } from "../store";

interface RepoSidebarProps {
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

export const RepoSidebar: React.FC<RepoSidebarProps> = ({
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
    <aside className="w-full md:w-64 bg-paper-base border-r border-hairline flex flex-col p-6 shrink-0">
      <div className="mb-6 flex justify-between items-center">
        <span className="font-label-sm text-label-sm text-ink-muted uppercase tracking-widest">Repositories</span>
        <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-[10px] font-bold">{repos.length} Total</span>
      </div>
      
      <div className="flex-1 flex flex-col gap-2 overflow-y-auto mb-6 custom-scrollbar">
        {repos.map((repo) => (
          <div
            key={repo.id}
            className={`p-3 rounded-lg border cursor-pointer transition-all duration-150 ${activeRepoId === repo.id ? "bg-surface-raised border-primary shadow-sm" : "bg-transparent border-transparent hover:bg-surface-container-low text-ink-muted hover:text-ink-primary"}`}
            onClick={() => onRepoSelect(repo.id)}
          >
            <div className="flex justify-between items-start gap-1">
              <div className="truncate">
                <p className="text-[10px] text-ink-muted leading-none font-label-md m-0 truncate">{repo.owner} /</p>
                <h4 className="font-label-md text-sm font-semibold truncate mt-1">{repo.name}</h4>
              </div>
              <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold tracking-tighter ${repo.index_status === "ready" ? "bg-primary-fixed text-primary" : repo.index_status === "indexing" ? "bg-secondary-container text-secondary-fixed-dim animate-pulse" : repo.index_status === "error" ? "bg-error-container text-error" : "bg-surface-container text-ink-muted"}`}>
                {repo.index_status}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-hairline pt-6">
        <h5 className="font-label-sm text-label-sm text-ink-muted uppercase tracking-widest mb-4">Register New Repo</h5>
        <form onSubmit={handleAddRepo} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-[10px] text-ink-muted">Owner</label>
            <input
              type="text"
              className="bg-surface-raised border border-hairline rounded px-3 py-1.5 font-label-sm text-sm focus:outline-none focus:border-primary placeholder:italic placeholder:opacity-50"
              placeholder="e.g. google"
              value={newRepoOwner}
              onChange={(e) => setNewRepoOwner(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-[10px] text-ink-muted">Name</label>
            <input
              type="text"
              className="bg-surface-raised border border-hairline rounded px-3 py-1.5 font-label-sm text-sm focus:outline-none focus:border-primary placeholder:italic placeholder:opacity-50"
              placeholder="e.g. guava"
              value={newRepoName}
              onChange={(e) => setNewRepoName(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="font-label-sm text-[10px] text-ink-muted">Default Branch</label>
            <input
              type="text"
              className="bg-surface-raised border border-hairline rounded px-3 py-1.5 font-label-sm text-sm focus:outline-none focus:border-primary"
              value={newRepoBranch}
              onChange={(e) => setNewRepoBranch(e.target.value)}
            />
          </div>
          <button type="submit" className="bg-primary text-on-primary font-label-md text-xs py-2 rounded shadow-sm hover:opacity-90 transition-opacity cursor-pointer">
            Add Repository
          </button>
        </form>
      </div>
    </aside>
  );
};
