"""Tests for scripts/update_citation.py — CITATION.cff version sync and verify.

The sample mirrors the shape of the real CITATION.cff, including the
multi-line ``keywords:`` block, to prove the surgical line replacement
preserves every other byte of the file.
"""

from __future__ import annotations

import pytest
from update_citation import check_citation_version, main, update_citation_version

CFF_SAMPLE = """cff-version: 1.2.0
message: "If you use sofer, please cite it as below."
title: sofer
abstract: CLI tool to create and populate Hugging Face Hub dataset repositories.
version: 0.1.0
authors:
  - family-names: Correa Dávola
    given-names: Emilio
    email: emidavola@gmail.com
    orcid: ""
repository-code: "https://github.com/emiliodavola/sofer"
url: "https://github.com/emiliodavola/sofer"
license: MIT
date-released: 2025-08-01
keywords:
  - huggingface
  - datasets
  - open-data
  - cli
  - python
"""


class TestUpdateCitationVersion:
    def test_update_sets_version_and_date_released(self):
        """Update replaces both fields and preserves the rest byte-for-byte."""
        updated = update_citation_version(CFF_SAMPLE, "0.2.2", "2026-08-27")
        expected = CFF_SAMPLE.replace("version: 0.1.0", "version: 0.2.2").replace(
            "date-released: 2025-08-01", "date-released: 2026-08-27"
        )
        assert updated == expected
        # The untouched multi-line keywords block and cff-version header survive.
        assert "cff-version: 1.2.0\n" in updated
        assert (
            "keywords:\n  - huggingface\n  - datasets\n  - open-data\n  - cli\n  - python\n"
            in updated
        )

    def test_update_is_idempotent(self):
        """Running update twice with the same values changes nothing."""
        once = update_citation_version(CFF_SAMPLE, "0.2.2", "2026-08-27")
        twice = update_citation_version(once, "0.2.2", "2026-08-27")
        assert twice == once

    def test_update_raises_when_version_missing(self):
        """A CFF without a version: line is rejected with ValueError."""
        text = CFF_SAMPLE.replace("version: 0.1.0\n", "")
        with pytest.raises(ValueError, match="version"):
            update_citation_version(text, "0.2.2", "2026-08-27")

    def test_update_raises_when_date_released_missing(self):
        """A CFF without a date-released: line is rejected with ValueError."""
        text = CFF_SAMPLE.replace("date-released: 2025-08-01\n", "")
        with pytest.raises(ValueError, match="date-released"):
            update_citation_version(text, "0.2.2", "2026-08-27")


class TestCheckCitationVersion:
    def test_check_true_when_version_matches(self):
        """A CFF declaring the expected version and a date passes."""
        assert check_citation_version(CFF_SAMPLE, "0.1.0") is True

    def test_check_false_on_version_mismatch(self):
        """A version mismatch fails the check."""
        assert check_citation_version(CFF_SAMPLE, "0.2.2") is False

    def test_check_false_when_date_released_missing(self):
        """A CFF without date-released fails even when the version matches."""
        text = CFF_SAMPLE.replace("date-released: 2025-08-01\n", "")
        assert check_citation_version(text, "0.1.0") is False

    def test_check_false_when_date_released_empty(self):
        """An empty date-released: value fails the check."""
        text = CFF_SAMPLE.replace("date-released: 2025-08-01", "date-released:")
        assert check_citation_version(text, "0.1.0") is False


class TestCli:
    def test_check_exit_zero_on_match(self, tmp_path):
        """--check exits 0 when the CFF declares the expected version."""
        cff = tmp_path / "CITATION.cff"
        cff.write_text(CFF_SAMPLE, encoding="utf-8")
        rc = main(["--check", "--version", "0.1.0", "--cff-path", str(cff)])
        assert rc == 0

    def test_check_exit_one_on_mismatch(self, tmp_path):
        """--check exits 1 when the CFF does not declare the expected version."""
        cff = tmp_path / "CITATION.cff"
        cff.write_text(CFF_SAMPLE, encoding="utf-8")
        rc = main(["--check", "--version", "0.9.9", "--cff-path", str(cff)])
        assert rc == 1

    def test_check_exit_one_when_file_missing(self, tmp_path):
        """--check exits 1 when the CFF file cannot be read."""
        missing = tmp_path / "missing.cff"
        rc = main(["--check", "--version", "0.1.0", "--cff-path", str(missing)])
        assert rc == 1

    def test_update_writes_file(self, tmp_path):
        """Without --check, main updates and writes both fields in place."""
        cff = tmp_path / "CITATION.cff"
        cff.write_text(CFF_SAMPLE, encoding="utf-8")
        rc = main(["--version", "0.2.2", "--date", "2026-08-27", "--cff-path", str(cff)])
        assert rc == 0
        written = cff.read_text(encoding="utf-8")
        assert written == CFF_SAMPLE.replace("version: 0.1.0", "version: 0.2.2").replace(
            "date-released: 2025-08-01", "date-released: 2026-08-27"
        )

    def test_malformed_date_exits_one(self, tmp_path):
        """A malformed --date value is rejected with exit 1."""
        cff = tmp_path / "CITATION.cff"
        cff.write_text(CFF_SAMPLE, encoding="utf-8")
        rc = main(["--version", "0.2.2", "--date", "2026-08-32", "--cff-path", str(cff)])
        assert rc == 1
        # The file must not have been touched.
        assert cff.read_text(encoding="utf-8") == CFF_SAMPLE

    def test_missing_field_exits_one(self, tmp_path):
        """A CFF missing a required field is rejected with exit 1."""
        cff = tmp_path / "CITATION.cff"
        cff.write_text(CFF_SAMPLE.replace("date-released: 2025-08-01\n", ""), encoding="utf-8")
        rc = main(["--version", "0.2.2", "--date", "2026-08-27", "--cff-path", str(cff)])
        assert rc == 1
