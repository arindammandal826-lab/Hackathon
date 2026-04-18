"""
types.py
Equivalent to src/types.ts — all shared dataclasses and type aliases.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

Department = Literal[
    "Shop & Establishment",
    "Factories",
    "Labour",
    "KSPCB",
    "BESCOM",
    "Factories & Boilers",
    "Labour Department",
    "Commercial Taxes",
    "BBMP Trade License",
    "BESCOM (Power)",
    "Pollution Control Board",
    "KSPCB (Pollution Control)",
]

Status = Literal["Active", "Dormant", "Closed", "Unknown"]


@dataclass
class SourceRecord:
    id: str
    department: str
    businessName: str
    address: str
    pinCode: str
    ownerName: str
    pan: Optional[str] = None
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "department": self.department,
            "businessName": self.businessName,
            "address": self.address,
            "pinCode": self.pinCode,
            "ownerName": self.ownerName,
            "pan": self.pan,
            "gstin": self.gstin,
            "phone": self.phone,
            "email": self.email,
            **self.extra,
        }


@dataclass
class StatusChange:
    from_status: Status
    to_status: Literal["Active", "Dormant", "Closed"]
    reason: str
    timestamp: str
    actor: str
    type: Literal["System", "Manual"]

    def to_dict(self) -> dict:
        return {
            "from": self.from_status,
            "to": self.to_status,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "type": self.type,
        }


@dataclass
class ManualStatusOverride:
    status: Literal["Active", "Dormant", "Closed"]
    reason: str
    timestamp: str
    actor: str


@dataclass
class UBIDRecord:
    ubid: str
    anchorType: Literal["Central", "Internal"]
    canonicalName: str
    canonicalAddress: str
    pinCode: str
    status: Literal["Active", "Dormant", "Closed"]
    confidence: float
    riskScore: float  # 0-100
    evidence: list[str]
    lastUpdated: str
    linkedRecords: list[SourceRecord] = field(default_factory=list)
    anchorId: Optional[str] = None
    pan: Optional[str] = None
    gstin: Optional[str] = None
    statusHistory: list[StatusChange] = field(default_factory=list)
    manualStatusOverride: Optional[ManualStatusOverride] = None
    unlinkedRecordIds: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ubid": self.ubid,
            "anchorType": self.anchorType,
            "anchorId": self.anchorId,
            "canonicalName": self.canonicalName,
            "canonicalAddress": self.canonicalAddress,
            "pinCode": self.pinCode,
            "pan": self.pan,
            "gstin": self.gstin,
            "status": self.status,
            "statusHistory": [s.to_dict() for s in self.statusHistory],
            "confidence": self.confidence,
            "riskScore": self.riskScore,
            "evidence": self.evidence,
            "lastUpdated": self.lastUpdated,
            "linkedRecords": [r.to_dict() for r in self.linkedRecords],
            "unlinkedRecordIds": self.unlinkedRecordIds,
        }


@dataclass
class ActivityEvent:
    id: str
    ubid: str
    department: str
    eventType: str
    date: str
    details: str
    value: Literal["High", "Medium", "Low", "Critical"]
    businessNameHint: Optional[str] = None
    addressHint: Optional[str] = None
    pinCodeHint: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ubid": self.ubid,
            "department": self.department,
            "eventType": self.eventType,
            "date": self.date,
            "details": self.details,
            "value": self.value,
            "businessNameHint": self.businessNameHint,
            "addressHint": self.addressHint,
            "pinCodeHint": self.pinCodeHint,
        }


@dataclass
class SystemKnowledge:
    manualLinks: list[dict[str, str]] = field(default_factory=list)  # [{recordId, ubid}]
    manualBlacklist: list[dict[str, str]] = field(default_factory=list)  # [{recordIdA, recordIdB}]
    learnedWeights: dict[str, float] = field(default_factory=lambda: {
        "nameWeight": 0.5,
        "addressWeight": 0.3,
        "pinWeight": 0.2,
    })


@dataclass
class MatchSuggestion:
    id: str
    recordA: SourceRecord
    recordB: SourceRecord
    confidence: float
    reasons: list[str]
    status: Literal["Pending", "Approved", "Rejected", "Auto-Committed"]
    confidenceBreakdown: Optional[dict[str, float]] = None
    riskFactors: Optional[list[str]] = None
    priority: Optional[Literal["High", "Medium", "Low"]] = None
    reviewerFeedback: Optional[dict] = None


@dataclass
class AuditEntry:
    id: str
    timestamp: str
    action: str
    actor: str
    entityId: str
    details: str
    type: Literal["Security", "Governance", "System"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "entityId": self.entityId,
            "details": self.details,
            "type": self.type,
        }
