"""
app.py  —  Karnataka UBID Intelligence Platform
Streamlit deployment entry point.

Run:
    streamlit run app.py
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import uuid
import json
from datetime import datetime, timezone

import streamlit as st

# ── page config must be first ──────────────────────────────────────────────
st.set_page_config(
    page_title="UBID Intelligence Platform",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── local imports ──────────────────────────────────────────────────────────
from models import SourceRecord, UBIDRecord, ActivityEvent, SystemKnowledge, AuditEntry
from mock_data import MOCK_UBIDS, MOCK_EVENTS, generate_mock_data
from ubid_service import resolve_ubids, generate_unified_business_identifier
from status_inference_service import infer_business_status, find_orphan_events
from fuzzy_matching_service import compare_records

# ══════════════════════════════════════════════════════════════════════════
# Custom CSS  — dark industrial theme matching the original React design
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

/* Root palette */
:root {
    --bg:        #0f1117;
    --card:      #1a1d27;
    --border:    #2a2d3e;
    --accent:    #3b82f6;
    --accent2:   #06b6d4;
    --active:    #22c55e;
    --dormant:   #f59e0b;
    --closed:    #ef4444;
    --text:      #e2e8f0;
    --muted:     #64748b;
    --sidebar:   #111320;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--sidebar) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 13px !important; }

/* Cards */
.ubid-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 10px;
    font-family: 'IBM Plex Sans', sans-serif;
}
.ubid-card:hover { border-color: var(--accent); transition: border-color .2s; }

/* Stat boxes */
.stat-box {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    text-align: center;
}
.stat-box .stat-val {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
}
.stat-box .stat-lbl {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: var(--muted);
    margin-top: 4px;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .05em;
    font-family: 'IBM Plex Mono', monospace;
}
.badge-active  { background:#052e16; color:#22c55e; border:1px solid #166534; }
.badge-dormant { background:#431407; color:#f59e0b; border:1px solid #92400e; }
.badge-closed  { background:#450a0a; color:#ef4444; border:1px solid #991b1b; }
.badge-central { background:#0c1a3a; color:#60a5fa; border:1px solid #1e40af; }
.badge-internal{ background:#1c1033; color:#a78bfa; border:1px solid #5b21b6; }

/* UBID mono */
.ubid-mono {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--accent2);
    letter-spacing: .05em;
}

/* Risk bar */
.risk-wrap { display:flex; align-items:center; gap:8px; }
.risk-bar-outer { flex:1; height:6px; background:#1e293b; border-radius:3px; overflow:hidden; }
.risk-bar-inner { height:100%; border-radius:3px; }

/* Evidence pill */
.ev-pill {
    display:inline-block;
    background:#0f172a;
    border:1px solid var(--border);
    border-radius:20px;
    padding:2px 10px;
    font-size:11px;
    color:#94a3b8;
    margin:2px 3px;
}

/* Section header */
.section-hdr {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .12em;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
    margin: 18px 0 10px;
    font-family: 'IBM Plex Mono', monospace;
}

/* Timeline dot */
.tl-row { display:flex; gap:12px; align-items:flex-start; margin-bottom:8px; }
.tl-dot { width:8px; height:8px; border-radius:50%; margin-top:5px; flex-shrink:0; }

/* Metric delta override */
[data-testid="stMetricDelta"] { font-size:11px; }

/* Audit row */
.audit-row {
    border-left: 3px solid var(--border);
    padding-left: 12px;
    margin-bottom: 10px;
}
.audit-row.sec { border-color: var(--closed); }
.audit-row.gov { border-color: var(--accent); }
.audit-row.sys { border-color: var(--muted); }

/* Chat bubble */
.chat-user { background:#1e3a5f; border-radius:8px 8px 2px 8px; padding:10px 14px; margin:6px 0; font-size:13px; }
.chat-ai   { background:#1a2435; border-radius:8px 8px 8px 2px; padding:10px 14px; margin:6px 0; font-size:13px; border-left:3px solid var(--accent); }

/* Orphan signal card */
.orphan-card {
    background: #1a1320;
    border: 1px solid #3b1d4a;
    border-radius:8px;
    padding:14px;
    margin-bottom:8px;
}

/* Input overrides */
.stTextInput input, .stSelectbox select, .stTextArea textarea {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
.stButton button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
.stButton button:hover { background:#2563eb !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# Session state initialisation
# ══════════════════════════════════════════════════════════════════════════
if "ubids" not in st.session_state:
    st.session_state.ubids: list[UBIDRecord] = list(MOCK_UBIDS)
if "events" not in st.session_state:
    st.session_state.events: list[ActivityEvent] = list(MOCK_EVENTS)
if "knowledge" not in st.session_state:
    st.session_state.knowledge = SystemKnowledge()
if "audit_log" not in st.session_state:
    st.session_state.audit_log: list[AuditEntry] = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history: list[dict] = []
if "selected_ubid" not in st.session_state:
    st.session_state.selected_ubid = None


def log_audit(action: str, entity_id: str, details: str, audit_type: str = "Governance"):
    st.session_state.audit_log.append(AuditEntry(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now(timezone.utc).isoformat(),
        action=action,
        actor="Senior Reviewer",
        entityId=entity_id,
        details=details,
        type=audit_type,
    ))


# ══════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding:10px 0 20px'>
      <div style='display:flex;align-items:center;gap:10px;margin-bottom:24px'>
        <div style='width:36px;height:36px;background:#3b82f6;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:18px'>🏭</div>
        <div>
          <div style='color:#fff;font-weight:700;font-size:13px;letter-spacing:.05em'>UBID PLATFORM</div>
          <div style='color:#475569;font-size:10px'>Karnataka Registry v2.0</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "🔍 UBID Explorer", "🗂 Central Registry",
         "👥 Reviewer Queue", "⚠️ Orphan Signals",
         "📜 Audit Ledger", "💬 AI Chat", "🧠 AI Deep Analysis",
         "⚙️ Entity Resolution"],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color:#2a2d3e;margin:20px 0'>", unsafe_allow_html=True)

    # Live status indicator
    active_count = sum(1 for u in st.session_state.ubids if u.status == "Active")
    total = len(st.session_state.ubids)
    health_pct = (active_count / total * 100) if total else 0
    st.markdown(f"""
    <div style='font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>
        Registry Status
    </div>
    <div style='display:flex;align-items:center;gap:6px;margin-bottom:4px'>
        <div style='width:7px;height:7px;background:#22c55e;border-radius:50%;
                    box-shadow:0 0 6px #22c55e'></div>
        <span style='color:#22c55e;font-size:11px;font-weight:700'>ONLINE</span>
    </div>
    <div style='font-size:11px;color:#64748b'>{total} UBIDs · {health_pct:.0f}% healthy</div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:11px;color:#334155'>
        <div style='color:#94a3b8;font-weight:700'>White Hawk Coders</div>
        <div style='color:#475569'>Senior Reviewer</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# Helper rendering functions
