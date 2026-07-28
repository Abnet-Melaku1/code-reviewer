import React, { useState, useEffect, useRef } from "react";
import {
  type Repository,
  type Convention,
  type PullRequest,
  type ReviewComment,
  MOCK_DIFF,
  fetchRepos,
  createRepo,
  updateRepoPosting,
  fetchConventions,
  toggleConventionActive,
  fetchPRs,
  fetchReviews,
  rerunReview,
  createReview,
  fetchComments,
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
  const [selectedPrId, setSelectedPrId] = useState<number | null>(null);

  // Form States
  const [newRepoOwner, setNewRepoOwner] = useState("");
  const [newRepoName, setNewRepoName] = useState("");
  const [newRepoBranch, setNewRepoBranch] = useState("main");

  // WebSocket Live simulation states
  const [wsLogs, setWsLogs] = useState<Array<{ type: "info" | "success" | "error"; text: string }>>([
    { type: "info", text: "[WS] Initializing WebSocket gateway subscriber..." },
  ]);
  const [isReviewing, setIsReviewing] = useState(false);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  // Load Initial Repositories
  useEffect(() => {
    fetchRepos()
      .then((data) => {
        setRepos(data);
        if (data.length > 0) {
          setActiveRepoId(data[0].id);
        }
      })
      .catch((err) => console.error("Error loading repositories:", err));
  }, []);

  // Fetch conventions and PRs when activeRepoId changes
  useEffect(() => {
    if (!activeRepoId) return;

    fetchConventions(activeRepoId)
      .then(setConventions)
      .catch((err) => console.error("Error loading conventions:", err));

    fetchPRs(activeRepoId)
      .then((data) => {
        setPrs(data);
        if (data.length > 0) {
          setSelectedPrId(data[0].id);
        } else {
          setSelectedPrId(null);
          setComments([]);
        }
      })
      .catch((err) => console.error("Error loading PRs:", err));
  }, [activeRepoId]);

  // Fetch comments for the selected PR review run
  const reloadPrComments = () => {
    if (!selectedPrId) {
      setComments([]);
      return;
    }
    fetchReviews(selectedPrId)
      .then(async (reviews) => {
        if (reviews.length > 0) {
          const latest = reviews[reviews.length - 1];
          try {
            const commentsData = await fetchComments(latest.id);
            setComments(commentsData);
          } catch (err) {
            console.error("Error loading comments:", err);
          }
        } else {
          setComments([]);
        }
      })
      .catch((err) => console.error("Error loading reviews:", err));
  };

  useEffect(() => {
    reloadPrComments();
  }, [selectedPrId]);

  // Connect to the real WebSocket progress gateway
  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onopen = () => {
      setWsLogs((prev) => [
        ...prev,
        { type: "success", text: "[WS] Connected to live backend WebSocket progress gateway" },
      ]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket event:", data);

        if (data.type === "index.status") {
          // Refresh repositories list to update index_status in UI
          fetchRepos().then(setRepos).catch(console.error);
          setWsLogs((prev) => [
            ...prev,
            { type: "info", text: `[WS] Repository #${data.repository_id} status: ${data.index_status.toUpperCase()}` },
          ]);
        } else if (data.type === "index.progress") {
          setWsLogs((prev) => [
            ...prev,
            { type: "info", text: `[WS] [Index Repo #${data.repository_id}] ${data.phase} (${data.files_done}/${data.files_total} files)` },
          ]);
        } else if (data.type === "review.queued") {
          setIsReviewing(true);
          setWsLogs((prev) => [
            ...prev,
            { type: "info", text: `[WS] Review queued: run #${data.review_id} for PR #${data.pull_request_id}` },
          ]);
        } else if (data.type === "review.progress") {
          setWsLogs((prev) => [
            ...prev,
            { type: "info", text: `[WS] [Review Run] ${data.phase}` },
          ]);
        } else if (data.type === "review.comment") {
          setWsLogs((prev) => [
            ...prev,
            { type: "success", text: `[WS] Review Comment generated for ${data.comment.file_path}:${data.comment.line}` },
          ]);
        } else if (data.type === "review.completed") {
          setIsReviewing(false);
          setWsLogs((prev) => [
            ...prev,
            { type: "success", text: `[WS] Review run completed! Summary: ${data.summary}` },
          ]);
          reloadPrComments();
        } else if (data.type === "review.failed") {
          setIsReviewing(false);
          setWsLogs((prev) => [
            ...prev,
            { type: "error", text: `[WS] Review failed: ${data.error}` },
          ]);
        }
      } catch (err) {
        console.error("Error processing WebSocket message:", err);
      }
    };

    ws.onclose = () => {
      setWsLogs((prev) => [
        ...prev,
        { type: "error", text: "[WS] Disconnected from backend WebSocket gateway" },
      ]);
    };

    return () => {
      ws.close();
    };
  }, [selectedPrId]);

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
  const handleAddRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoOwner || !newRepoName) return;

    try {
      const newRepo = await createRepo(newRepoOwner, newRepoName, newRepoBranch);
      setRepos((prev) => [...prev, newRepo]);
      setActiveRepoId(newRepo.id);

      // Reset Form
      setNewRepoOwner("");
      setNewRepoName("");
      setNewRepoBranch("main");
    } catch (err) {
      console.error("Failed to add repository:", err);
    }
  };

  // Toggle Convention Active State
  const toggleConvention = async (id: number) => {
    const conv = conventions.find((c) => c.id === id);
    if (!conv) return;
    try {
      const updated = await toggleConventionActive(activeRepoId, id, !conv.is_active);
      setConventions((prev) => prev.map((c) => (c.id === id ? updated : c)));
    } catch (err) {
      console.error("Failed to toggle convention:", err);
    }
  };

  // Toggle Posting Enabled
  const togglePostingEnabled = async (id: number) => {
    const repo = repos.find((r) => r.id === id);
    if (!repo) return;
    try {
      const updated = await updateRepoPosting(id, !repo.posting_enabled);
      setRepos((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (err) {
      console.error("Failed to toggle posting enabled:", err);
    }
  };

  // Trigger code review run using backend API
  const triggerCodeReview = async () => {
    if (!selectedPrId || isReviewing) return;

    setIsReviewing(true);
    setWsLogs((prev) => [
      ...prev,
      { type: "info", text: `[WS] Enqueuing review task for PR #${selectedPr?.number}...` },
    ]);

    try {
      // Find reviews for this PR
      const reviews = await fetchReviews(selectedPrId);
      if (reviews.length > 0) {
        // Rerun the latest review
        const latestReview = reviews[reviews.length - 1];
        await rerunReview(latestReview.id);
      } else {
        // Create first review
        await createReview(selectedPrId);
      }
    } catch (err: any) {
      setIsReviewing(false);
      setWsLogs((prev) => [
        ...prev,
        { type: "error", text: `[WS] Failed to trigger code review: ${err.message}` },
      ]);
    }
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
