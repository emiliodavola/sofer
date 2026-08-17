"""Shared regex patterns for sofer detectors.

Centralises the compiled patterns that more than one detector needs, so a
single definition serves every consumer. Keeping them here — rather than in
``semantic.py`` or ``pii.py`` — avoids duplicating the regex (AGENTS.md rule 4)
and sidesteps the semantic↔pii circular import that importing one detector
from the other would create.
"""

from __future__ import annotations

import re

# Matches an email-shaped string: a local part (allowing ``.``, ``+``, ``%``,
# ``-`` and ``_``), a single ``@``, and a dotted domain with a letter TLD.
# Used by both the semantic email detector and the email PII detector.
EMAIL_PATTERN: re.Pattern[str] = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
