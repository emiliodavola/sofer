"""Tests for sofer.pii — heuristic PII detection.

Covers the Phase 3 (WU3) detectors: the ``PiiDetection`` finding shape
(PII-02), the ``note``-always-``"possible_pii"`` rule (PII-03), the
``PiiDetector`` contract (PII-01), ``confidence = match_rate x prior`` rounded
to ``CONFIDENCE_ROUND_DIGITS``, the non-missing match-rate denominator, the
email PII detector (PII-04), the ``detect_threshold`` boundary, the
missing-prior ValueError, and ``infer_pii_types`` aggregation.
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from sofer.pii import (
    EmailPiiDetector,
    PiiDetection,
    PiiDetector,
    infer_pii_types,
)


class TestPiiDetectionShape:
    """PiiDetection carries label, confidence, and note (PII-02)."""

    def test_fields_present(self):
        finding = PiiDetection(label="email", confidence=0.72)
        assert finding.label == "email"
        assert finding.confidence == 0.72
        assert finding.note == "possible_pii"

    def test_note_defaults_to_possible_pii(self):
        finding = PiiDetection(label="email", confidence=0.98)
        assert finding.note == "possible_pii"

    def test_frozen(self):
        finding = PiiDetection(label="email", confidence=0.98)
        with pytest.raises(FrozenInstanceError):
            setattr(finding, "label", "phone")


class TestPiiDetectorContract:
    """PiiDetector is abstract; EmailPiiDetector is concrete (PII-01)."""

    def test_pii_detector_is_abstract(self):
        import inspect

        assert inspect.isabstract(PiiDetector)

    def test_email_pii_detector_is_subclass(self):
        assert issubclass(EmailPiiDetector, PiiDetector)

    def test_email_pii_detector_has_name_and_pattern(self):
        detector = EmailPiiDetector()
        assert detector.name == "email"
        assert isinstance(detector.pattern, re.Pattern)


class TestNoteAlwaysPossible:
    """note is always "possible_pii", never a categorical verdict (PII-03)."""

    def test_high_confidence_email_note_is_possible_pii(self):
        detector = EmailPiiDetector()
        finding = detector.detect(["a@b.co", "c@d.co", "e@f.co"])
        assert finding is not None
        assert finding.note == "possible_pii"

    def test_note_never_asserts_containment(self):
        detector = EmailPiiDetector()
        finding = detector.detect(["a@b.co", "c@d.co"])
        assert finding is not None
        assert finding.note != "contains_pii"
        assert finding.note != "contains PII"
        assert "contains" not in finding.note


class TestConfidence:
    """confidence = round(match_rate x prior, CONFIDENCE_ROUND_DIGITS)."""

    def test_confidence_rounding_uses_config_prior(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {"email": 0.9})
        monkeypatch.setattr("sofer.config.CONFIDENCE_ROUND_DIGITS", 4)
        detector = EmailPiiDetector()
        # 4 emails + 1 non-email => match_rate = 0.8
        values = ["a@b.co", "c@d.co", "e@f.co", "g@h.co", "not-an-email"]
        finding = detector.detect(values)
        assert finding is not None
        assert finding.confidence == pytest.approx(0.72)

    def test_confidence_deterministic(self):
        detector = EmailPiiDetector()
        values = ["a@b.co", "c@d.co", "e@f.co"]
        first = detector.detect(values)
        second = detector.detect(values)
        assert first is not None and second is not None
        assert first.confidence == second.confidence


class TestMatchRateDenominator:
    """match_rate counts non-missing values only (mirrors STI-01)."""

    def test_missing_values_excluded_from_denominator(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {"email": 1.0})
        detector = EmailPiiDetector()
        # 4 emails + 2 missing => match_rate = 4/4 = 1.0, not 4/6
        values = ["a@b.co", "c@d.co", "e@f.co", "g@h.co", "", "NA"]
        finding = detector.detect(values)
        assert finding is not None
        assert finding.confidence == pytest.approx(1.0)

    def test_missing_and_non_matching_denominator(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {"email": 1.0})
        detector = EmailPiiDetector()
        # 3 emails + 1 non-email + 2 missing => match_rate = 3/4 = 0.75
        values = ["a@b.co", "c@d.co", "e@f.co", "hello", "", "NA"]
        finding = detector.detect(values)
        assert finding is not None
        assert finding.confidence == pytest.approx(0.75)

    def test_all_missing_returns_none(self):
        detector = EmailPiiDetector()
        assert detector.detect(["", "NA", " "]) is None


class TestDetectThresholdBoundary:
    """match_rate below DETECT_THRESHOLD -> None; at/above -> finding."""

    def test_below_detect_threshold_returns_none(self):
        detector = EmailPiiDetector()
        # 1 email + 3 non-emails => match_rate = 0.25 < 0.5
        values = ["a@b.co", "foo", "bar", "baz"]
        assert detector.detect(values) is None

    def test_at_detect_threshold_returns_finding(self):
        detector = EmailPiiDetector()
        # 2 emails + 2 non-emails => match_rate = 0.5 == threshold
        values = ["a@b.co", "c@d.co", "foo", "bar"]
        finding = detector.detect(values)
        assert finding is not None
        assert isinstance(finding, PiiDetection)


class TestEmailPiiDetector:
    """EmailPiiDetector flags email columns as possible PII (PII-04)."""

    def test_email_column_flagged(self):
        detector = EmailPiiDetector()
        finding = detector.detect(["a@b.co", "c@d.co", "e@f.co"])
        assert finding is not None
        assert finding.label == "email"
        assert finding.note == "possible_pii"

    def test_non_email_column_returns_none(self):
        detector = EmailPiiDetector()
        assert detector.detect(["hello", "world", "foo bar"]) is None


class TestMissingPrior:
    """A detector whose name has no configured prior raises ValueError."""

    def test_prior_property_raises_value_error(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {})
        detector = EmailPiiDetector()
        with pytest.raises(ValueError, match="email"):
            _ = detector.prior

    def test_detect_raises_when_prior_missing(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {})
        detector = EmailPiiDetector()
        values = ["a@b.co", "c@d.co"]
        with pytest.raises(ValueError, match="email"):
            detector.detect(values)


class TestInferPiiTypes:
    """infer_pii_types aggregates all registered PII detectors."""

    def test_email_column_produces_one_finding(self):
        findings = infer_pii_types(["a@b.co", "c@d.co", "e@f.co"])
        assert len(findings) == 1
        assert findings[0].label == "email"
        assert findings[0].note == "possible_pii"

    def test_non_email_column_produces_no_findings(self):
        findings = infer_pii_types(["hello", "world"])
        assert findings == []
