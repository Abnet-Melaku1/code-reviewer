from enum import StrEnum


class Severity(StrEnum):
    """Severity of a review comment, listed most to least urgent.

    A ``StrEnum`` so values serialize as plain strings across the API and DB
    boundaries. This is the single source of truth for severities.

    Note: members compare lexicographically, not by urgency. To rank by urgency,
    use an explicit mapping rather than ``<``/``sorted``.
    """

    must_fix = "must_fix"
    suggestion = "suggestion"
    nit = "nit"
    context = "context"
