"""
services/status_inference_service.py
Equivalent to src/services/statusInferenceService.ts

Provides:
  - infer_business_status(ubid, events, window_months) -> StatusVerdict
  - find_orphan_events(events, ubids) -> list[ActivityEvent]
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta  # pip install python-dateutil

from models import ActivityEvent, UBIDRecord

# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class VerdictEvidence:
    signal_type: str
    source: str
    date: str
    impact: str  # "Positive" | "Negative" | "Neutral"
    description: str

    def to_dict(self) -> dict:
        return {
            "signalType": self.signal_type,
            "source": self.source,
            "date": self.date,
            "impact": self.impact,
            "description": self.description,
        }


@dataclass
class StatusVerdict:
    status: str  # "Active" | "Dormant" | "Closed"
    confidence: float
    reasoning: str
    evidence_trail: list[VerdictEvidence] = field(default_factory=list)
    analysis_window_months: int = 18

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidenceTrail": [e.to_dict() for e in self.evidence_trail],
            "analysisWindowMonths": self.analysis_window_months,
        }


# ---------------------------------------------------------------------------
# Signal impact mapping
# ---------------------------------------------------------------------------

_NEGATIVE_EVENTS = {"Closure", "Disconnection", "Compliance Filing (Overdue)"}
_POSITIVE_EVENTS = {
    "Renewal", "Inspection", "Bill Payment",
    "Safety Audit", "License Renewal",
}


def _get_signal_impact(event_type: str) -> str:
    if event_type in _NEGATIVE_EVENTS:
        return "Negative"
    if event_type in _POSITIVE_EVENTS:
        return "Positive"
    return "Neutral"


# ---------------------------------------------------------------------------
# Core inference logic
# ---------------------------------------------------------------------------

def infer_business_status(
    ubid: str,
    events: list[ActivityEvent],
    window_months: int = 18,
) -> StatusVerdict:
    """
    Infers business operational status from activity signal stream.

    Rules:
      ACTIVE  — signals (especially High/Critical) in the last 6 months.
      DORMANT — no signals in last 6 months, but signals in 6–18 months.
      CLOSED  — explicit Closure/Disconnection OR zero signals in 18 months.
    """
    now = datetime.now(timezone.utc)
    active_threshold = now - relativedelta(months=6)
    dormant_threshold = now - relativedelta(months=18)

    ubid_events = sorted(
        [e for e in events if e.ubid == ubid],
        key=lambda e: e.date,
        reverse=True,
    )

    def parse_date(d: str) -> datetime:
        dt = datetime.fromisoformat(d)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    active_signals = [e for e in ubid_events if parse_date(e.date) > active_threshold]
    recent_signals = [e for e in ubid_events if parse_date(e.date) > dormant_threshold]

    evidence_trail = [
        VerdictEvidence(
            signal_type=e.eventType,
            source=e.department,
            date=e.date,
            impact=_get_signal_impact(e.eventType),
            description=e.details,
        )
        for e in ubid_events
    ]

    # Highest-priority check: explicit closure / disconnection
    closure_signal = next(
        (e for e in ubid_events if e.eventType in ("Closure", "Disconnection")),
        None,
    )
    if closure_signal:
        return StatusVerdict(
            status="Closed",
            confidence=0.95,
            reasoning=(
                f"Explicit termination signal detected from "
                f"{closure_signal.department} on {closure_signal.date}."
            ),
            evidence_trail=evidence_trail,
            analysis_window_months=window_months,
        )

    # Active: at least one signal in the last 6 months
    if active_signals:
        diverse_sources = len({e.department for e in active_signals})
        confidence = min(0.7 + diverse_sources * 0.1, 0.99)
        return StatusVerdict(
            status="Active",
            confidence=confidence,
            reasoning=(
                f"Active operations confirmed via {len(active_signals)} signals "
                f"across {diverse_sources} departments in the last 6 months."
            ),
            evidence_trail=evidence_trail,
            analysis_window_months=window_months,
        )

    # Dormant: signals exist only in 6–18 month window
    if recent_signals:
        last_event = recent_signals[0]
        return StatusVerdict(
            status="Dormant",
            confidence=0.85,
            reasoning=(
                f"No signals detected in the last 6 months. "
                f"Last known activity was {last_event.eventType} on {last_event.date}."
            ),
            evidence_trail=evidence_trail,
            analysis_window_months=window_months,
        )

    # Closed by silence
    return StatusVerdict(
        status="Closed",
        confidence=0.90,
        reasoning=(
            f"Zero operational signals detected across all monitoring departments "
            f"for {window_months} months. Inferring business cessation."
        ),
        evidence_trail=evidence_trail,
        analysis_window_months=window_months,
    )


def find_orphan_events(
    events: list[ActivityEvent],
    ubids: list[UBIDRecord],
) -> list[ActivityEvent]:
    """Returns events whose UBID does not exist in the registry."""
    ubid_set = {u.ubid for u in ubids}
    return [e for e in events if e.ubid not in ubid_set]
