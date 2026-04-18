"""
services/ai_service.py
Equivalent to src/services/geminiService.ts

Replaces the Google Gemini SDK with the Anthropic Python SDK.
All four public functions are preserved with identical contracts.

Required:
    pip install anthropic python-dotenv
    ANTHROPIC_API_KEY must be set in the environment (or a .env file).
"""

from __future__ import annotations
import json
import os
import re
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_MODEL = "claude-opus-4-5"

# ---------------------------------------------------------------------------
# Shared system knowledge injected into every chat call
# ---------------------------------------------------------------------------

_SYSTEM_LOGIC_KNOWLEDGE = """
SYSTEM ARCHITECTURE & LOGIC:
1. UBID Format (KA-XXXXXXXX-C):
   - KA (Namespace): Globally unique Karnataka identifiers.
   - XXXXXXXX (Entropy): 8-char Base36 string (excluding O/I) providing 1.7 trillion possible IDs.
   - C (Reliability): A Mod-36 checksum character for manual input verification.
2. Fuzzy Matching Engine:
   - Uses Levenshtein Distance for strict string similarity.
   - Uses Soundex Phonetic Algorithm to catch spelling variations (e.g., 'Lakshmi' vs 'Laxmi').
   - Normalization removes special characters and expands common industrial abbreviations (Pvt, Ltd, Ind, Rd).
   - Weighted Scoring: Name (50%), Address (30%), PIN Code (20%).
3. Operational Status Inference:
   - Analysis window is 18 months.
   - 'Active': Diverse signals (Inspections, Payments) in the last 6 months.
   - 'Dormant': No activity in 6 months, but historic signals in 6-18 months.
   - 'Closed': Explicit disconnection/closure signal OR zero signals for 18 months.
4. Orphan Signal Resolution:
   - Logic identifies activity records without a parent UBID.
   - Reviewers can 'Merge' to an existing UBID if confidence is high, or 'Project' a new entity.
5. Entity Linkage: One UBID can link multiple source records across departments
   (Factories, Labour, KSPCB) to create a Triple-A single source of truth.
6. Privacy: PII is anonymized using regex before AI analysis.
"""

_CHAT_SYSTEM = (
    "You are the UBID Intelligence Assistant. Provide ultra-fast, direct, and structured "
    "technical data.\n"
    + _SYSTEM_LOGIC_KNOWLEDGE
    + "\nSTRICT RULES:\n"
    "1. NO introductory or closing pleasantries.\n"
    "2. Use numbered lists ONLY.\n"
    "3. One fact per line.\n"
    "4. Max 5 lines per response.\n"
    "5. No bolding or markdown headers beyond lists."
)


# ---------------------------------------------------------------------------
# PII anonymization
# ---------------------------------------------------------------------------

def _anonymize_data(data: Any) -> Any:
    """Strip PAN, GSTIN, and proper names from arbitrary data before LLM calls."""
    text = json.dumps(data)
    # PAN: ABCDE1234F
    text = re.sub(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", "PLACEHOLDER_PAN", text)
    # GSTIN: 29AAAAA0000A1Z5
    text = re.sub(
        r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}",
        "PLACEHOLDER_GSTIN",
        text,
    )
    # Capitalised names → synthetic placeholder (simple heuristic)
    text = re.sub(r"[A-Z][a-z]+(?=\s[A-Z][a-z]+)", "SyntheticEntity", text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public API — mirrors geminiService.ts exports
# ---------------------------------------------------------------------------


def get_general_chat_response(
    message: str,
    history: list[dict],
) -> str:
    """
    Multi-turn chat response.

    history format: [{"role": "user"|"assistant", "content": "..."}]
    """
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in history
    ]
    messages.append({"role": "user", "content": message})

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_CHAT_SYSTEM,
        messages=messages,
    )
    text = response.content[0].text
    if not text:
        raise RuntimeError("AI Assistant returned null signal.")
    return text


def get_high_thinking_analysis(input_data: Any) -> str:
    """
    Deep strategic audit on anonymized entity data.
    Equivalent to getHighThinkingAnalysis().
    """
    anonymized = _anonymize_data(input_data)
    prompt = (
        "Perform a Deep Strategic Audit on the following industrial entity data.\n\n"
        "CONTEXT: We are correlating static registry records with a live stream of "
        "cross-departmental activity signals.\n\n"
        "TASK:\n"
        "1. Analyze the 'entity' registry details for inconsistencies (PAN/GSTIN/Status).\n"
        "2. Cross-reference with the 'recentActivity' timeline. Identify if the timeline "
        "supports or contradicts the current registry status.\n"
        "3. Identify 'Hidden Linkage' risks (e.g., similar addresses or overlapping signals).\n"
        "4. Predict future operational health based on signal frequency.\n\n"
        "IMPORTANT: Focus on temporal sequences and cross-silo patterns.\n\n"
        f"Anonymized Data Stream:\n{json.dumps(anonymized, indent=2)}"
    )

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=(
            "You are a senior business intelligence analyst specializing in regulatory "
            "compliance and entity resolution. Provide deep, high-thinking analysis."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def get_maps_grounding_info(location: str) -> str:
    """
    Returns a structured industrial intelligence report for a Karnataka area.
    Equivalent to getMapsGroundingInfo().
    """
    prompt = (
        f"Provide a comprehensive industrial intelligence report for the {location} area "
        "in Karnataka.\n"
        "Focus on:\n"
        "1. Key industries and sectors present.\n"
        "2. Major industrial landmarks or clusters.\n"
        "3. Recent developments or infrastructure projects.\n"
        "4. Potential regulatory or environmental focus areas for this specific zone.\n\n"
        "Format the report with clear headings and structured sections. "
        "Use numbered lists for details."
    )

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=(
            "You are a specialized industrial intelligence analyst. Your reports are highly "
            "structured, data-driven, and professional. Use clear headings and numbered lists. "
            "DO NOT use asterisks (*) for formatting. Ensure each point starts on a new line."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def get_healer_patch(error_stack: str, component_context: str) -> str:
    """
    Provides an automated error-resolution instruction.
    Equivalent to getHealerPatch().
    """
    prompt = (
        "The UBID system has encountered a runtime error.\n"
        f"ERROR STACK: {error_stack}\n"
        f"COMPONENT CONTEXT: {component_context}\n\n"
        "Provide a 'Healer Instruction' to help the operator understand why this happened "
        "and how to avoid it.\n"
        "Suggest a defensive programming snippet to prevent this specific crash in the future.\n"
        "Format: Clear explanation + Code Snippet. No asterisks."
    )

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=(
            "You are an Automated Error Resolution AI designed for the UBID system. "
            "You stabilize and fix bugs."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def analyze_data_anomaly(data: Any) -> str:
    """
    Schema evolution analysis for non-standard incoming records.
    Equivalent to analyzeDataAnomaly().
    """
    prompt = (
        "The system has received a data record that doesn't fully match the standard UBID schema.\n"
        f"RAW DATA:\n{json.dumps(data, indent=2)}\n\n"
        "Analyze the fields:\n"
        "1. Identify compatible fields with the Registry (which field is Name? which is Address?).\n"
        "2. Map unknown fields to potential system benefits "
        "(e.g., a 'power_consumption' field might predict operational status).\n"
        "3. Propose a 'Compatibility Layer' to ingest this data.\n\n"
        "Format: Schema Mapping Table + Recommendation. No asterisks."
    )

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=(
            "You are a Data Resilience AI. You make the system compatible with any "
            "environment-specific data formats."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
