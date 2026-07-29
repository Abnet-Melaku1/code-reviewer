import React from "react";
import { type PullRequest, type ReviewComment, type Review, MOCK_DIFF } from "../store";
import { highlightCode } from "../utils/syntax";

interface ReviewWorkspaceProps {
  selectedPr: PullRequest | undefined;
  setSelectedPrId: (id: number | null) => void;
  isReviewing: boolean;
  triggerCodeReview: () => void;
  activeReview: Review | null;
  comments: ReviewComment[];
  hoveredCommentId: number | null;
  setHoveredCommentId: (id: number | null) => void;
  hoveredLineNum: number | null;
  setHoveredLineNum: (num: number | null) => void;
}

export const ReviewWorkspace: React.FC<ReviewWorkspaceProps> = ({
  selectedPr,
  setSelectedPrId,
  isReviewing,
  triggerCodeReview,
  activeReview,
  comments,
  hoveredCommentId,
  setHoveredCommentId,
  hoveredLineNum,
  setHoveredLineNum,
}) => {
  // Render Diff Line Table inside the workspace view for self-containment
  const renderDiffLines = () => {
    const lines = MOCK_DIFF.split("\n");
    let currentLineNum = 0;
    
    return (
      <div className="divide-y divide-hairline/30">
        {lines.map((lineText, index) => {
          let rowClass = "bg-transparent";
          let codeClass = "whitespace-pre px-4 py-1 flex-grow font-code-md text-[13px] text-on-surface";
          let prefix = "  ";

          if (lineText.startsWith("+")) {
            rowClass = "syntax-diff-add";
            codeClass = "whitespace-pre px-4 py-1 flex-grow font-code-md text-[13px] text-severity-nit";
            currentLineNum++;
            prefix = "+ ";
          } else if (lineText.startsWith("-")) {
            rowClass = "syntax-diff-remove";
            codeClass = "whitespace-pre px-4 py-1 flex-grow font-code-md text-[13px] text-severity-must-fix";
            prefix = "- ";
          } else if (lineText.startsWith("@@")) {
            rowClass = "bg-primary-fixed-dim/20";
            codeClass = "whitespace-pre px-4 py-1 flex-grow font-code-md text-[12px] text-primary";
            prefix = "";
          } else {
            currentLineNum++;
          }

          // Check if hovered
          const isLineHovered = hoveredLineNum === currentLineNum;

          return (
            <div 
              key={index} 
              className={`flex items-stretch hover:bg-surface-container-low transition-colors duration-100 group border-b border-hairline/10 ${rowClass} ${isLineHovered ? "bg-primary-fixed/20" : ""}`}
              onMouseEnter={() => currentLineNum > 0 && setHoveredLineNum(currentLineNum)}
              onMouseLeave={() => setHoveredLineNum(null)}
            >
              <div className="w-12 text-right pr-4 py-1 text-ink-muted select-none border-r border-hairline/30 font-code-md text-xs bg-surface-container-lowest/30">
                {lineText.startsWith("-") || lineText.startsWith("@@") ? "" : currentLineNum}
              </div>
              <div className={codeClass}>
                <span className="opacity-40 select-none mr-1">{prefix}</span>
                {highlightCode(prefix ? lineText.substring(1) : lineText)}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex-grow flex flex-col md:flex-row w-full">
      {/* Left Sidebar of PR Detail */}
      <aside className="w-full md:w-64 bg-paper-base border-r border-hairline flex flex-col p-6 shrink-0">
        <div className="mb-6 flex items-center gap-2">
          <button 
            onClick={() => setSelectedPrId(null)}
            className="material-symbols-outlined text-ink-muted p-1 hover:bg-surface-container rounded cursor-pointer"
            title="Back to queue"
          >
            arrow_back
          </button>
          <span className="font-label-sm text-label-sm text-ink-muted uppercase tracking-widest truncate">Back to Queue</span>
        </div>

        <div className="p-4 bg-surface-raised border border-hairline rounded-lg shadow-sm mb-6 flex flex-col gap-2">
          <p className="font-label-sm text-[9px] uppercase tracking-wider text-primary m-0">Current PR</p>
          <h4 className="font-label-md text-sm font-bold truncate leading-snug">{selectedPr?.title}</h4>
          <span className="text-[10px] text-ink-muted">PR #{selectedPr?.number} by @{selectedPr?.author}</span>
        </div>

        <nav className="flex-1 flex flex-col gap-1">
          <button className="w-full flex items-center gap-3 px-3 py-2 text-primary font-bold bg-surface-raised transition-all duration-150 rounded shadow-sm border border-hairline">
            <span className="material-symbols-outlined text-primary">folder_open</span>
            <span className="font-label-sm text-label-sm text-left">Review Files</span>
            <span className="ml-auto bg-primary-container text-on-primary-container px-1.5 rounded text-[10px] font-bold">1</span>
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-ink-muted hover:bg-surface-container-low transition-all duration-150 rounded text-left">
            <span className="material-symbols-outlined">history</span>
            <span className="font-label-sm text-label-sm">Review Commits</span>
          </button>
          <button 
            onClick={triggerCodeReview}
            disabled={isReviewing}
            className="mt-4 w-full bg-primary text-on-primary py-2.5 rounded font-label-md text-xs hover:opacity-95 transition-opacity flex items-center justify-center gap-2 cursor-pointer"
          >
            <span className="material-symbols-outlined text-sm">{isReviewing ? "sync" : "refresh"}</span>
            {isReviewing ? "Reviewing..." : "Rerun Review"}
          </button>
        </nav>
      </aside>

      {/* Center / Left Panel: Code view and summary */}
      <main className="flex-grow p-margin-page overflow-y-auto border-r border-hairline custom-scrollbar">
        {/* Summary Card */}
        <section className="mb-12 p-8 bg-surface-raised border border-hairline manuscript-shadow rounded-lg">
          <div className="flex items-center gap-3 mb-4">
            <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
            <h2 className="font-headline-md text-headline-md font-semibold">Review Summary</h2>
          </div>

          <p className="font-body-lg text-body-lg text-ink-primary leading-relaxed italic mb-6">
            {isReviewing 
              ? "Currently reviewing the diff hunks, matching rules, and verifying boundary line numbers..."
              : activeReview 
              ? activeReview.summary 
              : "No reviews run yet. Click 'Rerun Review' on the left panel to trigger the review agent pipeline."
            }
          </p>

          {!isReviewing && activeReview && (
            <div className="flex gap-4 text-xs font-label-md">
              <span className="text-severity-must-fix font-bold bg-error-container px-2 py-1 rounded">
                {comments.filter(c => c.severity === "must-fix").length} Must-Fix
              </span>
              <span className="text-severity-suggestion font-bold bg-secondary-fixed px-2 py-1 rounded">
                {comments.filter(c => c.severity === "suggestion").length} Suggestions
              </span>
              <span className="text-severity-nit font-bold bg-surface-container px-2 py-1 rounded text-ink-muted">
                {comments.filter(c => c.severity === "nit").length} Nits
              </span>
            </div>
          )}
        </section>

        {/* File Diff Container */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-ink-muted text-sm">description</span>
            <span className="font-code-md text-xs font-semibold text-ink-primary">guava/src/com/google/common/collect/CustomMultimap.java</span>
          </div>
          <span className="font-code-md text-xs text-ink-muted bg-surface-container px-2 py-0.5 rounded">+6 -4</span>
        </div>

        <div className="bg-surface-raised border border-hairline rounded-lg overflow-hidden manuscript-shadow">
          <div className="bg-paper-base px-4 py-2 border-b border-hairline flex items-center justify-between text-xs text-ink-muted font-code-md select-none">
            <span>@@ -12,6 +12,12 @@</span>
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-severity-must-fix"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-severity-suggestion"></span>
            </div>
          </div>
          <div className="overflow-x-auto custom-scrollbar">
            {renderDiffLines()}
          </div>
        </div>
      </main>

      {/* Right Panel: Marginalia Comments Gutter */}
      <aside className="w-full md:w-[400px] bg-paper-base/30 p-8 flex flex-col gap-6 overflow-y-auto max-h-[calc(100vh-64px)] shrink-0 custom-scrollbar">
        <div className="border-b border-hairline pb-3">
          <h3 className="font-label-sm text-label-sm text-ink-muted uppercase tracking-widest">Marginalia Notes</h3>
        </div>

        {comments.length === 0 ? (
          <div className="h-full flex flex-col justify-center items-center text-center text-ink-muted italic p-6">
            No review comments generated. 
          </div>
        ) : (
          <div className="space-y-6">
            {comments.map((comment) => {
              const isCommentHovered = hoveredCommentId === comment.id || hoveredLineNum === comment.line;
              return (
                <div 
                  key={comment.id}
                  className={`relative bg-surface-raised p-5 border rounded-lg manuscript-shadow transition-all duration-150 ${isCommentHovered ? "border-primary scale-[1.02]" : "border-hairline"}`}
                  onMouseEnter={() => setHoveredCommentId(comment.id)}
                  onMouseLeave={() => setHoveredCommentId(null)}
                >
                  <div className="marginalia-connector"></div>
                  
                  <div className="flex justify-between items-center mb-3">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2.5 h-2.5 rounded-full ${comment.severity === "must-fix" ? "bg-severity-must-fix" : comment.severity === "suggestion" ? "bg-severity-suggestion" : "bg-severity-nit"}`}></span>
                      <span className={`font-label-sm text-[10px] font-bold uppercase tracking-tighter ${comment.severity === "must-fix" ? "text-severity-must-fix" : comment.severity === "suggestion" ? "text-severity-suggestion" : "text-ink-muted"}`}>
                        {comment.severity}
                      </span>
                    </div>
                    <span className="font-code-md text-[10px] text-ink-muted bg-surface-container px-1.5 py-0.5 rounded">Line {comment.line}</span>
                  </div>

                  <p className="font-body-md text-sm text-ink-primary leading-relaxed mb-4">
                    {comment.body}
                  </p>

                  {comment.patch && (
                    <div className="bg-surface-container rounded p-3 mb-4 border border-hairline">
                      <div className="flex items-center justify-between mb-2 select-none border-b border-hairline/20 pb-1">
                        <span className="text-[9px] font-label-sm text-ink-muted uppercase">Suggested Change</span>
                        <button className="text-primary font-bold text-[10px] hover:underline uppercase cursor-pointer">Apply</button>
                      </div>
                      <code className="block font-code-md text-xs leading-snug overflow-x-auto whitespace-pre custom-scrollbar">
                        {highlightCode(comment.patch)}
                      </code>
                    </div>
                  )}

                  {comment.citations && comment.citations.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 border-t border-hairline/30 pt-3">
                      {comment.citations.map((cit, cIdx) => (
                        <span key={cIdx} className="citation-chip inline-flex items-center gap-1 px-1.5 py-0.5 border border-hairline rounded text-[10px] text-primary bg-primary/5 cursor-default relative">
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
              );
            })}
          </div>
        )}
      </aside>
    </div>
  );
};
