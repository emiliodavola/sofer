"""Semantic type inference for dataset columns.

Maps a column's values to a semantic type — "what kind of data is this?" —
with a deterministic confidence. Detectors are plugin-style: each subclass of
:class:`SemanticDetector` answers one "is this column type X?" question, and
:func:`infer_semantic_types` runs every registered detector over a column's
values, collecting the non-``None`` results.

Confidence is ``round(match_rate x prior, CONFIDENCE_ROUND_DIGITS)``, where the
prior is read from ``config.SEMANTIC_PRIORS`` at detect time — never a hardcoded
class attribute (AGENTS.md rule 1), so recalibration is a TOML edit rather than
a code change. The result is a :class:`Detection` whose ``status`` is derived
from the confidence against the config-driven ``confirm_threshold`` and
``min_threshold``.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import config
from ._patterns import EMAIL_PATTERN
from ._sentinels import MISSING_VALUE_SENTINELS
from .model import InferenceStatus


@dataclass(frozen=True)
class Detection:
    """Result of a semantic detector run over a column.

    Attributes:
        type:       Semantic type name (e.g. ``"email"``).
        match_rate: Fraction of non-missing values matching the pattern.
        confidence: ``round(match_rate x prior, CONFIDENCE_ROUND_DIGITS)``.
        status:     Derived status — ``confirmed`` / ``inferred`` / ``unknown``.
    """

    type: str
    match_rate: float
    confidence: float
    status: InferenceStatus


def _is_missing(value: str) -> bool:
    """Return ``True`` when ``value`` is whitespace-only or a missing sentinel.

    Missing values (``""``, ``"NA"``, whitespace, etc.) are excluded from the
    match-rate numerator and denominator (spec STI-01), so they neither help
    nor hurt a detector's confidence.
    """
    cleaned = value.strip()
    return not cleaned or cleaned.upper() in MISSING_VALUE_SENTINELS


class SemanticDetector(ABC):
    """Abstract base for a "what kind of data is this column?" detector.

    A subclass sets :attr:`name` (the key into ``config.SEMANTIC_PRIORS``) and
    :attr:`pattern` (a compiled regex) and implements :meth:`detect`. The
    shared detection algorithm — compute the match rate over non-missing values,
    gate on ``detect_threshold``, and build a :class:`Detection` with a rounded
    confidence and derived status — lives in :meth:`_evaluate` so it is written
    once, not copied into every detector (AGENTS.md rule 4).
    """

    name: str
    pattern: re.Pattern[str]

    @property
    def prior(self) -> float:
        """Resolve this detector's prior from config, keyed by :attr:`name`.

        Raises:
            ValueError: When ``name`` has no entry in ``SEMANTIC_PRIORS`` — a
                missing prior is a config error surfaced loudly, not a silent
                :class:`KeyError` (design review fix).
        """
        try:
            return config.SEMANTIC_PRIORS[self.name]
        except KeyError as exc:
            raise ValueError(f"no semantic prior configured for detector '{self.name}'") from exc

    @abstractmethod
    def detect(self, values: list[str]) -> Detection | None:
        """Return a :class:`Detection` if the column matches, else ``None``.

        Returns ``None`` when the match rate is below ``detect_threshold`` —
        the "not this type" signal, distinct from a returned :class:`Detection`
        whose ``status`` is ``unknown`` (spec STI-01/STI-04).
        """
        raise NotImplementedError

    def _match_rate(self, values: list[str]) -> float:
        """Fraction of non-missing values matching :attr:`pattern`.

        Missing values (whitespace-only or a sentinel) are excluded from both
        the numerator and the denominator. An all-missing (or empty) column
        yields ``0.0``.
        """
        non_missing = [v for v in values if not _is_missing(v)]
        if not non_missing:
            return 0.0
        matches = sum(1 for v in non_missing if self.pattern.search(v))
        return matches / len(non_missing)

    def _evaluate(self, values: list[str]) -> Detection | None:
        """Shared detection algorithm for regex-based detectors.

        Computes the match rate over non-missing values, returns ``None`` when
        it is below ``DETECT_THRESHOLD``, and otherwise builds a
        :class:`Detection` with ``confidence = round(match_rate x prior,
        CONFIDENCE_ROUND_DIGITS)`` and a status derived via
        :func:`infer_status`.
        """
        match_rate = self._match_rate(values)
        if match_rate < config.DETECT_THRESHOLD:
            return None
        confidence = round(match_rate * self.prior, config.CONFIDENCE_ROUND_DIGITS)
        return Detection(
            type=self.name,
            match_rate=match_rate,
            confidence=confidence,
            status=infer_status(confidence),
        )


class EmailDetector(SemanticDetector):
    """Detects email columns using the shared :data:`EMAIL_PATTERN`.

    The prior is read from ``[tool.sofer] semantic_priors.email`` at detect time
    via :attr:`SemanticDetector.prior` — not a hardcoded class attribute.
    """

    name = "email"
    pattern = EMAIL_PATTERN

    def detect(self, values: list[str]) -> Detection | None:
        return self._evaluate(values)


def infer_status(confidence: float) -> InferenceStatus:
    """Derive a status from confidence against the config thresholds.

    ``confirmed`` when ``confidence >= confirm_threshold``, ``inferred`` when
    ``min_threshold <= confidence < confirm_threshold``, and ``unknown``
    otherwise (spec STI-04). Both thresholds come from config, never inline
    literals.
    """
    if confidence >= config.CONFIRM_THRESHOLD:
        return InferenceStatus.CONFIRMED
    if confidence >= config.MIN_THRESHOLD:
        return InferenceStatus.INFERRED
    return InferenceStatus.UNKNOWN


# Plugin registry: every concrete detector instance, in run order. Extending
# inference is a matter of appending a new detector here — the orchestrator
# below never changes.
_DETECTORS: list[SemanticDetector] = [EmailDetector()]


def infer_semantic_types(values: list[str]) -> list[Detection]:
    """Run every registered detector over a column and collect the results.

    Detectors that return ``None`` (match rate below ``detect_threshold``) are
    dropped, so the returned list holds one :class:`Detection` per matching
    type — empty when no detector matches (spec STI-01).
    """
    detections: list[Detection] = []
    for detector in _DETECTORS:
        detection = detector.detect(values)
        if detection is not None:
            detections.append(detection)
    return detections
