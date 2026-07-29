import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useWebSocketStore(
  selectedPrId: number | null,
  reloadPrComments: () => void,
  setIsReviewing: (val: boolean) => void
) {
  const queryClient = useQueryClient();
  const [wsLogs, setWsLogs] = useState<Array<{ type: "info" | "success" | "error"; text: string }>>([
    { type: "info", text: "[WS] Initializing WebSocket gateway subscriber..." },
  ]);
  const [showLogs, setShowLogs] = useState(false);

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
          queryClient.invalidateQueries({ queryKey: ["repositories"] });
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
  }, [selectedPrId, reloadPrComments, setIsReviewing, queryClient]);

  return {
    wsLogs,
    setWsLogs,
    showLogs,
    setShowLogs,
  };
}
