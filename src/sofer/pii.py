"""Heuristic personally identifiable information (PII) detection for columns.

Maps a column's values to a *possible* PII finding — "is this data sensitive?" —
with a deterministic confidence. Detection is heuristic and strictly advisory:
a detector flags a column as *possibly* containing PII but never asserts it
does. Every finding carries ``note = "possible_pii"`` (spec PII-03), so the
tool never emits a categorical verdict it cannot prove.

The detector hierarchy mirrors :mod:`sofer.semantic`: each subclass of
:class:`PiiDetector` answers one "is this column sensitive?" question, and
:func:`infer_pii_types` runs every registered detector over a column's values,
collecting the non-``None`` results. The two hierarchies are intentionally
separate — an email column is both ``type=email`` *and* ``possible_pii``, and a
future non-PII semantic type (e.g. ``datetime``) has no PII signal — so a
detector never has to answer both questions at once.

Confidence reuses the semantic formula: ``round(match_rate x prior,
CONFIDENCE_ROUND_DIGITS)``, with the prior read from ``config.SEMANTIC_PRIORS``
at detect time. This is a documented MVP conflation — PII and semantic email
share the same ``email`` prior, since both judge the same ``@``+TLD structure. A
dedicated ``pii_priors`` config key is a later phase.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import config
from ._patterns import EMAIL_PATTERN
from .semantic import _is_missing


@dataclass(frozen=True)
class PiiDetection:
    """Result of a PII detector run over a column — always advisory.

    Attributes:
        label:      PII label (e.g. ``"email"``), sourced from the detector name.
        confidence: ``round(match_rate x prior, CONFIDENCE_ROUND_DIGITS)``.
        note:       Always the literal ``"possible_pii"`` — never a categorical
                    verdict such as ``"contains_pii"`` (spec PII-03).
    """

    label: str
    confidence: float
    note: str = "possible_pii"


class PiiDetector(ABC):
    """Abstract base for an "is this column sensitive?" detector.

    A subclass sets :attr:`name` (the key into ``config.SEMANTIC_PRIORS`` — see
    the MVP conflation note in the module docstring) and :attr:`pattern` (a
    compiled regex) and implements :meth:`detect`. The shared detection
    algorithm — compute the match rate over non-missing values, gate on
    ``detect_threshold``, and build a :class:`PiiDetection` with a rounded
    confidence — lives in :meth:`_evaluate` so it is written once, not copied
    into every detector (AGENTS.md rule 4).
    """

    name: str
    pattern: re.Pattern[str]

    @property
    def prior(self) -> float:
        """Resolve this detector's prior from config, keyed by :attr:`name`.

        Reads ``config.SEMANTIC_PRIORS`` (documented MVP conflation with the
        semantic email prior).

        Raises:
            ValueError: When ``name`` has no entry in ``SEMANTIC_PRIORS`` — a
                missing prior is a config error surfaced loudly, not a silent
                :class:`KeyError`.
        """
        try:
            return config.SEMANTIC_PRIORS[self.name]
        except KeyError as exc:
            raise ValueError(f"no semantic prior configured for detector '{self.name}'") from exc

    @abstractmethod
    def detect(self, values: list[str]) -> PiiDetection | None:
        """Return a :class:`PiiDetection` if the column may contain PII, else ``None``.

        Returns ``None`` when the match rate is below ``detect_threshold`` —
        the "no PII signal" answer, distinct from a returned
        :class:`PiiDetection` whose ``note`` is ``"possible_pii"`` (spec PII-01).
        """
        raise NotImplementedError

    def _match_rate(self, values: list[str]) -> float:
        """Fraction of non-missing values matching :attr:`pattern`.

        Missing values (whitespace-only or a sentinel) are excluded from both
        the numerator and the denominator — identical to the semantic detector
        so the two lenses judge the same data the same way. An all-missing (or
        empty) column yields ``0.0``.
        """
        non_missing = [v for v in values if not _is_missing(v)]
        if not non_missing:
            return 0.0
        matches = sum(1 for v in non_missing if self.pattern.search(v))
        return matches / len(non_missing)

    def _evaluate(self, values: list[str]) -> PiiDetection | None:
        """Shared detection algorithm for regex-based PII detectors.

        Computes the match rate over non-missing values, returns ``None`` when
        it is below ``DETECT_THRESHOLD``, and otherwise builds a
        :class:`PiiDetection` with ``confidence = round(match_rate x prior,
        CONFIDENCE_ROUND_DIGITS)`` and ``note = "possible_pii"``.
        """
        match_rate = self._match_rate(values)
        if match_rate < config.DETECT_THRESHOLD:
            return None
        confidence = round(match_rate * self.prior, config.CONFIDENCE_ROUND_DIGITS)
        return PiiDetection(label=self.name, confidence=confidence)


class EmailPiiDetector(PiiDetector):
    """Flags email columns as possible PII using the shared :data:`EMAIL_PATTERN`.

    The prior is read from ``[tool.sofer] semantic_priors.email`` at detect time
    via :attr:`PiiDetector.prior` — not a hardcoded class attribute.
    """

    name = "email"
    pattern = EMAIL_PATTERN

    def detect(self, values: list[str]) -> PiiDetection | None:
        return self._evaluate(values)


# Plugin registry: every concrete PII detector instance, in run order. Extending
# PII detection is a matter of appending a new detector here — the orchestrator
# below never changes.
_PII_DETECTORS: list[PiiDetector] = [EmailPiiDetector()]


def infer_pii_types(values: list[str]) -> list[PiiDetection]:
    """Run every registered PII detector over a column and collect the results.

    Detectors that return ``None`` (match rate below ``detect_threshold``) are
    dropped, so the returned list holds one :class:`PiiDetection` per possible
    PII signal — empty when no detector matches (mirrors
    :func:`sofer.semantic.infer_semantic_types`).
    """
    detections: list[PiiDetection] = []
    for detector in _PII_DETECTORS:
        detection = detector.detect(values)
        if detection is not None:
            detections.append(detection)
    return detections
