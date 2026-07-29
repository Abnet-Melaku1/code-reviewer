import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { type Repository, fetchRepos, createRepo, updateRepoPosting } from "../store";

export function useRepoStore() {
  const queryClient = useQueryClient();
  const [activeRepoId, setActiveRepoId] = useState<number>(0);
  const [newRepoOwner, setNewRepoOwner] = useState("");
  const [newRepoName, setNewRepoName] = useState("");
  const [newRepoBranch, setNewRepoBranch] = useState("main");

  // Query: Fetch all repositories
  const { data: repos = [] } = useQuery<Repository[]>({
    queryKey: ["repositories"],
    queryFn: fetchRepos,
  });

  // Automatically select the first repository once loaded if activeRepoId is not set
  React.useEffect(() => {
    if (repos.length > 0 && activeRepoId === 0) {
      setActiveRepoId(repos[0].id);
    }
  }, [repos, activeRepoId]);

  // Mutation: Register new repository
  const createRepoMutation = useMutation({
    mutationFn: ({ owner, name, branch }: { owner: string; name: string; branch: string }) =>
      createRepo(owner, name, branch),
    onSuccess: (newRepo) => {
      // Invalidate cache list and select new repo
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
      setActiveRepoId(newRepo.id);
      setNewRepoOwner("");
      setNewRepoName("");
      setNewRepoBranch("main");
    },
    onError: (err) => {
      console.error("Failed to register repository:", err);
    },
  });

  const handleAddRepo = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoOwner || !newRepoName) return;
    createRepoMutation.mutate({
      owner: newRepoOwner,
      name: newRepoName,
      branch: newRepoBranch,
    });
  };

  // Mutation: Toggle GitHub commenting settings
  const togglePostingMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      updateRepoPosting(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories"] });
    },
    onError: (err) => {
      console.error("Failed to toggle posting enabled:", err);
    },
  });

  const togglePostingEnabled = (id: number) => {
    const repo = repos.find((r) => r.id === id);
    if (!repo) return;
    togglePostingMutation.mutate({
      id,
      enabled: !repo.posting_enabled,
    });
  };

  const activeRepo = repos.find((r) => r.id === activeRepoId) || repos[0];

  return {
    repos,
    activeRepoId,
    setActiveRepoId,
    newRepoOwner,
    setNewRepoOwner,
    newRepoName,
    setNewRepoName,
    newRepoBranch,
    setNewRepoBranch,
    activeRepo,
    handleAddRepo,
    togglePostingEnabled,
  };
}
