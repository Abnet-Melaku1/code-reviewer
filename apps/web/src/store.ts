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

// Initial mock data
const INITIAL_REPOS: Repository[] = [
  {
    id: 1,
    owner: "google",
    name: "guava",
    default_branch: "master",
    index_status: "ready",
    posting_enabled: true,
  },
  {
    id: 2,
    owner: "django",
    name: "django",
    default_branch: "main",
    index_status: "indexing",
    posting_enabled: false,
  },
  {
    id: 3,
    owner: "owner",
    name: "repo",
    default_branch: "main",
    index_status: "pending",
    posting_enabled: false,
  },
];

const INITIAL_CONVENTIONS: Convention[] = [
  {
    id: 1,
    repository_id: 1,
    name: "Prefer Standard Java Streams",
    description: "Avoid using loop structures when mapping or filtering collections. Use standard Java streams instead.",
    severity: "suggestion",
    confidence: 0.94,
    is_active: true,
  },
  {
    id: 2,
    repository_id: 1,
    name: "Always Use Preconditions",
    description: "Check method arguments using Guava's Preconditions utility class at the start of public functions.",
    severity: "must-fix",
    confidence: 0.98,
    is_active: true,
  },
  {
    id: 3,
    repository_id: 1,
    name: "Use @Nullable for Optional Arguments",
    description: "Ensure optional method parameters are annotated with javax.annotation.Nullable.",
    severity: "nit",
    confidence: 0.85,
    is_active: true,
  },
];

const INITIAL_PRS: PullRequest[] = [
  {
    id: 1,
    repository_id: 1,
    number: 42,
    title: "refactor(collections): optimize Multimap implementation",
    author: "octocat",
    head_sha: "98da24f",
    base_sha: "1324ab2",
    state: "open",
  },
];

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

const INITIAL_COMMENTS: ReviewComment[] = [
  {
    id: 1,
    review_id: 1,
    path: "guava/src/com/google/common/collect/CustomMultimap.java",
    line: 16,
    body: "Instead of throwing raw NullPointerException, use `Preconditions.checkNotNull(map)` to align with the codebase's standard practices.",
    patch: "Preconditions.checkNotNull(map);",
    severity: "must-fix",
    citations: [
      {
        type: "convention",
        name: "Always Use Preconditions",
        description: "Check method arguments using Guava's Preconditions utility class at the start of public functions.",
      },
      {
        type: "chunk",
        name: "AbstractMultimap.java:L45-50",
        description: "Guava AbstractMultimap constructor checking params using Preconditions.checkNotNull.",
      },
    ],
  },
  {
    id: 2,
    review_id: 1,
    path: "guava/src/com/google/common/collect/CustomMultimap.java",
    line: 35,
    body: "Make sure `Collectors.toList()` is imported or use full class names. Standard practice is to statically import Collectors helper methods.",
    patch: "import static java.util.stream.Collectors.toList;",
    severity: "nit",
    citations: [
      {
        type: "chunk",
        name: "CollectionUtils.java:L12-15",
        description: "Static import utility matches in similar collections utility classes.",
      },
    ],
  },
];

// LocalStorage Helper functions
export function getSavedRepos(): Repository[] {
  const data = localStorage.getItem("cr_repos");
  if (!data) {
    localStorage.setItem("cr_repos", JSON.stringify(INITIAL_REPOS));
    return INITIAL_REPOS;
  }
  return JSON.parse(data);
}

export function saveRepos(repos: Repository[]): void {
  localStorage.setItem("cr_repos", JSON.stringify(repos));
}

export function getSavedConventions(): Convention[] {
  const data = localStorage.getItem("cr_conventions");
  if (!data) {
    localStorage.setItem("cr_conventions", JSON.stringify(INITIAL_CONVENTIONS));
    return INITIAL_CONVENTIONS;
  }
  return JSON.parse(data);
}

export function saveConventions(conventions: Convention[]): void {
  localStorage.setItem("cr_conventions", JSON.stringify(conventions));
}

export function getSavedPRs(): PullRequest[] {
  const data = localStorage.getItem("cr_prs");
  if (!data) {
    localStorage.setItem("cr_prs", JSON.stringify(INITIAL_PRS));
    return INITIAL_PRS;
  }
  return JSON.parse(data);
}

export function savePRs(prs: PullRequest[]): void {
  localStorage.setItem("cr_prs", JSON.stringify(prs));
}

export function getSavedComments(): ReviewComment[] {
  const data = localStorage.getItem("cr_comments");
  if (!data) {
    localStorage.setItem("cr_comments", JSON.stringify(INITIAL_COMMENTS));
    return INITIAL_COMMENTS;
  }
  return JSON.parse(data);
}

export function saveComments(comments: ReviewComment[]): void {
  localStorage.setItem("cr_comments", JSON.stringify(comments));
}
