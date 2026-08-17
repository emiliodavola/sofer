"""Tests for sofer.semantic — semantic type inference.

Covers the Phase 2 (WU2) detectors: the ``Detection`` result shape, the
``SemanticDetector`` contract, ``confidence = match_rate x prior`` rounded to
``CONFIDENCE_ROUND_DIGITS``, config-driven status thresholds, the non-missing
match-rate denominator, the email detector, and the missing-prior ValueError.
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from sofer.model import InferenceStatus
from sofer.semantic import (
    Detection,
    EmailDetector,
    SemanticDetector,
    infer_semantic_types,
    infer_status,
)


class TestDetectionShape:
    """Detection carries type, match_rate, confidence, and status (STI-02)."""

    def test_fields_present(self):
        detection = Detection(
            type="email",
            match_rate=0.8,
            confidence=0.72,
            status=InferenceStatus.CONFIRMED,
        )
        assert detection.type == "email"
        assert detection.match_rate == 0.8
        assert detection.confidence == 0.72
        assert detection.status == InferenceStatus.CONFIRMED

    def test_frozen(self):
        detection = Detection(
            type="email",
            match_rate=1.0,
            confidence=0.98,
            status=InferenceStatus.CONFIRMED,
        )
        with pytest.raises(FrozenInstanceError):
            setattr(detection, "type", "url")

    def test_status_is_inference_status(self):
        detection = Detection(
            type="email",
            match_rate=1.0,
            confidence=0.98,
            status=InferenceStatus.CONFIRMED,
        )
        assert isinstance(detection.status, InferenceStatus)


class TestDetectorContract:
    """SemanticDetector is an abstract base; EmailDetector is concrete (STI-01)."""

    def test_semantic_detector_is_abstract(self):
        import inspect

        assert inspect.isabstract(SemanticDetector)

    def test_email_detector_is_subclass(self):
        assert issubclass(EmailDetector, SemanticDetector)

    def test_email_detector_has_name_and_pattern(self):
        detector = EmailDetector()
        assert detector.name == "email"
        assert isinstance(detector.pattern, re.Pattern)


class TestConfidence:
    """confidence = round(match_rate x prior, CONFIDENCE_ROUND_DIGITS) (STI-03)."""

    def test_confidence_rounding_uses_config_prior(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {"email": 0.9})
        monkeypatch.setattr("sofer.config.CONFIDENCE_ROUND_DIGITS", 4)
        detector = EmailDetector()
        # 4 emails + 1 non-email => match_rate = 0.8
        values = ["a@b.co", "c@d.co", "e@f.co", "g@h.co", "not-an-email"]
        detection = detector.detect(values)
        assert detection is not None
        assert detection.match_rate == pytest.approx(0.8)
        assert detection.confidence == pytest.approx(0.72)

    def test_confidence_deterministic(self):
        detector = EmailDetector()
        values = ["a@b.co", "c@d.co", "e@f.co"]
        first = detector.detect(values)
        second = detector.detect(values)
        assert first is not None and second is not None
        assert first.confidence == second.confidence


class TestMatchRateDenominator:
    """match_rate counts non-missing values only (STI-01)."""

    def test_missing_values_excluded_from_denominator(self):
        detector = EmailDetector()
        # 4 emails + 2 missing => match_rate = 4/4 = 1.0, not 4/6
        values = ["a@b.co", "c@d.co", "e@f.co", "g@h.co", "", "NA"]
        detection = detector.detect(values)
        assert detection is not None
        assert detection.match_rate == pytest.approx(1.0)

    def test_missing_and_non_matching_denominator(self):
        detector = EmailDetector()
        # 3 emails + 1 non-email + 2 missing => match_rate = 3/4 = 0.75
        values = ["a@b.co", "c@d.co", "e@f.co", "hello", "", "NA"]
        detection = detector.detect(values)
        assert detection is not None
        assert detection.match_rate == pytest.approx(0.75)

    def test_all_missing_returns_none(self):
        detector = EmailDetector()
        assert detector.detect(["", "NA", " "]) is None


class TestDetectThresholdBoundary:
    """match_rate below DETECT_THRESHOLD -> None; at/above -> Detection."""

    def test_below_detect_threshold_returns_none(self):
        detector = EmailDetector()
        # 1 email + 3 non-emails => match_rate = 0.25 < 0.5
        values = ["a@b.co", "foo", "bar", "baz"]
        assert detector.detect(values) is None

    def test_at_detect_threshold_returns_detection(self):
        detector = EmailDetector()
        # 2 emails + 2 non-emails => match_rate = 0.5 == threshold
        values = ["a@b.co", "c@d.co", "foo", "bar"]
        assert detector.detect(values) is not None


class TestStatusBoundaries:
    """status derives from confidence against config thresholds (STI-04)."""

    def test_high_confidence_confirmed(self):
        assert infer_status(0.9) == InferenceStatus.CONFIRMED

    def test_mid_confidence_inferred(self):
        assert infer_status(0.6) == InferenceStatus.INFERRED

    def test_low_confidence_unknown(self):
        assert infer_status(0.3) == InferenceStatus.UNKNOWN

    def test_confirm_threshold_boundary(self):
        assert infer_status(0.8) == InferenceStatus.CONFIRMED

    def test_min_threshold_boundary(self):
        assert infer_status(0.5) == InferenceStatus.INFERRED


class TestEmailDetector:
    """EmailDetector detects email columns (STI-05)."""

    def test_email_column_detected(self):
        detector = EmailDetector()
        values = ["a@b.co", "c@d.co", "e@f.co"]
        detection = detector.detect(values)
        assert detection is not None
        assert detection.type == "email"

    def test_non_email_column_returns_none(self):
        detector = EmailDetector()
        values = ["hello", "world", "foo bar"]
        assert detector.detect(values) is None

    def test_email_detection_status_confirmed_with_default_prior(self):
        detector = EmailDetector()
        # match_rate 1.0 x prior 0.98 = 0.98 >= 0.8 -> confirmed
        detection = detector.detect(["a@b.co", "c@d.co"])
        assert detection is not None
        assert detection.status == InferenceStatus.CONFIRMED


class TestMissingPrior:
    """A detector whose name has no configured prior raises ValueError."""

    def test_prior_property_raises_value_error(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {})
        detector = EmailDetector()
        with pytest.raises(ValueError, match="email"):
            _ = detector.prior

    def test_detect_raises_when_prior_missing(self, monkeypatch):
        monkeypatch.setattr("sofer.config.SEMANTIC_PRIORS", {})
        detector = EmailDetector()
        values = ["a@b.co", "c@d.co"]
        with pytest.raises(ValueError, match="email"):
            detector.detect(values)


class TestInferSemanticTypes:
    """infer_semantic_types aggregates all registered detectors."""

    def test_email_column_produces_one_detection(self):
        detections = infer_semantic_types(["a@b.co", "c@d.co", "e@f.co"])
        assert len(detections) == 1
        assert detections[0].type == "email"

    def test_non_email_column_produces_no_detections(self):
        detections = infer_semantic_types(["hello", "world"])
        assert detections == []
