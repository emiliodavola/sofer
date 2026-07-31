"""Tests for data_uploader._sentinels — shared missing-value sentinel set."""

from data_uploader._sentinels import MISSING_VALUE_SENTINELS


class TestMissingValueSentinels:
    """The shared sentinel set is the single source of truth."""

    def test_empty_string_is_sentinel(self):
        """Empty string should be treated as missing."""
        assert "" in MISSING_VALUE_SENTINELS

    def test_common_na_variants(self):
        """Standard N/A markers should be sentinels."""
        assert "N/A" in MISSING_VALUE_SENTINELS
        assert "NA" in MISSING_VALUE_SENTINELS
        assert "n/a" in MISSING_VALUE_SENTINELS
        assert "na" in MISSING_VALUE_SENTINELS

    def test_null_variants(self):
        """SQL and Python null markers should be sentinels."""
        assert "null" in MISSING_VALUE_SENTINELS
        assert "NULL" in MISSING_VALUE_SENTINELS
        assert "None" in MISSING_VALUE_SENTINELS

    def test_space_is_sentinel(self):
        """Bare space should be treated as missing."""
        assert " " in MISSING_VALUE_SENTINELS

    def test_dash_markers(self):
        """Dash-based missing markers should be sentinels."""
        assert "-" in MISSING_VALUE_SENTINELS
        assert "--" in MISSING_VALUE_SENTINELS

    def test_question_marks(self):
        """Question-mark missing markers should be sentinels."""
        assert "??" in MISSING_VALUE_SENTINELS

    def test_backward_compat_sentinels(self):
        """Original sentinel values from the three legacy sets should still be present."""
        # From repo_compliance._NULL_SENTINELS and quality._EMPTY_SENTINELS
        assert "NOTAPPLICABLE" in MISSING_VALUE_SENTINELS
        assert "MISSING" in MISSING_VALUE_SENTINELS

    def test_is_frozenset(self):
        """The constant should be a frozenset (immutable)."""
        assert isinstance(MISSING_VALUE_SENTINELS, frozenset)

    def test_case_insensitive_upper_match(self):
        """Calling .upper() on any lowercase entry should produce a value in the set."""
        lowercase_entries = [s for s in MISSING_VALUE_SENTINELS if s != s.upper()]
        for entry in lowercase_entries:
            assert entry.upper() in MISSING_VALUE_SENTINELS, (
                f"'{entry}'.upper() = '{entry.upper()}' is not in MISSING_VALUE_SENTINELS"
            )


class TestSentinelModuleConsistency:
    """Every consumer imports the same sentinel set."""

    def test_codebook_uses_shared_sentinels(self):
        """codebook.infer_column_type should reference the shared set."""
        from data_uploader.codebook import infer_column_type

        # Smoke-test: the function should still be callable after the refactor
        result = infer_column_type(["1", "2", "3"])
        assert result == "numeric"

    def test_quality_uses_shared_sentinels(self):
        """quality._is_empty should reference the shared set."""
        from data_uploader.quality import _is_empty

        assert _is_empty("") is True
        assert _is_empty("NA") is True
        assert _is_empty("NULL") is True
        assert _is_empty("hello") is False

    def test_repo_compliance_uses_shared_sentinels(self):
        """repo_compliance should reference the shared set (no _NULL_SENTINELS)."""
        # Verify _NULL_SENTINELS is gone and MISSING_VALUE_SENTINELS is available
        from data_uploader import repo_compliance

        assert not hasattr(repo_compliance, "_NULL_SENTINELS"), (
            "_NULL_SENTINELS should no longer exist in repo_compliance"
        )
        assert hasattr(repo_compliance, "MISSING_VALUE_SENTINELS"), (
            "MISSING_VALUE_SENTINELS should be accessible via repo_compliance"
        )

    def test_shared_sentinel_identity(self):
        """All three modules should reference the exact same frozenset object."""
        from data_uploader._sentinels import MISSING_VALUE_SENTINELS as SRC
        from data_uploader.codebook import MISSING_VALUE_SENTINELS as CB
        from data_uploader.quality import MISSING_VALUE_SENTINELS as Q
        from data_uploader.repo_compliance import MISSING_VALUE_SENTINELS as RC

        assert SRC is CB is Q is RC, "All modules must reference the same frozenset object"
