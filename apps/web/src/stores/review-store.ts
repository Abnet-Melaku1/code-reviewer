import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  type Convention,
  type PullRequest,
  type ReviewComment,
  type Review,
  fetchConventions,
  toggleConventionActive,
  createConvention,
  fetchPRs,
  fetchReviews,
  rerunReview,
  createReview,
  fetchComments,
} from "../store";

export function useReviewStore(activeRepoId: number) {
  const queryClient = useQueryClient();
  const [selectedPrId, setSelectedPrId] = useState<number | null>(null);
  const [hoveredCommentId, setHoveredCommentId] = useState<number | null>(null);
  const [hoveredLineNum, setHoveredLineNum] = useState<number | null>(null);
  const [newConventionText, setNewConventionText] = useState(
    "Avoid using default exports for components to keep IDE imports predictable."
  );
  const [isReviewing, setIsReviewing] = useState(false);

  // Query: Conventions
  const { data: conventions = [] } = useQuery<Convention[]>({
    queryKey: ["conventions", activeRepoId],
    queryFn: () => fetchConventions(activeRepoId),
    enabled: activeRepoId > 0,
  });

  // Query: Pull Requests
  const { data: prs = [] } = useQuery<PullRequest[]>({
    queryKey: ["prs", activeRepoId],
    queryFn: () => fetchPRs(activeRepoId),
    enabled: activeRepoId > 0,
  });

  // Query: Reviews for the selected PR
  const { data: reviews = [] } = useQuery<Review[]>({
    queryKey: ["reviews", selectedPrId],
    queryFn: () => fetchReviews(selectedPrId!),
    enabled: selectedPrId !== null,
  });

  const latestReview = reviews.length > 0 ? reviews[reviews.length - 1] : null;

  // Query: Inline comments linked to the latest review
  const { data: comments = [] } = useQuery<ReviewComment[]>({
    queryKey: ["comments", latestReview?.id],
    queryFn: () => fetchComments(latestReview!.id),
    enabled: latestReview !== null,
  });

  // Action: Invalidate queries to reload review comments (called by WS gateway logs complete)
  const reloadPrComments = useCallback(() => {
    if (selectedPrId) {
      queryClient.invalidateQueries({ queryKey: ["reviews", selectedPrId] });
      if (latestReview) {
        queryClient.invalidateQueries({ queryKey: ["comments", latestReview.id] });
      }
    }
  }, [selectedPrId, latestReview, queryClient]);

  // Mutation: Toggle convention active state
  const toggleConventionMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      toggleConventionActive(activeRepoId, id, active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conventions", activeRepoId] });
    },
    onError: (err) => {
      console.error("Failed to toggle convention:", err);
    },
  });

  const toggleConvention = async (id: number) => {
    const conv = conventions.find((c) => c.id === id);
    if (!conv) return;
    toggleConventionMutation.mutate({
      id,
      active: !conv.is_active,
    });
  };

  // Mutation: Teach custom rule
  const createConventionMutation = useMutation({
    mutationFn: ({ title, description }: { title: string; description: string }) =>
      createConvention(activeRepoId, title, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conventions", activeRepoId] });
      setNewConventionText("");
    },
    onError: (err) => {
      console.error("Failed to create convention:", err);
    },
  });

  const handleApplyConvention = async () => {
    if (!newConventionText || !activeRepoId) return;
    const sentence = newConventionText.trim();
    const dotIndex = sentence.indexOf(".");
    const title = dotIndex !== -1 ? sentence.substring(0, dotIndex) : sentence.substring(0, 30);
    createConventionMutation.mutate({ title, description: sentence });
  };

  // Mutation: Run / Rerun review
  const triggerReviewMutation = useMutation({
    mutationFn: async () => {
      if (!selectedPrId) return;
      const existingReviews = await fetchReviews(selectedPrId);
      if (existingReviews.length > 0) {
        const latest = existingReviews[existingReviews.length - 1];
        await rerunReview(latest.id);
      } else {
        await createReview(selectedPrId);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews", selectedPrId] });
    },
  });

  const triggerCodeReview = async (onEnqueue: () => void, onError: (msg: string) => void) => {
    if (!selectedPrId || isReviewing) return;

    setIsReviewing(true);
    onEnqueue();

    triggerReviewMutation.mutate(undefined, {
      onError: (err: any) => {
        setIsReviewing(false);
        onError(err.message);
      },
    });
  };

  // derived selectors
  const activeRepoConventions = conventions.filter((c) => c.repository_id === activeRepoId);
  const activeRepoPrs = prs.filter((p) => p.repository_id === activeRepoId);
  const selectedPr = prs.find((p) => p.id === selectedPrId);

  return {
    conventions,
    prs,
    comments,
    activeReview: latestReview,
    selectedPrId,
    setSelectedPrId,
    hoveredCommentId,
    setHoveredCommentId,
    hoveredLineNum,
    setHoveredLineNum,
    newConventionText,
    setNewConventionText,
    isReviewing,
    setIsReviewing,
    activeRepoConventions,
    activeRepoPrs,
    selectedPr,
    reloadPrComments,
    toggleConvention,
    handleApplyConvention,
    triggerCodeReview,
  };
}
