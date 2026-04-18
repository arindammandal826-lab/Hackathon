"""
services/fuzzy_matching_service.py
Equivalent to src/services/fuzzyMatchingService.ts

Provides:
  - String normalization with abbreviation expansion
  - Levenshtein distance (memory-optimized 2-row variant)
  - String similarity ratio
  - Soundex phonetic encoding
  - Record comparison with weighted confidence scoring
"""

from __future__ import annotations
from functools import lru_cache
from typing import Optional

# ---------------------------------------------------------------------------
# Abbreviation table (bidirectional helpers included)
# ---------------------------------------------------------------------------

ABBREVIATIONS: dict[str, str] = {
    "pvt": "private",
    "ltd": "limited",
    "rd": "road",
    "st": "street",
    "bldg": "building",
    "ind": "industrial",
    "ent": "enterprises",
    "inc": "incorporated",
    "co": "company",
    "corp": "corporation",
    "mkt": "market",
    "dept": "department",
    "assn": "association",
    "svc": "services",
    "tech": "technologies",
    "solutions": "soln",
    "industrial": "ind",
}

# ---------------------------------------------------------------------------
# Normalization  (cached via lru_cache — equivalent to the Map<string,string>)
# ---------------------------------------------------------------------------

import re

@lru_cache(maxsize=5000)
def normalize_string(s: str) -> str:
    """Lowercase, strip non-alphanumeric, expand abbreviations."""
    if not s:
        return ""
    normalized = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    words = normalized.split()
    expanded = [ABBREVIATIONS.get(w, w) for w in words]
    return " ".join(expanded)


# ---------------------------------------------------------------------------
# Levenshtein Distance — iterative 2-row variant (O(min(m,n)) space)
# ---------------------------------------------------------------------------

def levenshtein_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)

    prev_row = list(range(len(b) + 1))
    curr_row = [0] * (len(b) + 1)

    for i, ca in enumerate(a, 1):
        curr_row[0] = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr_row[j] = min(
                curr_row[j - 1] + 1,   # insertion
                prev_row[j] + 1,        # deletion
                prev_row[j - 1] + cost, # substitution
            )
        prev_row = curr_row[:]
    return prev_row[len(b)]


def string_similarity(a: str, b: str) -> float:
    """Returns a similarity ratio in [0, 1]."""
    if a == b:
        return 1.0
    longer = a if len(a) >= len(b) else b
    shorter = b if len(a) >= len(b) else a
    if not longer:
        return 1.0
    distance = levenshtein_distance(a, b)
    return (len(longer) - distance) / len(longer)


# ---------------------------------------------------------------------------
# Soundex Phonetic Algorithm
# ---------------------------------------------------------------------------

_SOUNDEX_CODES: dict[str, str] = {
    **dict.fromkeys("BFPV", "1"),
    **dict.fromkeys("CGJKQSXZ", "2"),
    **dict.fromkeys("DT", "3"),
    "L": "4",
    **dict.fromkeys("MN", "5"),
    "R": "6",
}

def soundex(s: str) -> str:
    if not s:
        return ""
    cleaned = re.sub(r"[^A-Za-z]", "", s).upper()
    if not cleaned:
        return ""

    first_letter = cleaned[0]
    result = first_letter
    last_code = _SOUNDEX_CODES.get(first_letter, "0")

    for ch in cleaned[1:]:
        if len(result) >= 4:
            break
        code = _SOUNDEX_CODES.get(ch, "0")
        if code != "0" and code != last_code:
            result += code
        last_code = code

    return result.ljust(4, "0")


# ---------------------------------------------------------------------------
# Record comparison  (main export)
# ---------------------------------------------------------------------------

def compare_records(
    record_a,
    record_b,
    knowledge=None,
) -> dict:
    """
    Compares two SourceRecord objects and returns:
      { confidence, reasons, risk_factors }
    """
    reasons: list[str] = []
    risk_factors: list[str] = []

    # Default weights
    weights = (
        knowledge.learnedWeights
        if knowledge and knowledge.learnedWeights
        else {"nameWeight": 0.5, "addressWeight": 0.3, "pinWeight": 0.2}
    )

    # 1. Exact identifier anchors — short-circuit with high confidence
    if (
        record_a.gstin
        and record_a.gstin == record_b.gstin
        and record_a.gstin != "Pending"
    ):
        return {"confidence": 0.99, "reasons": ["GSTIN Exact Match"], "risk_factors": []}

    if record_a.pan and record_a.pan == record_b.pan:
        return {"confidence": 0.98, "reasons": ["PAN Exact Match"], "risk_factors": []}

    # 2. Name similarity
    norm_name_a = normalize_string(record_a.businessName)
    norm_name_b = normalize_string(record_b.businessName)
    name_score = string_similarity(norm_name_a, norm_name_b)

    if name_score > 0.85:
        reasons.append(f"High Name Similarity ({int(name_score * 100)}%)")
    elif name_score > 0.6:
        reasons.append(f"Moderate Name Similarity ({int(name_score * 100)}%)")

    # Phonetic check
    sx_a = soundex(record_a.businessName)
    sx_b = soundex(record_b.businessName)
    phonetic_match = sx_a == sx_b
    if phonetic_match and name_score < 0.9:
        reasons.append("Phonetic Name Match (Soundex)")

    # 3. Address similarity
    norm_addr_a = normalize_string(record_a.address)
    norm_addr_b = normalize_string(record_b.address)
    addr_score = string_similarity(norm_addr_a, norm_addr_b)

    if addr_score > 0.8:
        reasons.append(f"Strong Address Correlation ({int(addr_score * 100)}%)")

    # 4. PIN code
    pin_match = record_a.pinCode == record_b.pinCode
    if pin_match:
        reasons.append("Location/PIN Code Alignment")
    else:
        risk_factors.append("PIN Code Mismatch")

    # Weighted confidence
    confidence = (
        name_score * weights["nameWeight"]
        + addr_score * weights["addressWeight"]
        + (weights["pinWeight"] if pin_match else 0)
    )

    # Phonetic bonus
    if phonetic_match and name_score < 0.7:
        confidence += 0.1

    # Missing-GSTIN penalty
    if not record_a.gstin or not record_b.gstin:
        risk_factors.append("Indirect Anchor (Missing GSTIN)")

    confidence = max(0.1, min(0.98, confidence))

    return {
        "confidence": confidence,
        "reasons": reasons[:4],
        "risk_factors": risk_factors[:3],
    }