# ══════════════════════════════════════════════════════════════════════════

def status_badge(status: str) -> str:
    cls = {"Active": "badge-active", "Dormant": "badge-dormant", "Closed": "badge-closed"}.get(status, "")
    return f'<span class="badge {cls}">{status}</span>'


def anchor_badge(anchor: str) -> str:
    cls = "badge-central" if anchor == "Central" else "badge-internal"
    return f'<span class="badge {cls}">{anchor}</span>'


def risk_bar(score: float) -> str:
    color = "#ef4444" if score > 70 else "#f59e0b" if score > 40 else "#22c55e"
    return f"""
    <div class="risk-wrap">
        <div class="risk-bar-outer">
            <div class="risk-bar-inner" style="width:{score}%;background:{color}"></div>
        </div>
        <span style="font-size:11px;color:#94a3b8;font-family:'IBM Plex Mono',monospace">{score:.0f}</span>
    </div>"""


def render_ubid_card(u: UBIDRecord, clickable: bool = True):
    ev_pills = "".join(f'<span class="ev-pill">{e}</span>' for e in u.evidence[:3])
    linked_count = len(u.linkedRecords)
    st.markdown(f"""
    <div class="ubid-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
            <div>
                <div style="font-weight:700;font-size:15px;color:#e2e8f0;margin-bottom:4px">{u.canonicalName}</div>
                <div class="ubid-mono">{u.ubid}</div>
            </div>
            <div style="text-align:right">
                {status_badge(u.status)}&nbsp;{anchor_badge(u.anchorType)}
            </div>
        </div>
        <div style="font-size:12px;color:#64748b;margin-bottom:10px">📍 {u.canonicalAddress} &nbsp;·&nbsp; PIN {u.pinCode}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:10px">
            <div>
                <div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.08em">Confidence</div>
                <div style="font-size:14px;font-weight:700;color:#60a5fa">{u.confidence:.0%}</div>
            </div>
            <div>
                <div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.08em">Risk Score</div>
                {risk_bar(u.riskScore)}
            </div>
            <div>
                <div style="font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.08em">Records</div>
                <div style="font-size:14px;font-weight:700;color:#e2e8f0">{linked_count}</div>
            </div>
        </div>
        <div>{ev_pills}</div>
        <div style="font-size:10px;color:#334155;margin-top:8px">Updated {u.lastUpdated}</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ══════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("<h2 style='color:#e2e8f0;font-family:IBM Plex Sans;margin-bottom:4px'>Operations Dashboard</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:13px;margin-bottom:24px'>Real-time registry intelligence across Karnataka industrial zones</div>", unsafe_allow_html=True)

    ubids = st.session_state.ubids
    events = st.session_state.events

    active  = sum(1 for u in ubids if u.status == "Active")
    dormant = sum(1 for u in ubids if u.status == "Dormant")
    closed  = sum(1 for u in ubids if u.status == "Closed")
    total   = len(ubids)
    orphans = len(find_orphan_events(events, ubids))
    health  = (active / total * 100) if total else 0

    # Stat row
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, val, lbl, color in [
        (c1, total,    "Total UBIDs",       "#60a5fa"),
        (c2, active,   "Active Businesses", "#22c55e"),
        (c3, dormant,  "Dormant",           "#f59e0b"),
        (c4, closed,   "Closed",            "#ef4444"),
        (c5, orphans,  "Orphan Signals",    "#a78bfa"),
    ]:
        col.markdown(f"""
        <div class="stat-box">
            <div class="stat-val" style="color:{color}">{val}</div>
            <div class="stat-lbl">{lbl}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    left, right = st.columns([3, 2])

    with left:
        st.markdown("<div class='section-hdr'>Geospatial Registry Density — by PIN Code</div>", unsafe_allow_html=True)
        pin_stats: dict[str, dict] = {}
        for u in ubids:
            p = pin_stats.setdefault(u.pinCode, {"count": 0, "active": 0})
            p["count"] += 1
            if u.status == "Active":
                p["active"] += 1
        max_count = max((s["count"] for s in pin_stats.values()), default=1)
        for pin, s in sorted(pin_stats.items(), key=lambda x: -x[1]["count"]):
            bar_w = int(s["count"] / max_count * 100)
            active_w = int(s["active"] / max_count * 100)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <div style="width:60px;font-size:11px;color:#94a3b8;font-family:'IBM Plex Mono',monospace">{pin}</div>
                <div style="flex:1;height:8px;background:#1e293b;border-radius:4px;overflow:hidden;position:relative">
                    <div style="width:{bar_w}%;height:100%;background:#1e3a5f;position:absolute"></div>
                    <div style="width:{active_w}%;height:100%;background:#3b82f6;position:absolute"></div>
                </div>
                <div style="font-size:12px;font-weight:700;color:#e2e8f0;width:20px;text-align:right">{s['count']}</div>
                <div style="font-size:10px;color:#22c55e;width:30px">+{s['active']}</div>
            </div>""", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='section-hdr'>Status Distribution</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px">
            {''.join(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <div style="display:flex;align-items:center;gap:8px">
                    <div style="width:10px;height:10px;border-radius:50%;background:{color}"></div>
                    <span style="font-size:13px;color:#94a3b8">{label}</span>
                </div>
                <div>
                    <span style="font-size:16px;font-weight:700;color:{color}">{count}</span>
                    <span style="font-size:10px;color:#475569;margin-left:4px">({count/total*100:.0f}%)</span>
                </div>
            </div>
            """ for label, count, color in [
                ("Active",  active,  "#22c55e"),
                ("Dormant", dormant, "#f59e0b"),
                ("Closed",  closed,  "#ef4444"),
            ])}
            <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
                <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Compliance Health</div>
                <div style="height:8px;background:#1e293b;border-radius:4px;overflow:hidden">
                    <div style="width:{health:.0f}%;height:100%;background:linear-gradient(90deg,#22c55e,#3b82f6);border-radius:4px"></div>
                </div>
                <div style="font-size:13px;font-weight:700;color:#60a5fa;margin-top:6px">{health:.1f}%</div>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='section-hdr'>Recent Activity Feed</div>", unsafe_allow_html=True)
    recent = sorted(events, key=lambda e: e.date, reverse=True)[:8]
    value_color = {"High": "#ef4444", "Critical": "#a855f7", "Medium": "#f59e0b", "Low": "#22c55e"}
    for e in recent:
        col = value_color.get(e.value, "#64748b")
        st.markdown(f"""
        <div style="display:flex;gap:14px;align-items:center;padding:8px 0;border-bottom:1px solid #1e293b">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#475569;width:90px">{e.date}</div>
            <div style="width:8px;height:8px;border-radius:50%;background:{col};flex-shrink:0"></div>
            <div style="flex:1;font-size:13px;color:#94a3b8">{e.eventType}</div>
            <div style="font-size:11px;color:#475569;width:140px">{e.department}</div>
            <div><span class="badge" style="background:#0f172a;color:{col};border:1px solid {col}30">{e.value}</span></div>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: UBID Explorer
# ══════════════════════════════════════════════════════════════════════════
elif page == "🔍 UBID Explorer":
    st.markdown("<h2 style='color:#e2e8f0;font-family:IBM Plex Sans'>UBID Explorer</h2>", unsafe_allow_html=True)

    ubids = st.session_state.ubids
    events = st.session_state.events

    query = st.text_input("🔎 Search by UBID, Name, PAN, GSTIN or PIN", placeholder="e.g. Lakshmi, 560058, KA-7L…")

    filtered = [
        u for u in ubids
        if not query
        or query.lower() in u.ubid.lower()
        or query.lower() in u.canonicalName.lower()
        or query.lower() in (u.pan or "").lower()
        or query.lower() in (u.gstin or "").lower()
        or query in u.pinCode
    ]

    st.markdown(f"<div style='color:#475569;font-size:12px;margin-bottom:12px'>{len(filtered)} result(s)</div>", unsafe_allow_html=True)

    col_list, col_detail = st.columns([2, 3])

    with col_list:
        for u in filtered:
            clicked = st.button(
                f"{u.canonicalName[:28]}…" if len(u.canonicalName) > 28 else u.canonicalName,
                key=f"sel_{u.ubid}",
                use_container_width=True,
            )
            if clicked:
                st.session_state.selected_ubid = u.ubid

    with col_detail:
        sel_id = st.session_state.selected_ubid
        sel = next((u for u in ubids if u.ubid == sel_id), filtered[0] if filtered else None)

        if sel:
            render_ubid_card(sel, clickable=False)

            # Status inference
            verdict = infer_business_status(sel.ubid, events)
            inf_color = {"Active": "#22c55e", "Dormant": "#f59e0b", "Closed": "#ef4444"}.get(verdict.status, "#64748b")
            st.markdown(f"""
            <div class="ubid-card" style="border-left:3px solid {inf_color}">
                <div class="section-hdr" style="margin-top:0">AI Status Inference</div>
                <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px">
                    {status_badge(verdict.status)}
                    <span style="font-size:13px;color:#94a3b8">Confidence: <b style="color:{inf_color}">{verdict.confidence:.0%}</b></span>
                </div>
                <div style="font-size:12px;color:#64748b">{verdict.reasoning}</div>
            </div>""", unsafe_allow_html=True)

            # Event timeline
            ubid_events = sorted(
                [e for e in events if e.ubid == sel.ubid],
                key=lambda e: e.date, reverse=True
            )
            if ubid_events:
                st.markdown("<div class='section-hdr'>Activity Timeline</div>", unsafe_allow_html=True)
                for ev in ubid_events:
                    col_ev = {"High":"#ef4444","Critical":"#a855f7","Medium":"#f59e0b","Low":"#22c55e"}.get(ev.value,"#64748b")
                    st.markdown(f"""
                    <div class="tl-row">
                        <div class="tl-dot" style="background:{col_ev}"></div>
                        <div>
                            <div style="font-size:12px;font-weight:600;color:#e2e8f0">{ev.eventType}</div>
                            <div style="font-size:11px;color:#475569">{ev.department} · {ev.date}</div>
                            <div style="font-size:11px;color:#64748b">{ev.details}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)

            # Linked source records
            st.markdown("<div class='section-hdr'>Linked Source Records</div>", unsafe_allow_html=True)
            for r in sel.linkedRecords:
                st.markdown(f"""
                <div style="display:flex;gap:12px;align-items:center;padding:8px;background:#111827;
                            border-radius:6px;margin-bottom:6px;border:1px solid var(--border)">
                    <div style="width:6px;height:6px;border-radius:50%;background:#3b82f6;flex-shrink:0"></div>
                    <div style="flex:1">
                        <div style="font-size:13px;font-weight:600;color:#e2e8f0">{r.businessName}</div>
                        <div style="font-size:11px;color:#475569">{r.department} · {r.address}</div>
                    </div>
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#475569">{r.id}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#475569;padding:40px 0;text-align:center'>Select a UBID from the list</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Central Registry
# ══════════════════════════════════════════════════════════════════════════
elif page == "🗂 Central Registry":
    st.markdown("<h2 style='color:#e2e8f0'>Central Registry</h2>", unsafe_allow_html=True)

    ubids = st.session_state.ubids
    status_filter = st.selectbox("Filter by Status", ["All", "Active", "Dormant", "Closed"])
    anchor_filter = st.selectbox("Filter by Anchor", ["All", "Central", "Internal"])

    shown = [
        u for u in ubids
        if (status_filter == "All" or u.status == status_filter)
        and (anchor_filter == "All" or u.anchorType == anchor_filter)
    ]

    # Table header
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr;
                gap:8px;padding:8px 12px;background:#111827;border-radius:6px;
                font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:#475569;
                font-family:'IBM Plex Mono',monospace;margin-bottom:4px">
        <div>Entity Name</div><div>UBID</div><div>Status</div>
        <div>Anchor</div><div>Risk</div><div>Records</div>
    </div>""", unsafe_allow_html=True)

    for u in shown:
        risk_color = "#ef4444" if u.riskScore > 70 else "#f59e0b" if u.riskScore > 40 else "#22c55e"
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr 1fr;
                    gap:8px;padding:10px 12px;background:var(--card);border:1px solid var(--border);
                    border-radius:6px;margin-bottom:3px;align-items:center">
            <div style="font-size:13px;font-weight:600;color:#e2e8f0">{u.canonicalName}</div>
            <div class="ubid-mono" style="font-size:10px">{u.ubid[:14]}…</div>
            <div>{status_badge(u.status)}</div>
            <div>{anchor_badge(u.anchorType)}</div>
            <div style="font-size:12px;font-weight:700;color:{risk_color}">{u.riskScore:.0f}</div>
            <div style="font-size:12px;color:#94a3b8">{len(u.linkedRecords)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"<div style='color:#475569;font-size:11px;margin-top:8px'>Showing {len(shown)} of {len(ubids)} UBIDs</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Reviewer Queue
# ══════════════════════════════════════════════════════════════════════════
elif page == "👥 Reviewer Queue":
    st.markdown("<h2 style='color:#e2e8f0'>Reviewer Queue</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:13px;margin-bottom:20px'>Fuzzy match suggestions awaiting human review</div>", unsafe_allow_html=True)

    data = generate_mock_data()
    src = data["sourceRecords"]
    suggestions = []
    seen = set()

    for i, a in enumerate(src):
        for b in src[i + 1:]:
            if a.pinCode != b.pinCode:
                continue
            pair_key = tuple(sorted([a.id, b.id]))
            if pair_key in seen:
                continue
            seen.add(pair_key)
            result = compare_records(a, b, st.session_state.knowledge)
            if 0.55 <= result["confidence"] < 0.99:
                suggestions.append({
                    "recordA": a, "recordB": b,
                    "confidence": result["confidence"],
                    "reasons": result["reasons"],
                    "risk_factors": result["risk_factors"],
                })

    suggestions.sort(key=lambda s: -s["confidence"])

    if not suggestions:
        st.info("No pending match suggestions.")
    else:
        st.markdown(f"<div style='color:#475569;font-size:12px;margin-bottom:12px'>{len(suggestions)} suggestions pending</div>", unsafe_allow_html=True)

    for i, s in enumerate(suggestions[:12]):
        conf = s["confidence"]
        conf_color = "#22c55e" if conf > 0.85 else "#f59e0b" if conf > 0.7 else "#ef4444"
        priority = "High" if conf > 0.85 else "Medium" if conf > 0.7 else "Low"
        priority_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}[priority]

        with st.expander(f"[{priority}] {s['recordA'].businessName}  ↔  {s['recordB'].businessName}   —   {conf:.0%} match"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div class="ubid-card">
                    <div style="font-size:10px;color:#475569;margin-bottom:4px">RECORD A · {s['recordA'].id}</div>
                    <div style="font-weight:700;color:#e2e8f0">{s['recordA'].businessName}</div>
                    <div style="font-size:12px;color:#64748b">{s['recordA'].address}</div>
                    <div style="font-size:11px;color:#475569;margin-top:6px">
                        PIN: {s['recordA'].pinCode} &nbsp;·&nbsp; {s['recordA'].department}
                    </div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="ubid-card">
                    <div style="font-size:10px;color:#475569;margin-bottom:4px">RECORD B · {s['recordB'].id}</div>
                    <div style="font-weight:700;color:#e2e8f0">{s['recordB'].businessName}</div>
                    <div style="font-size:12px;color:#64748b">{s['recordB'].address}</div>
                    <div style="font-size:11px;color:#475569;margin-top:6px">
                        PIN: {s['recordB'].pinCode} &nbsp;·&nbsp; {s['recordB'].department}
                    </div>
                </div>""", unsafe_allow_html=True)

            st.markdown(f"""
            <div style="margin:8px 0">
                <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Match Signals</div>
                {''.join(f'<span class="ev-pill" style="color:#60a5fa;border-color:#1e3a5f">{r}</span>' for r in s['reasons'])}
            </div>""", unsafe_allow_html=True)

            if s["risk_factors"]:
                st.markdown(f"""
                <div style="margin-bottom:10px">
                    <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Risk Factors</div>
                    {''.join(f'<span class="ev-pill" style="color:#f59e0b;border-color:#451a03">{r}</span>' for r in s['risk_factors'])}
                </div>""", unsafe_allow_html=True)

            ba, bb, _ = st.columns([1, 1, 3])
            if ba.button("✅ Approve", key=f"approve_{i}", use_container_width=True):
                log_audit("Linkage Approved", s["recordA"].id, f"Linked with {s['recordB'].id}")
                st.success("Approved — records linked.")
            if bb.button("❌ Reject", key=f"reject_{i}", use_container_width=True):
                log_audit("Linkage Rejected", s["recordA"].id, f"Blacklisted from matching {s['recordB'].id}", "Security")
                st.warning("Rejected — pair blacklisted.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Orphan Signals
# ══════════════════════════════════════════════════════════════════════════
elif page == "⚠️ Orphan Signals":
    st.markdown("<h2 style='color:#e2e8f0'>Orphan Signals</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:13px;margin-bottom:20px'>Activity events that cannot be linked to any existing UBID</div>", unsafe_allow_html=True)

    orphans = find_orphan_events(st.session_state.events, st.session_state.ubids)

    if not orphans:
        st.success("✅ No orphan signals — all events are linked.")
    else:
        st.markdown(f"<div style='color:#f59e0b;font-size:13px;margin-bottom:12px'>⚠️ {len(orphans)} unlinked event(s) require resolution</div>", unsafe_allow_html=True)

        for orphan in orphans:
            val_color = {"High":"#ef4444","Critical":"#a855f7","Medium":"#f59e0b","Low":"#22c55e"}.get(orphan.value,"#64748b")
            st.markdown(f"""
            <div class="orphan-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <div style="font-size:10px;color:#7c3aed;font-family:'IBM Plex Mono',monospace;margin-bottom:4px">ORPHAN · {orphan.id}</div>
                        <div style="font-weight:700;font-size:15px;color:#e2e8f0">{orphan.eventType}</div>
                        <div style="font-size:12px;color:#64748b;margin-top:2px">{orphan.department} · {orphan.date}</div>
                        <div style="font-size:12px;color:#475569;margin-top:4px">{orphan.details}</div>
                    </div>
                    <span class="badge" style="color:{val_color};border-color:{val_color}40;background:{val_color}10">{orphan.value}</span>
                </div>
                {f'<div style="margin-top:10px;padding:8px;background:#0f0a1a;border-radius:4px;font-size:12px;color:#94a3b8"><b style="color:#7c3aed">Hint →</b> {orphan.businessNameHint} &nbsp;|&nbsp; {orphan.addressHint or "N/A"} &nbsp;|&nbsp; PIN {orphan.pinCodeHint or "?"}</div>' if orphan.businessNameHint else ''}
            </div>""", unsafe_allow_html=True)

            act_col, link_col, _ = st.columns([1, 2, 2])
            action = act_col.selectbox("Action", ["—", "Create New UBID", "Link to Existing"], key=f"act_{orphan.id}", label_visibility="collapsed")

            if action == "Create New UBID":
                if link_col.button("🆕 Project New Entity", key=f"create_{orphan.id}"):
                    new_id = f"KA-ORPHAN-{orphan.id[:5].upper()}"
                    new_rec = SourceRecord(
                        id=f"SR-{orphan.id}", department=orphan.department,
                        businessName=orphan.businessNameHint or f"Unknown ({orphan.id})",
                        address=orphan.addressHint or "TBD",
                        pinCode=orphan.pinCodeHint or "000000", ownerName="Derived from Signal",
                    )
                    new_ubid = UBIDRecord(
                        ubid=new_id, anchorType="Internal",
                        canonicalName=new_rec.businessName, canonicalAddress=new_rec.address,
                        pinCode=new_rec.pinCode, status="Active",
                        confidence=0.75, riskScore=30,
                        evidence=[f"Resolved from Orphan: {orphan.eventType}"],
                        lastUpdated=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        linkedRecords=[new_rec],
                    )
                    st.session_state.ubids.append(new_ubid)
                    for e in st.session_state.events:
                        if e.id == orphan.id:
                            e.ubid = new_id
                    log_audit("Orphan Resolution", new_id, f"Projected from {orphan.eventType}")
                    st.success(f"Created {new_id}")
                    st.rerun()

            elif action == "Link to Existing":
                names = {u.ubid: u.canonicalName for u in st.session_state.ubids}
                target_id = link_col.selectbox("Select UBID", list(names.keys()),
                    format_func=lambda x: f"{x} — {names[x]}", key=f"link_sel_{orphan.id}")
                if st.button("🔗 Link Signal", key=f"do_link_{orphan.id}"):
                    for u in st.session_state.ubids:
                        if u.ubid == target_id:
                            u.evidence.append(f"Linked Orphan: {orphan.eventType}")
                    for e in st.session_state.events:
                        if e.id == orphan.id:
                            e.ubid = target_id
                    log_audit("Orphan Linkage", target_id, f"Linked signal {orphan.eventType}")
                    st.success(f"Linked to {target_id}")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Audit Ledger
# ══════════════════════════════════════════════════════════════════════════
elif page == "📜 Audit Ledger":
    st.markdown("<h2 style='color:#e2e8f0'>Audit Ledger</h2>", unsafe_allow_html=True)

    log = st.session_state.audit_log
    if not log:
        st.info("No audit entries yet. Approve/reject a match or resolve an orphan to generate entries.")
    else:
        type_filter = st.selectbox("Filter", ["All", "Governance", "Security", "System"])
        shown = [e for e in reversed(log) if type_filter == "All" or e.type == type_filter]
        st.markdown(f"<div style='color:#475569;font-size:12px;margin-bottom:12px'>{len(shown)} entries</div>", unsafe_allow_html=True)
        cls_map = {"Security": "sec", "Governance": "gov", "System": "sys"}
        color_map = {"Security": "#ef4444", "Governance": "#3b82f6", "System": "#64748b"}
        for entry in shown:
            cls = cls_map.get(entry.type, "sys")
            color = color_map.get(entry.type, "#64748b")
            st.markdown(f"""
            <div class="audit-row {cls}">
                <div style="display:flex;gap:10px;align-items:center;margin-bottom:2px">
                    <span class="badge" style="color:{color};border-color:{color}40;background:{color}10">{entry.type}</span>
                    <span style="font-size:12px;font-weight:600;color:#e2e8f0">{entry.action}</span>
                    <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#475569">{entry.entityId}</span>
                </div>
                <div style="font-size:11px;color:#64748b">{entry.details}</div>
                <div style="font-size:10px;color:#334155;margin-top:2px">{entry.timestamp[:19].replace('T',' ')} · {entry.actor}</div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: AI Chat
# ══════════════════════════════════════════════════════════════════════════
elif page == "💬 AI Chat":
    st.markdown("<h2 style='color:#e2e8f0'>AI Intelligence Chat</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:13px;margin-bottom:20px'>Natural-language interface to the UBID knowledge base</div>", unsafe_allow_html=True)

    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-…",
                             help="Your key is used only for this session and never stored.")

    # Display history
    for msg in st.session_state.chat_history:
        cls = "chat-user" if msg["role"] == "user" else "chat-ai"
        prefix = "🧑 You" if msg["role"] == "user" else "🤖 UBID AI"
        st.markdown(f"""
        <div class="{cls}">
            <div style="font-size:10px;color:#475569;margin-bottom:4px">{prefix}</div>
            <div style="font-size:13px;color:#e2e8f0">{msg['content']}</div>
        </div>""", unsafe_allow_html=True)

    user_msg = st.chat_input("Ask about UBID logic, status inference, matching rules…")
    if user_msg:
        if not api_key:
            st.warning("Please enter your Anthropic API key above.")
        else:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
            history.append({"role": "user", "content": user_msg})

            SYSTEM = """You are the UBID Intelligence Assistant for Karnataka's industrial registry.
STRICT RULES: 1. No pleasantries. 2. Numbered lists only. 3. One fact per line. 4. Max 5 lines."""

            with st.spinner("AI thinking…"):
                try:
                    resp = client.messages.create(
                        model="claude-opus-4-5", max_tokens=512,
                        system=SYSTEM, messages=history,
                    )
                    ai_text = resp.content[0].text
                    st.session_state.chat_history.append({"role": "user", "content": user_msg})
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_text})
                    st.rerun()
                except Exception as ex:
                    st.error(f"API error: {ex}")

    if st.session_state.chat_history:
        if st.button("🗑 Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# PAGE: AI Deep Analysis
# ══════════════════════════════════════════════════════════════════════════
elif page == "🧠 AI Deep Analysis":
    st.markdown("<h2 style='color:#e2e8f0'>AI Deep Analysis</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:13px;margin-bottom:20px'>High-thinking strategic audit on any registered entity</div>", unsafe_allow_html=True)

    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-…")

    ubids = st.session_state.ubids
    names = {u.ubid: f"{u.canonicalName} ({u.ubid})" for u in ubids}
    chosen_id = st.selectbox("Select Entity", list(names.keys()), format_func=lambda x: names[x])
    chosen = next(u for u in ubids if u.ubid == chosen_id)

    if st.button("🧠 Run Deep Analysis", use_container_width=True):
        if not api_key:
            st.warning("Enter your API key.")
        else:
            import anthropic, re, json as _json
            client = anthropic.Anthropic(api_key=api_key)

            ubid_events = [e for e in st.session_state.events if e.ubid == chosen_id]
            payload = {"entity": chosen.to_dict(), "recentActivity": [e.to_dict() for e in ubid_events]}

            # Anonymize
            raw = _json.dumps(payload)
            raw = re.sub(r"[A-Z]{5}[0-9]{4}[A-Z]{1}", "PLACEHOLDER_PAN", raw)
            raw = re.sub(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}", "PLACEHOLDER_GSTIN", raw)
            anon = _json.loads(raw)

            prompt = f"""Perform a Deep Strategic Audit on this industrial entity data.
TASK:
1. Analyze registry details for inconsistencies (PAN/GSTIN/Status).
2. Cross-reference the activity timeline — does it support the current status?
3. Identify hidden linkage risks (similar addresses, overlapping signals).
4. Predict future operational health from signal frequency trends.

Anonymized Data:
{_json.dumps(anon, indent=2)}"""

            with st.spinner("AI analysing… (this may take 15–30 seconds)"):
                try:
                    resp = client.messages.create(
                        model="claude-opus-4-5", max_tokens=1024,
                        system="You are a senior business intelligence analyst specialising in regulatory compliance and entity resolution.",
                        messages=[{"role": "user", "content": prompt}],
                    )
                    result = resp.content[0].text
                    log_audit("Deep Analysis", chosen_id, "AI strategic audit completed.", "System")
                    st.markdown(f"""
                    <div class="ubid-card" style="border-left:3px solid #3b82f6">
                        <div class="section-hdr" style="margin-top:0">Analysis Result — {chosen.canonicalName}</div>
                        <div style="font-size:13px;color:#94a3b8;white-space:pre-wrap;line-height:1.7">{result}</div>
                    </div>""", unsafe_allow_html=True)
                except Exception as ex:
                    st.error(f"API error: {ex}")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: Entity Resolution
# ══════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Entity Resolution":
    st.markdown("<h2 style='color:#e2e8f0'>Entity Resolution Engine</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:13px;margin-bottom:20px'>Run two-pass GSTIN/PAN anchoring + fuzzy grouping on raw source records</div>", unsafe_allow_html=True)

    data = generate_mock_data()
    src = data["sourceRecords"]
    st.markdown(f"<div style='color:#64748b;font-size:13px;margin-bottom:16px'>Source record pool: <b style='color:#e2e8f0'>{len(src)}</b> records across multiple departments</div>", unsafe_allow_html=True)

    # Preview source records
    with st.expander(f"Preview source records ({len(src)})"):
        for r in src[:10]:
            st.markdown(f"""
            <div style="display:flex;gap:10px;align-items:center;padding:6px 0;border-bottom:1px solid #1e293b">
                <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#475569;width:70px">{r.id}</div>
                <div style="flex:1;font-size:12px;color:#e2e8f0">{r.businessName}</div>
                <div style="font-size:11px;color:#64748b;width:180px">{r.department}</div>
                <div style="font-size:11px;color:#475569">{r.pinCode}</div>
            </div>""", unsafe_allow_html=True)
        if len(src) > 10:
            st.markdown(f"<div style='color:#475569;font-size:11px;padding-top:6px'>… and {len(src)-10} more</div>", unsafe_allow_html=True)

    if st.button("▶️  Run Entity Resolution", use_container_width=True):
        with st.spinner("Running two-pass resolution…"):
            resolved = resolve_ubids(src, st.session_state.knowledge)

        st.success(f"Resolved {len(src)} source records → {len(resolved)} unique UBIDs")
        st.markdown("<div class='section-hdr'>Generated UBIDs</div>", unsafe_allow_html=True)

        for u in resolved:
            conf_color = "#22c55e" if u.confidence > 0.9 else "#f59e0b" if u.confidence > 0.75 else "#ef4444"
            st.markdown(f"""
            <div class="ubid-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <div class="ubid-mono">{u.ubid}</div>
                        <div style="font-weight:700;font-size:14px;color:#e2e8f0;margin-top:2px">{u.canonicalName}</div>
                        <div style="font-size:11px;color:#64748b">{u.canonicalAddress} · PIN {u.pinCode}</div>
                    </div>
                    <div style="text-align:right">
                        {anchor_badge(u.anchorType)}
                        <div style="font-size:12px;color:{conf_color};margin-top:4px">{u.confidence:.0%} conf</div>
                    </div>
                </div>
                <div style="margin-top:8px;font-size:11px;color:#475569">
                    {len(u.linkedRecords)} linked records &nbsp;·&nbsp;
                    {''.join(f'<span class="ev-pill">{e}</span>' for e in u.evidence[:2])}
                </div>
            </div>""", unsafe_allow_html=True)

        if st.button("➕ Add all to Registry"):
            st.session_state.ubids.extend(resolved)
            log_audit("Bulk Resolution", "REGISTRY", f"Added {len(resolved)} UBIDs from resolution run.", "System")
            st.success(f"Registry now contains {len(st.session_state.ubids)} UBIDs.")
            st.rerun()
