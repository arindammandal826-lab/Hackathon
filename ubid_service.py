"""
services/ubid_service.py
Equivalent to src/services/ubidService.ts

Provides:
  - generate_unified_business_identifier(seed) -> "KA-XXXXXXXX-C"
  - resolve_ubids(records, knowledge) -> list[UBIDRecord]
"""

from __future__ import annotations
from datetime import date
from typing import Optional

from models import SourceRecord, SystemKnowledge, UBIDRecord
from services.fuzzy_matching_service import compare_records

# ---------------------------------------------------------------------------
# Alphabet definitions
# ---------------------------------------------------------------------------

# 34 chars — excludes O and I (ambiguous glyphs)
ENTROPY_ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"
# Full 36-char set for Mod-36 checksum
MOD36_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# UBID generation helpers
# ---------------------------------------------------------------------------

def _generate_entropy_string(seed: str) -> str:
    """Deterministic 8-char entropy string from a seed (mirrors JS djb2)."""
    h = 0
    for ch in seed:
        h = ((h << 5) - h + ord(ch)) & 0xFFFFFFFF
        # Keep it signed 32-bit (mirrors JS `hash & hash`)
        if h >= 0x80000000:
            h -= 0x100000000

    val = abs(h)
    entropy = []
    for i in range(8):
        entropy.append(ENTROPY_ALPHABET[val % len(ENTROPY_ALPHABET)])
        val = val // len(ENTROPY_ALPHABET) + (i * 137)
        if val == 0:
            val = len(seed) + i + 100

    return "".join(reversed(entropy))


def _calculate_mod36_checksum(entropy: str) -> str:
    """Weighted Mod-36 checksum over "KA" + entropy."""
    full = f"KA{entropy}"
    total = 0
    for i, ch in enumerate(full):
        idx = MOD36_ALPHABET.find(ch)
        total += (idx if idx != -1 else 0) * (i + 1)
    return MOD36_ALPHABET[total % 36]


def generate_unified_business_identifier(seed: str) -> str:
    """Returns a UBID in the format KA-XXXXXXXX-C."""
    entropy = _generate_entropy_string(seed)
    checksum = _calculate_mod36_checksum(entropy)
    return f"KA-{entropy}-{checksum}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_base_ubid(
    record: SourceRecord,
    anchor_type: str,
    anchor_id: Optional[str] = None,
) -> UBIDRecord:
    seed = anchor_id or f"{record.businessName}-{record.pinCode}-{record.ownerName}"
    ubid = generate_unified_business_identifier(seed)
    return UBIDRecord(
        ubid=ubid,
        anchorType=anchor_type,          # type: ignore[arg-type]
        anchorId=anchor_id,
        canonicalName=record.businessName,
        canonicalAddress=record.address,
        pinCode=record.pinCode,
        pan=record.pan,
        gstin=record.gstin,
        status="Active",
        confidence=0.99 if anchor_type == "Central" else 0.75,
        riskScore=10 if anchor_type == "Central" else 40,
        evidence=[],
        lastUpdated=date.today().isoformat(),
        linkedRecords=[],
    )


def _is_blacklisted(
    id_a: str,
    id_b: str,
    knowledge: Optional[SystemKnowledge],
) -> bool:
    if knowledge is None:
        return False
    for entry in knowledge.manualBlacklist:
        ra, rb = entry.get("recordIdA", ""), entry.get("recordIdB", "")
        if (ra == id_a and rb == id_b) or (ra == id_b and rb == id_a):
            return True
    return False


# ---------------------------------------------------------------------------
# Main resolution function
# ---------------------------------------------------------------------------

def resolve_ubids(
    records: list[SourceRecord],
    knowledge: Optional[SystemKnowledge] = None,
) -> list[UBIDRecord]:
    """
    Two-pass entity resolution:
      Pass 1 — Anchor on GSTIN / PAN (deterministic, high confidence).
      Pass 2 — Fuzzy grouping by name + address within same PIN code.

    Returns a deduplicated list of UBIDRecord objects.
    """
    # Central registry keyed by "KA-REG-G-<gstin>" or "KA-REG-P-<pan>"
    registry: dict[str, UBIDRecord] = {}
    internal_registry: list[UBIDRecord] = []
    linked_ids: set[str] = set()

    # ------------------------------------------------------------------
    # Pass 1 — GSTIN / PAN anchoring
    # ------------------------------------------------------------------
    for record in records:
        gstin = record.gstin if record.gstin and record.gstin != "Pending" else None
        pan = record.pan or None

        if gstin or pan:
            gstin_key = f"KA-REG-G-{gstin}" if gstin else None
            pan_key = f"KA-REG-P-{pan}" if pan else None
            target_key = gstin_key or pan_key

            existing = registry.get(target_key)  # type: ignore[arg-type]

            # Check blacklist against already-linked records
            if existing:
                has_conflict = any(
                    _is_blacklisted(r.id, record.id, knowledge)
                    for r in existing.linkedRecords
                )
                if has_conflict:
                    continue

            if not existing:
                existing = _create_base_ubid(record, "Central", gstin or pan)  # type: ignore[arg-type]
                registry[target_key] = existing  # type: ignore[index]

            existing.linkedRecords.append(record)
            linked_ids.add(record.id)

            match_type = "GSTIN Match" if gstin else "PAN Match"
            evidence_entry = f"{match_type} ({record.department})"
            if evidence_entry not in existing.evidence:
                existing.evidence.append(evidence_entry)

    # ------------------------------------------------------------------
    # Pass 2 — Fuzzy grouping for unanchored records
    # ------------------------------------------------------------------
    FUZZY_THRESHOLD = 0.8

    for record in records:
        if record.id in linked_ids:
            continue

        best_match: Optional[UBIDRecord] = None
        highest_confidence = FUZZY_THRESHOLD

        # Optimisation: only compare within the same PIN code
        candidates = [u for u in internal_registry if u.pinCode == record.pinCode]

        for ubid_entry in candidates:
            if not ubid_entry.linkedRecords:
                continue
            result = compare_records(ubid_entry.linkedRecords[0], record, knowledge)
            if result["confidence"] > highest_confidence:
                highest_confidence = result["confidence"]
                best_match = ubid_entry

        if best_match:
            best_match.linkedRecords.append(record)
            best_match.evidence.append(
                f"Fuzzy Linkage ({record.department}, {int(highest_confidence * 100)}% Conf)"
            )
        else:
            new_ubid = _create_base_ubid(record, "Internal")
            new_ubid.linkedRecords.append(record)
            new_ubid.evidence.append(f"Address/Name Anchor ({record.department})")
            internal_registry.append(new_ubid)

        linked_ids.add(record.id)

    return list(registry.values()) + internal_registry
