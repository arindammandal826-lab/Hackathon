"""
main.py
Karnataka UBID Intelligence Platform — Python CLI

Equivalent to the React/TypeScript App.tsx but as an interactive
command-line application.  Run:

    python main.py

Sub-commands available in the interactive menu:
  1. Dashboard          — summary stats
  2. UBID Explorer      — search & detail view for a UBID
  3. Central Registry   — list all known UBIDs
  4. Reviewer Queue     — fuzzy match suggestions awaiting approval
  5. Orphan Signals     — events with no parent UBID
  6. Audit Ledger       — chronological governance log
  7. AI Chat            — natural-language query to the AI assistant
  8. AI Deep Analysis   — high-thinking audit on a UBID
  9. Resolve UBIDs      — run entity resolution on mock source records
  0. Exit
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from models import (
    SourceRecord,
    UBIDRecord,
    ActivityEvent,
    SystemKnowledge,
    AuditEntry,
    MatchSuggestion,
)
from mock_data import MOCK_UBIDS, MOCK_EVENTS, generate_mock_data
from services.ubid_service import resolve_ubids, generate_unified_business_identifier
from services.status_inference_service import infer_business_status, find_orphan_events
from services.fuzzy_matching_service import compare_records, normalize_string

# ---------------------------------------------------------------------------
# Global application state  (mirrors React useState hooks)
# ---------------------------------------------------------------------------

_ubids: list[UBIDRecord] = list(MOCK_UBIDS)
_events: list[ActivityEvent] = list(MOCK_EVENTS)
_knowledge: SystemKnowledge = SystemKnowledge()
_audit_log: list[AuditEntry] = []
_chat_history: list[dict] = []


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------

def _log_audit(
    action: str,
    entity_id: str,
    details: str,
    audit_type: str = "Governance",
) -> None:
    entry = AuditEntry(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        action=action,
        actor="Senior Reviewer (CLI)",
        entityId=entity_id,
        details=details,
        type=audit_type,  # type: ignore[arg-type]
    )
    _audit_log.append(entry)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

_DIVIDER = "─" * 68


def _print_header(title: str) -> None:
    print(f"\n{'═' * 68}")
    print(f"  {title.upper()}")
    print(f"{'═' * 68}")


def _status_badge(status: str) -> str:
    badges = {"Active": "[ACTIVE]", "Dormant": "[DORMANT]", "Closed": "[CLOSED]"}
    return badges.get(status, f"[{status.upper()}]")


def _print_ubid_summary(u: UBIDRecord) -> None:
    risk_bar = "█" * (u.riskScore // 10) + "░" * (10 - u.riskScore // 10)
    print(f"  UBID     : {u.ubid}")
    print(f"  Name     : {u.canonicalName}")
    print(f"  Status   : {_status_badge(u.status)}  Confidence: {u.confidence:.0%}")
    print(f"  Risk     : [{risk_bar}] {u.riskScore}/100")
    print(f"  Anchor   : {u.anchorType}  ({u.anchorId or 'N/A'})")
    print(f"  PIN Code : {u.pinCode}")
    print(f"  Records  : {len(u.linkedRecords)} linked")
    print(f"  Updated  : {u.lastUpdated}")


# ---------------------------------------------------------------------------
# Menu sections
# ---------------------------------------------------------------------------

def menu_dashboard() -> None:
    _print_header("Dashboard")

    total = len(_ubids)
    active = sum(1 for u in _ubids if u.status == "Active")
    dormant = sum(1 for u in _ubids if u.status == "Dormant")
    closed = sum(1 for u in _ubids if u.status == "Closed")
    orphans = len(find_orphan_events(_events, _ubids))
    health = (active / total * 100) if total else 0.0

    print(f"\n  Total UBIDs       : {total}")
    print(f"  Active Businesses : {active}")
    print(f"  Dormant           : {dormant}")
    print(f"  Closed            : {closed}")
    print(f"  Compliance Health : {health:.1f}%")
    print(f"  Orphan Signals    : {orphans}")

    print(f"\n  {'─' * 40}")
    print(f"  {'PIN Code':<12} {'Count':>5}  {'Active':>6}")
    print(f"  {'─' * 40}")
    pin_stats: dict[str, dict] = {}
    for u in _ubids:
        p = pin_stats.setdefault(u.pinCode, {"count": 0, "active": 0})
        p["count"] += 1
        if u.status == "Active":
            p["active"] += 1
    for pin, s in sorted(pin_stats.items(), key=lambda x: -x[1]["count"]):
        bar = "█" * s["count"]
        print(f"  {pin:<12} {s['count']:>5}  {s['active']:>6}  {bar}")

    print(f"\n  Recent events (last 5):")
    recent = sorted(_events, key=lambda e: e.date, reverse=True)[:5]
    for e in recent:
        print(f"    [{e.date}] {e.eventType:<20}  {e.department:<25}  {e.value}")


def menu_explorer() -> None:
    _print_header("UBID Explorer")
    query = input("  Search (UBID / name / PAN / GSTIN): ").strip().lower()

    results = [
        u for u in _ubids
        if query in u.ubid.lower()
        or query in u.canonicalName.lower()
        or query in (u.pan or "").lower()
        or query in (u.gstin or "").lower()
    ]

    if not results:
        print("  No results found.")
        return

    for i, u in enumerate(results):
        print(f"\n  [{i + 1}] {u.ubid} — {u.canonicalName} {_status_badge(u.status)}")

    try:
        choice = int(input("  Select (number): ")) - 1
        selected = results[choice]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    _print_header(f"Detail — {selected.canonicalName}")
    _print_ubid_summary(selected)

    # Status inference
    verdict = infer_business_status(selected.ubid, _events)
    print(f"\n  === AI Status Inference ===")
    print(f"  Inferred Status : {verdict.status} ({verdict.confidence:.0%})")
    print(f"  Reasoning       : {verdict.reasoning}")
    if verdict.evidence_trail:
        print(f"\n  Evidence trail:")
        for ev in verdict.evidence_trail[:5]:
            print(f"    [{ev.date}] {ev.signal_type:<22} {ev.impact:<8} {ev.source}")

    # Linked records
    print(f"\n  === Linked Source Records ===")
    for r in selected.linkedRecords:
        print(f"    {r.id:<8}  {r.department:<30}  {r.businessName}")


def menu_registry() -> None:
    _print_header("Central Registry")
    for u in _ubids:
        badge = _status_badge(u.status)
        anchor = f"[{u.anchorType}]"
        print(f"  {u.ubid}  {badge:<10} {anchor:<10}  {u.canonicalName}")
    print(f"\n  Total: {len(_ubids)} UBIDs")


def menu_reviewer_queue() -> None:
    _print_header("Reviewer Queue — Fuzzy Match Suggestions")
    data = generate_mock_data()
    src_records = data["sourceRecords"]

    suggestions: list[MatchSuggestion] = []
    for i, a in enumerate(src_records):
        for b in src_records[i + 1:]:
            if a.pinCode != b.pinCode:
                continue
            result = compare_records(a, b, _knowledge)
            if 0.6 <= result["confidence"] < 0.99:
                suggestions.append(
                    MatchSuggestion(
                        id=f"MATCH-{a.id}-{b.id}",
                        recordA=a,
                        recordB=b,
                        confidence=result["confidence"],
                        reasons=result["reasons"],
                        status="Pending",
                        riskFactors=result["risk_factors"],
                        priority=(
                            "High" if result["confidence"] > 0.85
                            else "Medium" if result["confidence"] > 0.7
                            else "Low"
                        ),
                    )
                )

    suggestions.sort(key=lambda s: -s.confidence)
    if not suggestions:
        print("  No pending suggestions.")
        return

    for i, s in enumerate(suggestions[:10]):
        print(
            f"  [{i + 1}] {s.confidence:.0%}  {s.recordA.businessName!r:<35} "
            f"↔  {s.recordB.businessName!r}"
        )
        print(f"       Reasons: {', '.join(s.reasons[:2])}")
        print(f"       Risk   : {', '.join(s.riskFactors or []) or 'None'}")
        print()


def menu_orphan_signals() -> None:
    _print_header("Orphan Signals")
    orphans = find_orphan_events(_events, _ubids)
    if not orphans:
        print("  No orphan signals detected.")
        return

    for i, e in enumerate(orphans):
        print(f"  [{i + 1}] {e.id:<6}  {e.eventType:<25}  {e.department:<25}  {e.date}")
        if e.businessNameHint:
            print(f"         Hint → {e.businessNameHint!r}  {e.pinCodeHint or ''}")

    try:
        choice = int(input("\n  Select orphan to resolve (0 to skip): ")) - 1
        if choice < 0:
            return
        orphan = orphans[choice]
    except (ValueError, IndexError):
        return

    action = input("  Action: [c]reate new UBID | [l]ink to existing | [skip]: ").strip().lower()

    if action == "c":
        new_ubid_id = f"KA-ORPHAN-{orphan.id[:5].upper()}"
        initial_record = SourceRecord(
            id=f"SR-{orphan.id}",
            department=orphan.department,
            businessName=orphan.businessNameHint or f"Unknown Entity ({orphan.id})",
            address=orphan.addressHint or "Address TBD",
            pinCode=orphan.pinCodeHint or "000000",
            ownerName="Derived from Signal",
        )
        new_record = UBIDRecord(
            ubid=new_ubid_id,
            anchorType="Internal",
            canonicalName=initial_record.businessName,
            canonicalAddress=initial_record.address,
            pinCode=initial_record.pinCode,
            status="Active",
            confidence=0.75,
            riskScore=30,
            evidence=[f"Resolved from Orphan Event: {orphan.eventType}"],
            lastUpdated=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            linkedRecords=[initial_record],
        )
        _ubids.append(new_record)
        # Assign event to new UBID
        for e in _events:
            if e.id == orphan.id:
                e.ubid = new_ubid_id
                break
        _log_audit("Orphan Resolution", new_ubid_id, f"Projected new entity from {orphan.eventType}")
        print(f"  Created: {new_ubid_id}")

    elif action == "l":
        print("  Existing UBIDs:")
        for i, u in enumerate(_ubids):
            print(f"    [{i + 1}] {u.ubid}  {u.canonicalName}")
        try:
            idx = int(input("  Link to UBID number: ")) - 1
            target = _ubids[idx]
            target.evidence.append(f"Linked Orphan Event: {orphan.eventType}")
            for e in _events:
                if e.id == orphan.id:
                    e.ubid = target.ubid
                    break
            _log_audit("Orphan Linkage", target.ubid, f"Linked signal {orphan.eventType}")
            print(f"  Linked to {target.ubid}")
        except (ValueError, IndexError):
            print("  Invalid.")


def menu_audit_ledger() -> None:
    _print_header("Audit Ledger")
    if not _audit_log:
        print("  No audit entries yet.")
        return
    for e in reversed(_audit_log[-20:]):
        print(f"  [{e.timestamp[:19]}]  {e.type:<12}  {e.action:<20}  {e.entityId}")
        print(f"    {e.details}")


def menu_ai_chat() -> None:
    _print_header("AI Intelligence Chat")
    print("  (type 'back' to return to main menu)\n")

    try:
        from services.ai_service import get_general_chat_response
    except ImportError:
        print("  anthropic package not installed. Run: pip install anthropic python-dateutil")
        return

    while True:
        user_input = input("  You: ").strip()
        if user_input.lower() in ("back", "exit", "quit"):
            break
        if not user_input:
            continue

        try:
            response = get_general_chat_response(user_input, _chat_history)
            _chat_history.append({"role": "user", "content": user_input})
            _chat_history.append({"role": "assistant", "content": response})
            print(f"\n  AI: {response}\n")
        except Exception as exc:
            print(f"  [Error] {exc}")


def menu_deep_analysis() -> None:
    _print_header("AI Deep Analysis (High-Thinking Mode)")

    try:
        from services.ai_service import get_high_thinking_analysis
    except ImportError:
        print("  anthropic package not installed.")
        return

    print("  Select a UBID to analyse:")
    for i, u in enumerate(_ubids):
        print(f"    [{i + 1}] {u.ubid}  {u.canonicalName}")

    try:
        idx = int(input("  Choice: ")) - 1
        selected = _ubids[idx]
    except (ValueError, IndexError):
        print("  Invalid.")
        return

    ubid_events = [e for e in _events if e.ubid == selected.ubid]
    payload = {
        "entity": selected.to_dict(),
        "recentActivity": [e.to_dict() for e in ubid_events],
    }

    print("  Sending to AI… (this may take a moment)")
    try:
        result = get_high_thinking_analysis(payload)
        print(f"\n{result}")
    except Exception as exc:
        print(f"  [Error] {exc}")


def menu_resolve() -> None:
    _print_header("Entity Resolution — Run on Mock Source Records")
    data = generate_mock_data()
    src = data["sourceRecords"]
    print(f"  Running resolution on {len(src)} source records…")
    resolved = resolve_ubids(src, _knowledge)
    print(f"  Generated {len(resolved)} UBIDs:\n")
    for u in resolved:
        print(f"  {u.ubid}  [{u.anchorType:<8}]  {u.canonicalName:<35}  ({len(u.linkedRecords)} records)")
    add = input(f"\n  Add these {len(resolved)} new UBIDs to registry? [y/N]: ").strip().lower()
    if add == "y":
        _ubids.extend(resolved)
        _log_audit("Bulk Resolution", "REGISTRY", f"Added {len(resolved)} UBIDs from entity resolution run.", "System")
        print(f"  Registry now contains {len(_ubids)} UBIDs.")


# ---------------------------------------------------------------------------
# Main interactive loop
# ---------------------------------------------------------------------------

_MENU = """
  ┌─────────────────────────────────────────────────┐
  │     KARNATAKA UBID INTELLIGENCE PLATFORM        │
  ├─────────────────────────────────────────────────┤
  │  1. Dashboard              6. Audit Ledger       │
  │  2. UBID Explorer          7. AI Chat            │
  │  3. Central Registry       8. AI Deep Analysis   │
  │  4. Reviewer Queue         9. Resolve UBIDs      │
  │  5. Orphan Signals         0. Exit               │
  └─────────────────────────────────────────────────┘
"""

_HANDLERS = {
    "1": menu_dashboard,
    "2": menu_explorer,
    "3": menu_registry,
    "4": menu_reviewer_queue,
    "5": menu_orphan_signals,
    "6": menu_audit_ledger,
    "7": menu_ai_chat,
    "8": menu_deep_analysis,
    "9": menu_resolve,
}


def main() -> None:
    print("\n  UBID Intelligence Platform — Python Edition")
    print(f"  Registry loaded: {len(_ubids)} UBIDs, {len(_events)} events")

    while True:
        print(_MENU)
        choice = input("  Select option: ").strip()
        if choice == "0":
            print("  Goodbye.\n")
            break
        handler = _HANDLERS.get(choice)
        if handler:
            handler()
        else:
            print("  Unknown option.")


if __name__ == "__main__":
    main()
