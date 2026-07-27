import json
from typing import NamedTuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from codereviewer.providers.fake import FakeLlmProvider
from codereviewer.reviewer.agent import run_review
from codereviewer.reviewer.analyzers import register_default_analyzers
from codereviewer.schemas.enums import ConventionSource, SymbolKind
from codereviewer.schemas.models import CodeChunk, Convention, RetrievedContext


class ExpectedFinding(NamedTuple):
    file_path: str
    line: int
    severity: str
    pattern: str


class UnexpectedFinding(NamedTuple):
    file_path: str
    line: int
    pattern: str


class GoldenPR(NamedTuple):
    id: int
    title: str
    diff_content: str
    retrieved_chunks: list[CodeChunk]
    retrieved_conventions: list[Convention]
    mock_llm_response: str
    expected_findings: list[ExpectedFinding]
    unexpected_findings: list[UnexpectedFinding]


GOLDEN_SET = [
    # Golden PR 1: Guava NullPointer check replacement
    GoldenPR(
        id=1,
        title="Check preconditions checkNotNull",
        diff_content=(
            "diff --git a/Multimap.java b/Multimap.java\n"
            "--- a/Multimap.java\n"
            "+++ b/Multimap.java\n"
            "@@ -10,6 +10,9 @@\n"
            " public class Multimap {\n"
            "   private final Map map;\n"
            "   public Multimap(Map map) {\n"
            "+    if (map == null) {\n"
            '+      throw new NullPointerException("map cannot be null");\n'
            "+    }\n"
            "     this.map = map;\n"
            "   }\n"
            " }\n"
        ),
        retrieved_chunks=[
            CodeChunk(
                id=10,
                symbol_kind=SymbolKind.function,
                symbol_name="Multimap",
                start_line=5,
                end_line=15,
                content="public Multimap(Map map) {\n  Preconditions.checkNotNull(map);\n}",
                token_count=10,
            )
        ],
        retrieved_conventions=[
            Convention(
                id=20,
                title="Always Use Preconditions",
                description="Check method arguments using Guava's Preconditions utility class.",
                source=ConventionSource.inferred,
                confidence=0.98,
            )
        ],
        mock_llm_response=json.dumps(
            [
                {
                    "file_path": "Multimap.java",
                    "line": 14,
                    "side": "right",
                    "severity": "must_fix",
                    "body": (
                        "Instead of throwing raw NullPointerException, use "
                        "Preconditions.checkNotNull(map) to align with standard practice."
                    ),
                    "suggested_patch": "Preconditions.checkNotNull(map);",
                    "citation_ids": [10],
                    "citation_conventions": ["Always Use Preconditions"],
                }
            ]
        ),
        expected_findings=[
            ExpectedFinding(
                file_path="Multimap.java",
                line=14,
                severity="must_fix",
                pattern="Preconditions.checkNotNull",
            )
        ],
        unexpected_findings=[],
    ),
    # Golden PR 2: No comments on clean code (verifying absence of false positives)
    GoldenPR(
        id=2,
        title="Clean Java Stream usage",
        diff_content=(
            "diff --git a/Utils.java b/Utils.java\n"
            "--- a/Utils.java\n"
            "+++ b/Utils.java\n"
            "@@ -30,6 +30,8 @@\n"
            "   public List getKeys() {\n"
            "     return map.keySet().stream().collect(Collectors.toList());\n"
            "   }\n"
        ),
        retrieved_chunks=[],
        retrieved_conventions=[
            Convention(
                id=21,
                title="Prefer Standard Java Streams",
                description="Avoid using loop structures when mapping or filtering collections.",
                source=ConventionSource.inferred,
                confidence=0.94,
            )
        ],
        mock_llm_response=json.dumps([]),  # no comments emitted
        expected_findings=[],
        unexpected_findings=[
            UnexpectedFinding(
                file_path="Utils.java",
                line=31,
                pattern="loop",
            )
        ],
    ),
]


@pytest.mark.eval
@pytest.mark.anyio
async def test_review_quality_eval_harness() -> None:
    """Gates build on Golden Set evaluation metrics (Precision >= 70%, FPR <= 15%)."""
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for pr in GOLDEN_SET:
        # Mock database session
        session = AsyncMock()
        session.add = MagicMock()

        # Mock LLM provider with custom response per PR
        llm = FakeLlmProvider(default_response=pr.mock_llm_response)
        register_default_analyzers(llm)

        # Mock Retriever
        retriever = MagicMock()
        mock_context = RetrievedContext(
            chunks=pr.retrieved_chunks,
            conventions=pr.retrieved_conventions,
        )
        retriever.retrieve_context = AsyncMock(return_value=mock_context)

        # Run Review Agent
        await run_review(
            session=session,
            provider=llm,
            retriever=retriever,
            pull_request_id=pr.id,
            repository_id=1,
            diff_content=pr.diff_content,
            commit_sha="commit_sha",
        )

        # Retrieve actual comments generated
        added_objs = [call[0][0] for call in session.add.call_args_list]
        actual_comments = [c for c in added_objs if c.__class__.__name__ == "ReviewComment"]

        # Track matched expected findings
        matched_expected = set()

        for comment in actual_comments:
            matched_any_expected = False
            # Check if this comment matches any expected finding
            for i, expected in enumerate(pr.expected_findings):
                if (
                    comment.file_path == expected.file_path
                    and comment.line == expected.line
                    and comment.severity.value == expected.severity
                    and expected.pattern in comment.body
                ):
                    true_positives += 1
                    matched_expected.add(i)
                    matched_any_expected = True
                    break

            if not matched_any_expected:
                # Check if it was an unexpected finding or simply an extra comment (FP)
                false_positives += 1

        # Any expected finding not matched is a False Negative
        fn_count = len(pr.expected_findings) - len(matched_expected)
        false_negatives += fn_count

    # Calculate final metrics
    total_actual = true_positives + false_positives
    total_expected = true_positives + false_negatives

    precision = (true_positives / total_actual) if total_actual > 0 else 1.0
    recall = (true_positives / total_expected) if total_expected > 0 else 1.0
    false_positive_rate = (false_positives / total_actual) if total_actual > 0 else 0.0

    print("\n--- EVALUATION METRICS ---")
    print(f"True Positives: {true_positives}")
    print(f"False Positives: {false_positives}")
    print(f"False Negatives: {false_negatives}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall: {recall:.2%}")
    print(f"False Positive Rate: {false_positive_rate:.2%}")

    # Enforce quality standards gating build
    # Precision must be >= 70%
    assert precision >= 0.70, f"Precision {precision:.2%} is below target 70%"
    # False Positive Rate must be <= 15%
    assert false_positive_rate <= 0.15, (
        f"False Positive Rate {false_positive_rate:.2%} is above target 15%"
    )
