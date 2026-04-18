"""
mock_data.py
Equivalent to src/mockData.ts — seed data for development / testing.
"""

from __future__ import annotations
import random
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from models import SourceRecord, ActivityEvent, UBIDRecord, StatusChange

DEPARTMENTS = [
    "Shop & Establishment",
    "Factories",
    "Labour",
    "KSPCB",
    "BESCOM",
]

SAMPLE_NAMES = [
    "Sri Lakshmi Enterprises",
    "Laxmi Ent.",
    "Peenya Precision Tools",
    "Precision Tools & Dies",
    "Karnataka Steel Works",
    "KA Steel Works Pvt Ltd",
    "Green Valley Agro",
    "Green Valley Agricultural Products",
    "Modern Textiles",
    "Modern Textile Mills",
]

SAMPLE_ADDRESSES = [
    "Plot 45, 2nd Phase, Peenya Industrial Area",
    "No 45, Peenya 2nd Phase, Bangalore",
    "12/A, Industrial Suburb, Yeshwanthpur",
    "12A, Yeshwanthpur Industrial Suburb",
    "Survey No 89, Whitefield Main Road",
    "89, Main Rd, Whitefield",
]


def _months_ago(n: float) -> datetime:
    now = datetime.now(timezone.utc)
    full_months = int(n)
    extra_days = int((n - full_months) * 30)
    return now - relativedelta(months=full_months, days=extra_days)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def generate_mock_data() -> dict:
    """
    Returns {'sourceRecords': [...]} — a list of SourceRecord objects
    simulating entity resolution needs (2-3 records per business).
    """
    source_records: list[SourceRecord] = []
    rng = random.Random(42)  # fixed seed for reproducibility

    for i in range(20):
        base_name = rng.choice(SAMPLE_NAMES)
        base_addr = rng.choice(SAMPLE_ADDRESSES)
        pin = "560058"
        pan = f"ABCDE{1000 + i}F" if rng.random() > 0.3 else None

        num_records = rng.randint(2, 3)
        for j in range(num_records):
            name = base_name if j == 0 else base_name[: max(3, len(base_name) - rng.randint(1, 5))]
            addr = (
                base_addr
                if j == 0
                else base_addr.replace("Road", "RD").replace("Industrial", "Ind.")
            )
            source_records.append(
                SourceRecord(
                    id=f"REC-{i}-{j}",
                    department=rng.choice(DEPARTMENTS),
                    businessName=name,
                    address=addr,
                    pinCode=pin,
                    pan=pan,
                    ownerName="White Hawk Coders",
                )
            )

    return {"sourceRecords": source_records}


# ---------------------------------------------------------------------------
# Static mock UBID registry
# ---------------------------------------------------------------------------

