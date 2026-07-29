export interface Repository {
  id: number;
  owner: string;
  name: string;
  default_branch: string;
  index_status: "pending" | "indexing" | "ready" | "error";
  posting_enabled: boolean;
}

export interface Convention {
  id: number;
  repository_id: number;
  name: string;
  description: string;
  severity: "nit" | "suggestion" | "must-fix";
  confidence: number;
  is_active: boolean;
}

export interface PullRequest {
  id: number;
  repository_id: number;
  number: number;
  title: string;
  author: string;
  head_sha: string;
  base_sha: string;
  state: "open" | "closed";
}

export interface ReviewComment {
  id: number;
  review_id: number;
  path: string;
  line: number;
  body: string;
  patch: string | null;
  severity: "nit" | "suggestion" | "must-fix";
  citations: Array<{
    type: "convention" | "chunk";
    name: string;
    description: string;
  }>;
}

export interface Review {
  id: number;
  pull_request_id: number;
  status: "queued" | "running" | "completed" | "failed";
  summary: string;
  must_fix: number;
  suggestions: number;
  nits: number;
  tokens_prompt?: number;
  tokens_completion?: number;
  cost_cents?: number;
  latency_ms?: number;
  model: string;
}

export const MOCK_DIFF = `diff --git a/guava/src/com/google/common/collect/CustomMultimap.java b/guava/src/com/google/common/collect/CustomMultimap.java
index 1324ab2..98da24f 100644
--- a/guava/src/com/google/common/collect/CustomMultimap.java
+++ b/guava/src/com/google/common/collect/CustomMultimap.java
@@ -12,6 +12,12 @@ public class CustomMultimap<K, V> extends AbstractMultimap<K, V> {
   private final Map<K, Collection<V>> map;

   public CustomMultimap(Map<K, Collection<V>> map) {
+    if (map == null) {
+      throw new NullPointerException("map cannot be null");
+    }
     this.map = map;
   }

@@ -25,4 +31,8 @@ public class CustomMultimap<K, V> extends AbstractMultimap<K, V> {
   public List<V> getValues(K key) {
-    List<V> list = new ArrayList<>();
-    for (V value : map.get(key)) {
-      list.add(value);
-    }
-    return list;
+    return map.get(key).stream().collect(Collectors.toList());
   }
 }`;

const API_BASE = "http://localhost:8000/api/v1";

export async function fetchRepos(): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/repositories`);
  if (!res.ok) throw new Error("Failed to fetch repositories");
  return res.json();
}

export async function createRepo(
  owner: string,
  name: string,
  default_branch: string
): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      github_installation_id: Math.floor(Math.random() * 100000) + 1,
      owner,
      name,
      default_branch,
    }),
  });
  if (!res.ok) throw new Error("Failed to create repository");
  return res.json();
}

export async function updateRepoPosting(id: number, posting_enabled: boolean): Promise<Repository> {
  const res = await fetch(`${API_BASE}/repositories/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ posting_enabled }),
  });
  if (!res.ok) throw new Error("Failed to update repository settings");
  return res.json();
}

export async function reindexRepo(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/repositories/${id}/reindex`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to trigger re-index");
}

export async function fetchConventions(repoId: number): Promise<Convention[]> {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/conventions`);
  if (!res.ok) throw new Error("Failed to fetch conventions");
  const data = await res.json();
  return data.map((c: any) => ({
    id: c.id,
    repository_id: repoId,
    name: c.title,
    description: c.description,
    severity: "suggestion",
    confidence: c.confidence,
    is_active: c.active,
  }));
}

export async function createConvention(
  repoId: number,
  title: string,
  description: string
): Promise<Convention> {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/conventions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description }),
  });
  if (!res.ok) throw new Error("Failed to create convention");
  const c = await res.json();
  return {
    id: c.id,
    repository_id: repoId,
    name: c.title,
    description: c.description,
    severity: "suggestion",
    confidence: c.confidence,
    is_active: c.active,
  };
}

export async function toggleConventionActive(
  repoId: number,
  id: number,
  active: boolean
): Promise<Convention> {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/conventions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });
  if (!res.ok) throw new Error("Failed to update convention");
  const c = await res.json();
  return {
    id: c.id,
    repository_id: repoId,
    name: c.title,
    description: c.description,
    severity: "suggestion",
    confidence: c.confidence,
    is_active: c.active,
  };
}

export async function fetchPRs(repoId: number): Promise<PullRequest[]> {
  const res = await fetch(`${API_BASE}/repositories/${repoId}/pulls`);
  if (!res.ok) throw new Error("Failed to fetch pulls");
  const data = await res.json();
  return data.map((p: any) => ({
    id: p.id,
    repository_id: repoId,
    number: p.number,
    title: p.title,
    author: p.author,
    head_sha: p.head_sha,
    base_sha: p.base_sha,
    state: p.state === "open" ? "open" : "closed",
  }));
}

export async function fetchReviews(prId: number): Promise<Review[]> {
  const res = await fetch(`${API_BASE}/pulls/${prId}/reviews`);
  if (!res.ok) throw new Error("Failed to fetch reviews");
  return res.json();
}

export async function rerunReview(reviewId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/rerun`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to trigger re-run");
}

export async function createReview(prId: number): Promise<Review> {
  const res = await fetch(`${API_BASE}/pulls/${prId}/reviews`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to trigger review");
  return res.json();
}


export async function fetchComments(reviewId: number): Promise<ReviewComment[]> {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/comments`);
  if (!res.ok) throw new Error("Failed to fetch comments");
  const data = await res.json();
  return data.map((c: any) => ({
    id: c.id,
    review_id: reviewId,
    path: c.file_path,
    line: c.line,
    body: c.body,
    patch: c.suggested_patch,
    severity: c.severity === "must_fix" ? "must-fix" : c.severity,
    citations: (c.citations || []).map((cit: any) => {
      const type = cit.kind === "code_chunk" ? "chunk" : "convention";
      let name = "";
      let description = "";
      if (cit.kind === "code_chunk") {
        name = `code chunk #${cit.code_chunk_id}`;
        description = "Grounded source code reference";
      } else if (cit.kind === "convention") {
        name = `convention #${cit.convention_id}`;
        description = "Learned coding standard";
      } else {
        name = cit.diff_ref || "diff hunk";
        description = "Anchored diff hunk";
      }
      return { type, name, description };
    }),
  }));
}
