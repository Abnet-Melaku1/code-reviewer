import React, { useState, useEffect, useRef } from "react";
import {
  type Repository,
  type Convention,
  type PullRequest,
  type ReviewComment,
  MOCK_DIFF,
  getSavedRepos,
  saveRepos,
  getSavedConventions,
  saveConventions,
  getSavedPRs,
  savePRs,
  getSavedComments,
} from "./store";

export default function App(): React.ReactElement {
  // Database States
  const [repos, setRepos] = useState<Repository[]>([]);
  const [conventions, setConventions] = useState<Convention[]>([]);
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [comments, setComments] = useState<ReviewComment[]>([]);

  // Selection States
  const [activeRepoId, setActiveRepoId] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<"conventions" | "prs" | "settings">("prs");
  const [selectedPrId, setSelectedPrId] = useState<number | null>(1);

  // Form States
  const [newRepoOwner, setNewRepoOwner] = useState("");
  const [newRepoName, setNewRepoName] = useState("");
  const [newRepoBranch, setNewRepoBranch] = useState("main");

  // WebSocket Live simulation states
  const [wsLogs, setWsLogs] = useState<Array<{ type: "info" | "success" | "error"; text: string }>>([
    { type: "info", text: "[WS] Connected to WebSocket endpoint wss://api.codereviewer.ai/ws" },
    { type: "info", text: "[WS] Idle. Waiting for repository events..." },
  ]);
  const [isReviewing, setIsReviewing] = useState(false);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  // Load Saved Data
  useEffect(() => {
    setRepos(getSavedRepos());
    setConventions(getSavedConventions());
    setPrs(getSavedPRs());
    setComments(getSavedComments());
  }, []);

  // Sync scroll on WS logs
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [wsLogs]);

  // Selected entities helper
  const activeRepo = repos.find((r) => r.id === activeRepoId) || repos[0];
  const activeRepoConventions = conventions.filter((c) => c.repository_id === activeRepoId);
  const activeRepoPrs = prs.filter((p) => p.repository_id === activeRepoId);
  const selectedPr = prs.find((p) => p.id === selectedPrId);

  // Add Repository Handler
  const handleAddRepo = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoOwner || !newRepoName) return;

    const newRepo: Repository = {
      id: Date.now(),
      owner: newRepoOwner,
      name: newRepoName,
      default_branch: newRepoBranch,
      index_status: "pending",
      posting_enabled: false,
    };

    const updated = [...repos, newRepo];
    setRepos(updated);
    saveRepos(updated);

    // Add some default mocked conventions for the new repo
    const newConventions: Convention[] = [
      {
        id: Date.now() + 1,
        repository_id: newRepo.id,
        name: "Standard Header Requirement",
        description: "Ensure all source files contain the standard license header.",
        severity: "must-fix",
        confidence: 0.99,
        is_active: true,
      },
      {
        id: Date.now() + 2,
        repository_id: newRepo.id,
        name: "Clean Log Messages",
        description: "Do not print debug statement passwords, tokens, or personal identifiers in logger output.",
        severity: "must-fix",
        confidence: 0.95,
        is_active: true,
      },
    ];
    const updatedConvs = [...conventions, ...newConventions];
    setConventions(updatedConvs);
    saveConventions(updatedConvs);

    // Add default mock PR
    const newPR: PullRequest = {
      id: Date.now() + 3,
      repository_id: newRepo.id,
      number: 1,
      title: "initial: setup basic template structure",
      author: "developer",
      head_sha: "head_sha_abc",
      base_sha: "base_sha_123",
      state: "open",
    };
    const updatedPRs = [...prs, newPR];
    setPrs(updatedPRs);
    savePRs(updatedPRs);

    // Reset Form
    setNewRepoOwner("");
    setNewRepoName("");
    setNewRepoBranch("main");
    setActiveRepoId(newRepo.id);
    setSelectedPrId(newPR.id);
  };

  // Toggle Convention Active State
  const toggleConvention = (id: number) => {
    const updated = conventions.map((c) =>
      c.id === id ? { ...c, is_active: !c.is_active } : c
    );
    setConventions(updated);
    saveConventions(updated);
  };

  // Toggle Posting Enabled
  const togglePostingEnabled = (id: number) => {
    const updated = repos.map((r) =>
      r.id === id ? { ...r, posting_enabled: !r.posting_enabled } : r
    );
    setRepos(updated);
    saveRepos(updated);
  };

  // Trigger simulated code review run
  const triggerCodeReview = () => {
    if (!selectedPr || isReviewing) return;

    setIsReviewing(true);
    setWsLogs([
      { type: "info", text: `[WS] Connected to WebSocket endpoint wss://api.codereviewer.ai/ws` },
      { type: "info", text: `[WS] Initializing review agent run for PR #${selectedPr.number}...` },
    ]);

    const steps = [
      { text: `[WS] Pulling repository ${activeRepo.owner}/${activeRepo.name} base commit ${selectedPr.base_sha}...`, delay: 1200, type: "info" as const },
      { text: `[WS] Computing local git diff base...head (three-dot comparison)...`, delay: 2200, type: "info" as const },
      { text: `[WS] Parsed 1 files and 2 hunks from git diff.`, delay: 3500, type: "info" as const },
      { text: `[WS] Running pgvector search (Cosine Distance) to fetch similar CodeChunks...`, delay: 4800, type: "info" as const },
      { text: `[WS] Retrieved 3 nearest vector chunks matching code context.`, delay: 5800, type: "info" as const },
      { text: `[WS] Grounding agent against ${activeRepoConventions.filter(c => c.is_active).length} active conventions...`, delay: 7000, type: "info" as const },
      { text: `[WS] Invoking LLM StyleAnalyzer using model configuration: gpt-4o...`, delay: 8500, type: "info" as const },
      { text: `[WS] Review agent completed run. 2 suggestions generated.`, delay: 10500, type: "success" as const },
      {
        text: activeRepo.posting_enabled
          ? `[WS] Posting 2 review comments back to GitHub API (POST /repos/${activeRepo.owner}/${activeRepo.name}/pulls/${selectedPr.number}/comments)...`
          : `[WS] Posting disabled. Gated comments in DB storage.`,
        delay: 12000,
        type: "info" as const,
      },
      { text: `[WS] Success! review completed.`, delay: 13500, type: "success" as const },
    ];

    steps.forEach((step) => {
      setTimeout(() => {
        setWsLogs((prev) => [...prev, { type: step.type, text: step.text }]);
        if (step.text.includes("Success! review completed")) {
          setIsReviewing(false);
        }
      }, step.delay);
    });
  };

  // Render Diff Line Table
  const renderDiffLines = () => {
    const lines = MOCK_DIFF.split("\n");
    let currentLineNum = 0;
    
    return (
      <table className="diff-table">
        <tbody>
          {lines.map((lineText, index) => {
            let rowClass = "diff-row-normal";
            if (lineText.startsWith("+")) {
              rowClass = "diff-row-added";
              currentLineNum++;
            } else if (lineText.startsWith("-")) {
              rowClass = "diff-row-removed";
            } else if (lineText.startsWith("@@")) {
              rowClass = "diff-row-header";
            } else {
              currentLineNum++;
            }

            // Find matching comment for current line
            const lineComments = comments.filter(
              (c) => c.line === currentLineNum && index > 10 // ensure it maps after the header lines
            );

            return (
              <React.Fragment key={index}>
                <tr className={`diff-row ${rowClass}`}>
                  <td className="diff-num">
                    {lineText.startsWith("-") || lineText.startsWith("@@") ? "" : currentLineNum}
                  </td>
                  <td className="diff-content">{lineText.substring(1)}</td>
                </tr>
                {lineComments.length > 0 &&
                  lineComments.map((comment) => (
                    <tr key={comment.id} className="inline-comment-row">
                      <td className="inline-comment-placeholder"></td>
                      <td style={{ padding: 0 }}>
                        <div className={`comment-card comment-card-${comment.severity}`}>
                          <div className="comment-header">
                            <div className="comment-author-info">
                              <div className="comment-avatar">AI</div>
                              <span className="comment-author">CodeReviewer.ai Agent</span>
                            </div>
                            <span className={`comment-severity-tag tag-${comment.severity}`}>
                              {comment.severity}
                            </span>
                          </div>
                          <div className="comment-body">{comment.body}</div>
                          {comment.patch && (
                            <div className="patch-block">
                              <div className="patch-header">SUGGESTED PATCH</div>
                              <pre className="patch-content"><code>{comment.patch}</code></pre>
                            </div>
                          )}
                          {comment.citations && comment.citations.length > 0 && (
                            <div className="citations-list">
                              {comment.citations.map((cit, cIdx) => (
                                <span key={cIdx} className="citation-chip">
                                  🔗 {cit.name}
                                  <div className="citation-tooltip">
                                    <strong>{cit.type.toUpperCase()}: {cit.name}</strong>
                                    <p style={{ margin: "4px 0 0 0" }}>{cit.description}</p>
                                  </div>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    );
  };

  return (
    <div>
      {/* Header */}
      <header className="navbar glass">
        <div className="logo-container">
          <div className="logo-icon">CR</div>
          <span className="logo-text">CodeReviewer.ai</span>
          <span className="logo-sub">BETA</span>
        </div>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#10b981" }}></span>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>API Gateway: Online</span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Sidebar Panel */}
        <div className="sidebar-panel">
          {/* Repository Selector */}
          <div className="glass" style={{ padding: "1.5rem" }}>
            <h3 className="sidebar-title">Repositories</h3>
            <div className="repo-list">
              {repos.map((repo) => (
                <div
                  key={repo.id}
                  className={`glass repo-card ${activeRepoId === repo.id ? "active" : "glass-hover"}`}
                  onClick={() => {
                    setActiveRepoId(repo.id);
                    // Select first PR of the selected repo if available
                    const repoPrs = prs.filter((p) => p.repository_id === repo.id);
                    if (repoPrs.length > 0) {
                      setSelectedPrId(repoPrs[0].id);
                    } else {
                      setSelectedPrId(null);
                    }
                  }}
                >
                  <div className="repo-card-header">
                    <div>
                      <span className="repo-owner">{repo.owner} /</span>
                      <div className="repo-name">{repo.name}</div>
                    </div>
                    <span className={`badge badge-${repo.index_status}`}>
                      {repo.index_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Add Repository */}
          <div className="glass" style={{ padding: "1.5rem" }}>
            <h3 className="sidebar-title">Register Repository</h3>
            <form onSubmit={handleAddRepo} className="repo-form">
              <div className="form-group">
                <label className="form-label">Repository Owner</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. google"
                  value={newRepoOwner}
                  onChange={(e) => setNewRepoOwner(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Repository Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. guava"
                  value={newRepoName}
                  onChange={(e) => setNewRepoName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Default Branch</label>
                <input
                  type="text"
                  className="form-input"
                  value={newRepoBranch}
                  onChange={(e) => setNewRepoBranch(e.target.value)}
                />
              </div>
              <button type="submit" className="btn" style={{ marginTop: "0.5rem" }}>
                Add Repository
              </button>
            </form>
          </div>
        </div>

        {/* Workspace panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
          {/* Active Repo Indicator */}
          {activeRepo && (
            <div className="glass" style={{ padding: "1.5rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 700 }}>
                  {activeRepo.owner} / {activeRepo.name}
                </h2>
                <p style={{ margin: "0.25rem 0 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                  Default branch: <code>{activeRepo.default_branch}</code>
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span className="form-label">POST COMMENTS ON GITHUB:</span>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={activeRepo.posting_enabled}
                      onChange={() => togglePostingEnabled(activeRepo.id)}
                    />
                    <span className="slider"></span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="glass" style={{ padding: "1.5rem", minHeight: "600px" }}>
            <div className="tab-container">
              <button
                className={`tab-btn ${activeTab === "prs" ? "active" : ""}`}
                onClick={() => setActiveTab("prs")}
              >
                Pull Requests & Reviews
              </button>
              <button
                className={`tab-btn ${activeTab === "conventions" ? "active" : ""}`}
                onClick={() => setActiveTab("conventions")}
              >
                Conventions Surface
              </button>
              <button
                className={`tab-btn ${activeTab === "settings" ? "active" : ""}`}
                onClick={() => setActiveTab("settings")}
              >
                Settings
              </button>
            </div>

            {/* Tab: Conventions */}
            {activeTab === "conventions" && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                  <div>
                    <h3 style={{ margin: 0 }}>Grounding Conventions</h3>
                    <p style={{ margin: "0.25rem 0 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                      Active guidelines the RAG retrieval uses to ground reviews for this codebase.
                    </p>
                  </div>
                </div>

                {activeRepoConventions.length === 0 ? (
                  <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                    No conventions mined for this repository yet. Register a webhook and open a PR to start mining!
                  </div>
                ) : (
                  <div className="conventions-grid">
                    {activeRepoConventions.map((conv) => (
                      <div key={conv.id} className="glass convention-card">
                        <div className="convention-header">
                          <h4 className="convention-title">{conv.name}</h4>
                          <label className="toggle-switch">
                            <input
                              type="checkbox"
                              checked={conv.is_active}
                              onChange={() => toggleConvention(conv.id)}
                            />
                            <span className="slider"></span>
                          </label>
                        </div>
                        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0, flexGrow: 1 }}>
                          {conv.description}
                        </p>
                        <div className="convention-meta">
                          <span className={`badge tag-${conv.severity}`}>{conv.severity}</span>
                          <span>Confidence: <strong>{Math.round(conv.confidence * 100)}%</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab: Pull Requests & Reviews */}
            {activeTab === "prs" && (
              <div>
                {activeRepoPrs.length === 0 ? (
                  <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
                    No Pull Requests registered for this repository.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
                    {/* PR Selector Dropdown */}
                    <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                      <span className="form-label">Active PR:</span>
                      <select
                        className="form-input"
                        value={selectedPrId || ""}
                        onChange={(e) => setSelectedPrId(Number(e.target.value))}
                        style={{ minWidth: "300px" }}
                      >
                        {activeRepoPrs.map((pr) => (
                          <option key={pr.id} value={pr.id}>
                            #{pr.number}: {pr.title}
                          </option>
                        ))}
                      </select>
                      <button
                        className="btn"
                        onClick={triggerCodeReview}
                        disabled={isReviewing}
                      >
                        {isReviewing ? "Reviewing..." : "Run Code Review"}
                      </button>
                    </div>

                    {selectedPr && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                        {/* PR Metadata */}
                        <div className="glass" style={{ padding: "1.25rem", background: "rgba(255,255,255,0.01)" }}>
                          <h4 style={{ margin: 0, fontSize: "1.1rem" }}>
                            #{selectedPr.number} — {selectedPr.title}
                          </h4>
                          <div style={{ display: "flex", gap: "1.5rem", marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                            <span>Author: <strong>{selectedPr.author}</strong></span>
                            <span>Base SHA: <code>{selectedPr.base_sha}</code></span>
                            <span>Head SHA: <code>{selectedPr.head_sha}</code></span>
                            <span className="badge badge-ready">{selectedPr.state}</span>
                          </div>
                        </div>

                        {/* Live WebSocket console */}
                        <div className="ws-panel">
                          <div className="ws-header">
                            <span>AGENT WEBSOCKET CONSOLE LOGS</span>
                            <span style={{ color: isReviewing ? "var(--accent-cyan)" : "var(--text-muted)" }}>
                              {isReviewing ? "● RECEIVING" : "● DISCONNECTED"}
                            </span>
                          </div>
                          <div className="ws-console">
                            {wsLogs.map((log, idx) => (
                              <div
                                key={idx}
                                className={
                                  log.type === "success"
                                    ? "ws-line"
                                    : log.type === "error"
                                    ? "ws-line-error"
                                    : "ws-line-info"
                                }
                              >
                                {log.text}
                              </div>
                            ))}
                            <div ref={consoleEndRef} />
                          </div>
                        </div>

                        {/* Inline Code Diff View */}
                        <div>
                          <h4 style={{ margin: "0 0 1rem 0" }}>Files Diff & Inline Comments</h4>
                          <div className="diff-container">
                            <div className="diff-header">
                              <span>guava/src/com/google/common/collect/CustomMultimap.java</span>
                              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>2hunks / 2 comments</span>
                            </div>
                            <div className="diff-lines-wrapper">{renderDiffLines()}</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Tab: Settings */}
            {activeTab === "settings" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "600px" }}>
                <h3 style={{ margin: 0 }}>Webhook Integration</h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", margin: 0 }}>
                  To link GitHub events directly to CodeReviewer, register the following endpoint URL as a webhook in your GitHub App or repository:
                </p>
                <div className="glass" style={{ padding: "1rem", background: "#020408" }}>
                  <code style={{ color: "var(--accent-cyan)", fontSize: "0.9rem" }}>
                    https://api.codereviewer.ai/webhooks/github
                  </code>
                </div>
                
                <div className="form-group">
                  <label className="form-label">Webhook Secret Key</label>
                  <input
                    type="password"
                    className="form-input"
                    value="••••••••••••••••••••••••••••••••"
                    disabled
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
