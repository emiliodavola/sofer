"""Issue #395 — profile and codebook must agree on ragged CSV rows.

The same file used to yield ``0.0%`` missing in the profile and ``33.3%`` in the
codebook for the same column, because the codebook padded a short row while the
profile skipped the missing field. Both readers now share one width policy and
report the counters that policy produces.
"""

from __future__ import annotations

import yaml

from sofer._csv_reader import read_columns
from sofer.codebook import generate as generate_codebook
from sofer.profile import profile

RAGGED = "id;valor\nA;10\nB\nC;30;EXTRA\n"


def _ragged_csv(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text(RAGGED, encoding="utf-8")
    return path


class TestSharedWidthPolicy:
    def test_short_row_padded_and_long_row_truncated(self, tmp_path) -> None:
        """One short row pads with "", one long row truncates and is counted."""
        record = read_columns(
            _ragged_csv(tmp_path), delimiter=";", encoding="utf-8", max_sample=None
        )

        assert record.headers == ["id", "valor"]
        assert record.rows == 3
        assert record.ragged_padded == 1
        assert record.ragged_truncated == 1
        assert record.extra_fields_dropped == 1
        assert record.is_ragged is True
        assert record.columns[1] == ["10", "", "30"]

    def test_clean_file_reports_no_ragged_rows(self, tmp_path) -> None:
        path = tmp_path / "clean.csv"
        path.write_text("a;b\n1;2\n3;4\n", encoding="utf-8")

        record = read_columns(path, delimiter=";", encoding="utf-8", max_sample=None)

        assert record.rows == 2
        assert record.is_ragged is False
        assert (record.ragged_padded, record.ragged_truncated) == (0, 0)

    def test_empty_file_reports_no_rows(self, tmp_path) -> None:
        path = tmp_path / "empty.csv"
        path.write_text("", encoding="utf-8")

        record = read_columns(path, delimiter=";", encoding="utf-8", max_sample=None)

        assert record.headers == []
        assert record.rows == 0


class TestArtifactsAgree:
    def test_missing_percentage_matches_between_artifacts(self, tmp_path) -> None:
        """The acceptance criterion: one denominator, one answer."""
        path = _ragged_csv(tmp_path)
        assert profile(path, delimiter=";", encoding="utf-8") == 0
        meta = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))

        codebook = generate_codebook(path, delimiter=";", encoding="utf-8")

        valor = next(col for col in meta["structure"]["schema"] if col["name"] == "valor")
        assert valor["missing_pct"] == 33.3
        assert "| `valor` | mixed (mostly numeric) | 2 | 33.3% |" in codebook
        assert meta["file"]["rows"] == 3
        assert "**Rows:** 3" in codebook

    def test_profile_records_the_row_width_counters(self, tmp_path) -> None:
        """metadata.yaml states how the short and long rows were treated."""
        path = _ragged_csv(tmp_path)
        assert profile(path, delimiter=";", encoding="utf-8") == 0
        meta = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))

        assert meta["file"]["ragged_padded"] == 1
        assert meta["file"]["ragged_truncated"] == 1
        assert meta["file"]["extra_fields_dropped"] == 1

    def test_codebook_states_the_row_width_counters(self, tmp_path) -> None:
        """The codebook page names the padding and the dropped extra field."""
        codebook = generate_codebook(_ragged_csv(tmp_path), delimiter=";", encoding="utf-8")

        assert "**Ragged rows:**" in codebook
        assert "1 short row(s) padded with an empty value" in codebook
        assert "1 long row(s) truncated (1 extra field(s) dropped)" in codebook

    def test_clean_file_carries_no_ragged_note(self, tmp_path) -> None:
        path = tmp_path / "clean.csv"
        path.write_text("a;b\n1;2\n", encoding="utf-8")

        codebook = generate_codebook(path, delimiter=";", encoding="utf-8")
        assert profile(path, delimiter=";", encoding="utf-8") == 0
        meta = yaml.safe_load((tmp_path / "metadata.yaml").read_text(encoding="utf-8"))

        assert "Ragged rows" not in codebook
        assert meta["file"]["ragged_padded"] == 0
        assert meta["file"]["ragged_truncated"] == 0