MOCK_UBIDS: list[UBIDRecord] = [
    UBIDRecord(
        ubid="KA-7L8K2P9R-5",
        anchorType="Central",
        anchorId="29AAAAA0000A1Z5",
        canonicalName="Sri Lakshmi Enterprises",
        canonicalAddress="Plot 45, 2nd Phase, Peenya Industrial Area, Bangalore 560058",
        pinCode="560058",
        pan="ABCDE1234F",
        gstin="29AAAAA0000A1Z5",
        status="Active",
        statusHistory=[
            StatusChange(
                from_status="Unknown",
                to_status="Active",
                reason="Initial Entity Resolution",
                timestamp=_months_ago(0.6).isoformat(),
                actor="System (Anchoring Logic)",
                type="System",
            )
        ],
        confidence=0.99,
        riskScore=12,
        evidence=[
            "GSTIN Exact Match (Commercial Taxes)",
            "PAN Match (Factories)",
            "Address Fuzzy Match (Labour)",
        ],
        lastUpdated=_fmt(_months_ago(0.5)),
        linkedRecords=[
            SourceRecord(
                id="R1",
                department="Factories",
                businessName="Sri Lakshmi Enterprises",
                address="Plot 45, Peenya",
                pinCode="560058",
                pan="ABCDE1234F",
                gstin="29AAAAA0000A1Z5",
                ownerName="White Hawk",
            ),
            SourceRecord(
                id="R2",
                department="Labour",
                businessName="Laxmi Ent.",
                address="45, 2nd Phase Peenya",
                pinCode="560058",
                ownerName="White Hawk",
            ),
        ],
    ),
    UBIDRecord(
        ubid="KA-B4V6N1M8-X",
        anchorType="Central",
        anchorId="BPLAS8899K",
        canonicalName="Bharath Plastics Ltd",
        canonicalAddress="No 22, 1st Cross, Peenya 1st Stage, Bangalore 560058",
        pinCode="560058",
        pan="BPLAS8899K",
        status="Active",
        statusHistory=[
            StatusChange(
                from_status="Unknown",
                to_status="Active",
                reason="PAN-based Anchor Creation",
                timestamp=_months_ago(4.2).isoformat(),
                actor="System (Risk Engine)",
                type="System",
            )
        ],
        confidence=0.94,
        riskScore=35,
        evidence=["PAN Match (KSPCB)", "Name Match (KSPCB)"],
        lastUpdated=_fmt(_months_ago(4)),
        linkedRecords=[
            SourceRecord(
                id="R21",
                department="KSPCB",
                businessName="Bharath Plastics",
                address="22, 1st Cross, Peenya",
                pinCode="560058",
                pan="BPLAS8899K",
                ownerName="Gopal Krishnan",
            )
        ],
    ),
    UBIDRecord(
        ubid="KA-X9W3Q7Z2-K",
        anchorType="Internal",
        canonicalName="Green Valley Agro",
        canonicalAddress="No 124, Bagalur Road, Yelahanka, Bangalore 560063",
        pinCode="560063",
        status="Closed",
        statusHistory=[
            StatusChange(
                from_status="Active",
                to_status="Dormant",
                reason="No signals detected (6m Gap)",
                timestamp=_months_ago(5.5).isoformat(),
                actor="System (Logic Engine)",
                type="System",
            ),
            StatusChange(
                from_status="Dormant",
                to_status="Closed",
                reason="Explicit Disconnection Event",
                timestamp=_months_ago(5.1).isoformat(),
                actor="BESCOM Data Processing",
                type="System",
            ),
        ],
        confidence=0.78,
        riskScore=88,
        evidence=["Name Match (Labour)", "Address Fuzzy Match (Factories)"],
        lastUpdated=_fmt(_months_ago(5)),
        linkedRecords=[
            SourceRecord(
                id="R6",
                department="Labour",
                businessName="Green Valley Agro",
                address="124 Bagalur Rd",
                pinCode="560063",
                ownerName="Meena S.",
            ),
            SourceRecord(
                id="R7",
                department="Factories",
                businessName="Green Valley Agricultural Products",
                address="No 124, Yelahanka",
                pinCode="560063",
                ownerName="Meena S.",
            ),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Static mock activity events
# ---------------------------------------------------------------------------

MOCK_EVENTS: list[ActivityEvent] = [
    ActivityEvent(
        id="E1",
        ubid="KA-7L8K2P9R-5",
        department="KSPCB",
        eventType="Inspection",
        date=_fmt(_months_ago(2)),
        details="Routine environmental compliance check",
        value="High",
        businessNameHint="Sri Lakshmi Enterprises",
        addressHint="Plot 45, Peenya Ind Area",
        pinCodeHint="560058",
    ),
    ActivityEvent(
        id="E2",
        ubid="KA-7L8K2P9R-5",
        department="BESCOM",
        eventType="Bill Payment",
        date=_fmt(_months_ago(1)),
        details="Monthly electricity bill paid",
        value="Low",
    ),
    ActivityEvent(
        id="E3",
        ubid="KA-B4V6N1M8-X",
        department="Labour",
        eventType="Compliance Filing",
        date=_fmt(_months_ago(14)),
        details="Annual return filed",
        value="High",
        businessNameHint="Bharath Plastics",
        pinCodeHint="560058",
    ),
    ActivityEvent(
        id="E4",
        ubid="KA-7L8K2P9R-5",
        department="Factories",
        eventType="Safety Audit",
        date=_fmt(_months_ago(3)),
        details="Quarterly safety standards verification",
        value="High",
    ),
    ActivityEvent(
        id="E5",
        ubid="KA-B4V6N1M8-X",
        department="KSPCB",
        eventType="Renewal",
        date=_fmt(_months_ago(6)),
        details="Pollution control certificate renewed",
        value="Medium",
    ),
    ActivityEvent(
        id="E6",
        ubid="KA-X9W3Q7Z2-K",
        department="BESCOM",
        eventType="Meter Reading",
        date=_fmt(_months_ago(0.5)),
        details="Industrial high-tension meter reading",
        value="Low",
    ),
    ActivityEvent(
        id="E7",
        ubid="KA-X9W3Q7Z2-K",
        department="Shop & Establishment",
        eventType="License Renewal",
        date=_fmt(_months_ago(10)),
        details="Trade license successfully renewed",
        value="High",
    ),
    ActivityEvent(
        id="E8",
        ubid="KA-X9W3Q7Z2-K",
        department="BESCOM",
        eventType="Disconnection",
        date=_fmt(_months_ago(5)),
        details="Power supply disconnected on request",
        value="Critical",
    ),
    ActivityEvent(
        id="E11",
        ubid="KA-7L8K2P9R-5",
        department="Factories",
        eventType="Safety Audit",
        date=_fmt(_months_ago(0.5)),
        details="CNC workshop safety certification",
        value="High",
    ),
    ActivityEvent(
        id="E12",
        ubid="KA-B4V6N1M8-X",
        department="KSPCB",
        eventType="Emission Test",
        date=_fmt(_months_ago(1)),
        details="Plastic moulding emission monitoring",
        value="Medium",
    ),
    ActivityEvent(
        id="E13",
        ubid="",
        department="Labour",
        eventType="Inspection",
        date=_fmt(_months_ago(0.1)),
        details="Child labour compliance verification",
        value="High",
        businessNameHint="SRI LAXMI ENT",
        addressHint="45, PEENYA II PHASE",
        pinCodeHint="560058",
    ),
    ActivityEvent(
        id="E14",
        ubid="",
        department="BESCOM",
        eventType="Load Upgrade",
        date=_fmt(_months_ago(0.2)),
        details="Request for 50HP power upgrade",
        value="Medium",
        businessNameHint="GREEN VALEY AGRO",
        addressHint="124, BAGALUR RD",
        pinCodeHint="560063",
    ),
]
