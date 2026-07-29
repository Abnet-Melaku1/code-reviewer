"use client";

import React, { useState } from "react";
import { useRepoStore } from "../stores/repo-store";
import { useReviewStore } from "../stores/review-store";
import { useWebSocketStore } from "../stores/websocket-store";

import { TopAppBar } from "../components/top-app-bar";
import { Footer } from "../components/footer";
import { WebSocketConsole } from "../components/web-socket-console";
import { CodebaseKnowledge } from "../views/codebase-knowledge";
import { ReviewQueue } from "../views/review-queue";
import { ReviewWorkspace } from "../views/review-workspace";
import { HouseStyle } from "../views/house-style";
import { Settings } from "../views/settings";

export default function Page(): React.ReactElement {
  const [activeTab, setActiveTab] = useState<"repositories" | "reviews" | "style" | "settings" >("repositories");

  // Decoupled hooks store layout to satisfy coding guidelines
  const repoStore = useRepoStore();
  const reviewStore = useReviewStore(repoStore.activeRepoId);
  const wsStore = useWebSocketStore(
    reviewStore.selectedPrId,
    reviewStore.reloadPrComments,
    reviewStore.setIsReviewing
  );

  const handleRepoSelect = (id: number) => {
    repoStore.setActiveRepoId(id);
    reviewStore.setSelectedPrId(null);
  };

  const handleCodeReviewTrigger = () => {
    reviewStore.triggerCodeReview(
      () => {
        wsStore.setWsLogs((prev) => [
          ...prev,
          { type: "info", text: `[WS] Enqueuing review task for PR #${reviewStore.selectedPr?.number}...` },
        ]);
        wsStore.setShowLogs(true);
      },
      (errorMsg) => {
        wsStore.setWsLogs((prev) => [
          ...prev,
          { type: "error", text: `[WS] Failed to trigger code review: ${errorMsg}` },
        ]);
      }
    );
  };

  return (
    <div className="min-h-screen flex flex-col font-body-md text-body-md text-ink-primary bg-background w-full">
      {/* TopAppBar Navigation */}
      <TopAppBar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        showLogs={wsStore.showLogs}
        setShowLogs={wsStore.setShowLogs}
        setSelectedPrId={reviewStore.setSelectedPrId}
      />

      {/* Main Content Layout */}
      <div className="flex-1 flex pt-16 min-h-[calc(100vh-64px)] w-full">
        {/* VIEW: Repositories (Codebase Knowledge) */}
        {activeTab === "repositories" && (
          <CodebaseKnowledge
            activeRepo={repoStore.activeRepo}
            activeRepoConventions={reviewStore.activeRepoConventions}
            toggleConvention={reviewStore.toggleConvention}
            togglePostingEnabled={repoStore.togglePostingEnabled}
            repos={repoStore.repos}
            activeRepoId={repoStore.activeRepoId}
            onRepoSelect={handleRepoSelect}
            newRepoOwner={repoStore.newRepoOwner}
            setNewRepoOwner={repoStore.setNewRepoOwner}
            newRepoName={repoStore.newRepoName}
            setNewRepoName={repoStore.setNewRepoName}
            newRepoBranch={repoStore.newRepoBranch}
            setNewRepoBranch={repoStore.setNewRepoBranch}
            handleAddRepo={repoStore.handleAddRepo}
          />
        )}

        {/* VIEW: Review Queue (List of PRs OR Active PR review workspace) */}
        {activeTab === "reviews" && (
          <div className="flex-grow flex w-full">
            {!reviewStore.selectedPrId ? (
              <ReviewQueue
                activeRepoPrs={reviewStore.activeRepoPrs}
                setSelectedPrId={reviewStore.setSelectedPrId}
              />
            ) : (
              <ReviewWorkspace
                selectedPr={reviewStore.selectedPr}
                setSelectedPrId={reviewStore.setSelectedPrId}
                isReviewing={reviewStore.isReviewing}
                triggerCodeReview={handleCodeReviewTrigger}
                activeReview={reviewStore.activeReview}
                comments={reviewStore.comments}
                hoveredCommentId={reviewStore.hoveredCommentId}
                setHoveredCommentId={reviewStore.setHoveredCommentId}
                hoveredLineNum={reviewStore.hoveredLineNum}
                setHoveredLineNum={reviewStore.setHoveredLineNum}
              />
            )}
          </div>
        )}

        {/* VIEW: House Style */}
        {activeTab === "style" && (
          <HouseStyle
            newConventionText={reviewStore.newConventionText}
            setNewConventionText={reviewStore.setNewConventionText}
            handleApplyConvention={reviewStore.handleApplyConvention}
          />
        )}

        {/* VIEW: Settings */}
        {activeTab === "settings" && <Settings />}
      </div>

      {/* Floating Websocket Logs Panel */}
      <WebSocketConsole
        showLogs={wsStore.showLogs}
        setShowLogs={wsStore.setShowLogs}
        isReviewing={reviewStore.isReviewing}
        wsLogs={wsStore.wsLogs}
      />

      {/* Footer */}
      <Footer />
    </div>
  );
}
