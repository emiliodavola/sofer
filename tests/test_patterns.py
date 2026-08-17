"""Tests for sofer._patterns — shared regexes.

``_patterns.py`` holds regexes shared across detector modules (semantic and
PII) so that one definition serves both, avoiding duplication and the
semantic↔pii circular import that would otherwise result.
"""

from __future__ import annotations

import re

from sofer._patterns import EMAIL_PATTERN


class TestEmailPattern:
    """EMAIL_PATTERN is the single source of truth for email shape."""

    def test_is_compiled_pattern(self):
        """EMAIL_PATTERN must be a compiled regex Pattern object."""
        assert isinstance(EMAIL_PATTERN, re.Pattern)

    def test_matches_valid_email(self):
        """A typical email address must match."""
        assert EMAIL_PATTERN.search("user@example.com") is not None

    def test_matches_email_with_subdomain(self):
        """Emails with subdomains and plus addressing must match."""
        assert EMAIL_PATTERN.search("first.last+tag@sub.example.org") is not None

    def test_rejects_non_email(self):
        """Plain text must not match."""
        assert EMAIL_PATTERN.search("not-an-email") is None

    def test_rejects_missing_at(self):
        """A string with a dot but no @ must not match."""
        assert EMAIL_PATTERN.search("user.example.com") is None
