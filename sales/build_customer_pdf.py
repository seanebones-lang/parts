#!/usr/bin/env python3
"""Generate comprehensive Parts customer sales PDF packet."""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from pypdf import PdfReader

OUT = Path("/Users/nexteleven/Desktop/parts docs/sales/Parts_Customer_Sales_Packet.pdf")
OUT.parent.mkdir(parents=True, exist_ok=True)

NAVY = HexColor("#0B1F33")
TEAL = HexColor("#0D9488")
SLATE = HexColor("#334155")
LIGHT = HexColor("#F1F5F9")
MUTED = HexColor("#64748B")
BORDER = HexColor("#CBD5E1")

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=white,
        leading=34,
        alignment=TA_LEFT,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSub",
        fontName="Helvetica",
        fontSize=13,
        textColor=HexColor("#99F6E4"),
        leading=18,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverMeta",
        fontName="Helvetica",
        fontSize=10,
        textColor=HexColor("#CBD5E1"),
        leading=14,
    )
)
styles.add(
    ParagraphStyle(
        name="H1",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=NAVY,
        spaceBefore=16,
        spaceAfter=8,
        leading=20,
    )
)
styles.add(
    ParagraphStyle(
        name="H2",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=TEAL,
        spaceBefore=12,
        spaceAfter=6,
        leading=15,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=10,
        textColor=SLATE,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletBody",
        fontName="Helvetica",
        fontSize=10,
        textColor=SLATE,
        leading=13,
        leftIndent=12,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="Callout",
        fontName="Helvetica-Oblique",
        fontSize=10,
        textColor=NAVY,
        leading=14,
        leftIndent=8,
        rightIndent=8,
        spaceBefore=6,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8.5,
        textColor=SLATE,
        leading=11,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=white,
        leading=11,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        fontName="Helvetica",
        fontSize=8.5,
        textColor=MUTED,
        leading=11,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="Quote",
        fontName="Helvetica-Oblique",
        fontSize=11,
        textColor=NAVY,
        leading=15,
        leftIndent=16,
        rightIndent=16,
        spaceBefore=8,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="CB",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=HexColor("#5EEAD4"),
    )
)


def p(text, style="Body"):
    return Paragraph(text, styles[style])


def bullet(text):
    return Paragraph(f"• {text}", styles["BulletBody"])


def hdr_cell(text):
    return Paragraph(text, styles["TableHeader"])


def cell(text):
    return Paragraph(text, styles["TableCell"])


def make_table(headers, rows, col_widths):
    data = [[hdr_cell(h) for h in headers]]
    for row in rows:
        data.append([cell(c) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("BACKGROUND", (0, 1), (-1, -1), white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def footer_canvas(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(0.75 * inch, 0.6 * inch, letter[0] - 0.75 * inch, 0.6 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            0.75 * inch,
            0.4 * inch,
            "NextEleven LLC · Parts · Confidential Customer Packet · (c) 2026",
        )
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = []

cover_banner = Table(
    [
        [Paragraph("NEXTELEVEN LLC", styles["CB"])],
        [Paragraph("PARTS", styles["CoverTitle"])],
        [
            Paragraph(
                "Multi-Location Dealership Parts Intelligence",
                styles["CoverSub"],
            )
        ],
        [
            Paragraph(
                "Customer Sales Packet<br/>Proprietary Product Information<br/>July 2026",
                styles["CoverMeta"],
            )
        ],
    ],
    colWidths=[7.0 * inch],
)
cover_banner.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("LEFTPADDING", (0, 0), (-1, -1), 28),
            ("RIGHTPADDING", (0, 0), (-1, -1), 28),
            ("TOPPADDING", (0, 0), (-1, 0), 36),
            ("TOPPADDING", (0, 1), (-1, 1), 18),
            ("TOPPADDING", (0, 2), (-1, -1), 6),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 36),
            ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )
)
story.append(cover_banner)
story.append(Spacer(1, 22))

story.append(
    p(
        "<b>One sentence:</b> Parts finds the right part across every rooftop in your group — "
        "in plain English — and tells you green, yellow, or red whether a human should touch the answer.",
        "Callout",
    )
)
story.append(
    p(
        "This packet is for dealership groups evaluating Parts for multi-store availability, "
        "counter productivity, and trustworthy AI at the parts desk. It is informational and does "
        "not grant a software license. All software remains proprietary to NextEleven LLC."
    )
)

story.append(
    make_table(
        ["Fact", "Detail"],
        [
            ["Product", "Parts — Multi-Location Dealership Parts AI"],
            ["Company", "NextEleven LLC (Frisco, Texas)"],
            ["Engineering reference", "https://github.com/seanebones-lang/parts"],
            ["Core package", "parrts v0.4.2 (hybrid RAG)"],
            ["License", "Proprietary — not open source"],
            ["Last measured health", "2026-07-31 · 59 tests passed · eval 12/12 hit@5"],
            ["Pilot shape", "30 days · 1–3 rooftops · written success metrics"],
        ],
        [1.7 * inch, 5.3 * inch],
    )
)
story.append(Spacer(1, 14))
story.append(p("<b>Contents</b>", "H2"))
for i, title in enumerate(
    [
        "The Problem We Solve",
        "Solution Overview",
        "How It Works (Architecture)",
        "Key Capabilities",
        "What Is Real vs Optional",
        "Traffic-Light Trust Model",
        "Demo Scenario and Proof Points",
        "Ideal Fit and Disqualifiers",
        "30-Day Pilot Blueprint",
        "ROI Discussion Framework",
        "Security, Data and Licensing",
        "Implementation and Requirements",
        "FAQ",
        "Commercial Next Steps",
        "Appendix: Technical Health Snapshot",
    ],
    1,
):
    story.append(bullet(f"<b>{i}.</b>  {title}"))

story.append(PageBreak())

# 1
story.append(p("1. The Problem We Solve", "H1"))
story.append(
    p(
        "Across multi-rooftop dealer groups, a simple question — <i>“Do you have brake pads for a "
        "2019 Honda Civic?”</i> — still burns minutes of advisor and counter time. Staff bounce "
        "between DMS screens, phone trees, and tribal knowledge. Wrong “yes” answers create "
        "comebacks, goodwill costs, and CSI risk. Wrong “no” answers lose work to competitors."
    )
)
story.append(
    p(
        "Generic chatbots make this worse when they invent inventory. Dealers do not need more "
        "confident paragraphs. They need <b>defensible availability answers</b> with a clear human gate."
    )
)
story.append(p("Typical pain points", "H2"))
for t in [
    "Cross-store blindness — nobody sees group inventory in one plain-English step",
    "Advisor hold time — every availability check steals fixed-ops capacity",
    "Inconsistent process — each rooftop answers differently",
    "AI distrust — prior chatbot pilots hallucinated stock",
    "Integration fear — teams reject rip-and-replace DMS projects",
]:
    story.append(bullet(t))

story.append(PageBreak())

# 2
story.append(p("2. Solution Overview", "H1"))
story.append(
    p(
        "<b>Parts</b> is multi-location dealership parts intelligence from NextEleven LLC. "
        "Users ask in natural language. The system retrieves and ranks parts across locations, "
        "applies a green / yellow / red traffic-light policy, and exposes results via CLI, API, and web UI."
    )
)
story.append(
    p(
        "Parts is designed to sit <b>beside</b> your DMS — accelerating availability intelligence — "
        "not to rip out your system of record on day one."
    )
)
story.append(p("Value pillars", "H2"))
story.append(
    make_table(
        ["Pillar", "What the customer gets"],
        [
            ["Find", "Plain-English lookup that understands vehicle + part language"],
            ["Trust", "Traffic-light policy so the floor knows when AI is enough"],
            ["Multi-store", "Ranked results across rooftops; expand sibling locations by SKU"],
            ["Integrate later", "FastAPI enterprise surface when you are ready for DMS/SSO"],
            ["Measure", "Golden-query eval harness for pilot proof — not vibes"],
        ],
        [1.4 * inch, 5.6 * inch],
    )
)
story.append(Spacer(1, 12))
story.append(p("Positioning statement", "H2"))
story.append(
    p(
        "“Parts is retrieval-first dealership software: plain-English multi-store availability "
        "with a human brake pedal — not chatbot theater and not a DMS replacement.”",
        "Quote",
    )
)

story.append(PageBreak())

# 3
story.append(p("3. How It Works (Architecture)", "H1"))
story.append(
    p(
        "Parts is a dual-stack platform. The <b>parrts core</b> is the source of truth for retrieval. "
        "The enterprise backend and frontend sit on top for APIs, agents, and UI."
    )
)
story.append(
    make_table(
        ["Layer", "Role", "Customer meaning"],
        [
            [
                "parrts core",
                "Hybrid dense + keyword ranking, traffic-light policy, offline-capable",
                "The brain for “do you have it?”",
            ],
            [
                "Enterprise API",
                "FastAPI, /api/v1 modules, health, metrics",
                "Integration surface for IT",
            ],
            [
                "LangGraph agents",
                "Parts, CS, inventory, pricing, payment, shipping, supplier, follow-up",
                "Workflow orchestration; soft-fail offline",
            ],
            ["Frontend", "Next.js parts search + traffic badge", "Counter / pilot UI"],
            [
                "Ops",
                "Docker profiles, CI, eval, pgvector seed",
                "Deploy path when ready",
            ],
        ],
        [1.35 * inch, 2.85 * inch, 2.8 * inch],
    )
)
story.append(Spacer(1, 10))
story.append(
    p(
        "Default embedding path for demos is offline-safe (no cloud model required). "
        "Optional cloud LLMs can help phrase answers but are not required for stock retrieval. "
        "Optional Postgres + pgvector supports larger centralized catalogs when available."
    )
)

story.append(PageBreak())

# 4
story.append(p("4. Key Capabilities", "H1"))
caps = [
    ("Natural language parts lookup", "Ask the way humans ask — vehicle, part type, brand cues."),
    (
        "Hybrid retrieval",
        "Combines meaning-based and keyword-style ranking (RRF fusion) for parts language.",
    ),
    ("Multi-location ranking", "See which rooftop can fulfill; filter by location when needed."),
    ("Parent / sibling expand", "Expand a hit across stores carrying the same base SKU."),
    ("Traffic-light policy", "Green / yellow / red with confidence and recommended actions."),
    ("CLI for power users", "parrts ingest / query / status — scriptable and demo-friendly."),
    ("HTTP API", "/query, /health, /metrics plus enterprise /api/v1 route groups."),
    ("Web UI", "Parts page with live API path and mock fallback for resilient demos."),
    (
        "Agent orchestration",
        "Email to classify to parts/service/inventory/pricing paths with human flags.",
    ),
    ("Evaluation harness", "Fixed golden queries; hit@k, MRR, recall, latency reporting."),
    (
        "Auth modes",
        "AUTH_MODE=demo for controlled demos; production expects JWT on wired writes.",
    ),
    ("pgvector path", "Opt-in production vector store with seed script when Postgres is up."),
]
for title, body in caps:
    story.append(p(f"<b>{title}.</b> {body}"))

story.append(PageBreak())

# 5
story.append(p("5. What Is Real vs Optional (Honesty Table)", "H1"))
story.append(
    p(
        "We win long dealer relationships by not overselling. Use this table in every serious conversation."
    )
)
story.append(
    make_table(
        ["Capability", "Status today", "What you need"],
        [
            ["Hybrid RAG lookup + traffic-light", "Measured / shipping", "Install core package"],
            ["Multi-location seed catalog demo", "Ready", "Laptop or server"],
            ["Automated tests + eval harness", "Measured", "None"],
            ["FastAPI boot + 15 API modules load", "Measured", "Python deps"],
            ["Next.js UI type-check clean", "Measured", "Node for UI"],
            ["Cloud LLM answer wording", "Optional", "Anthropic/OpenAI keys"],
            ["Live Stripe payments", "Mock until keyed", "Stripe account + scope"],
            ["Live carrier labels (EasyPost)", "Mock until keyed", "EasyPost + scope"],
            ["Live pgvector at scale", "Code-ready", "Docker + Postgres"],
            ["Full DMS bi-directional sync", "Integration SOW", "Discovery + project"],
            ["Unattended full autonomy / no humans", "Not offered as SLA", "—"],
            ["Open-source / free redistribution", "Not available", "Proprietary license only"],
        ],
        [2.4 * inch, 1.8 * inch, 2.8 * inch],
    )
)
story.append(Spacer(1, 10))
story.append(
    p(
        "Claims of full 13-agent production SLA, guaranteed ROI dollars, or always-live supplier "
        "scraping are aspirational unless scoped in a signed SOW.",
        "Small",
    )
)

story.append(PageBreak())

# 6
story.append(p("6. Traffic-Light Trust Model", "H1"))
story.append(
    p("Traffic-light is a product feature for fixed-ops culture — not a slide gimmick.")
)
story.append(
    make_table(
        ["Signal", "Typical meaning", "Recommended floor behavior"],
        [
            [
                "GREEN",
                "Strong match and healthy stock posture",
                "Safe to answer quickly; still verify process rules",
            ],
            [
                "YELLOW",
                "Mid confidence and/or thin stock",
                "Human reviews before promising customer",
            ],
            [
                "RED",
                "Weak match, zero stock, or no hits",
                "Do not auto-promise; escalate / source",
            ],
        ],
        [1.1 * inch, 2.6 * inch, 3.3 * inch],
    )
)
story.append(Spacer(1, 10))
story.append(
    p(
        "Thresholds can be tuned in a pilot against your golden queries and risk tolerance. "
        "The goal is not zero human involvement — it is putting humans on the hard cases, "
        "not every easy availability check."
    )
)

story.append(PageBreak())

# 7
story.append(p("7. Demo Scenario and Proof Points", "H1"))
story.append(p("Example demo query", "H2"))
story.append(p("<font face='Courier'>parrts query \"brake pads for 2019 Honda Civic\" --no-llm</font>"))
story.append(
    p(
        "On the standard seed catalog (health check 2026-07-31): traffic-light <b>green</b>, "
        "top SKU example <b>BP-HC19-L4</b>, multi-location hits available; "
        "<font face='Courier'>--expand-parent</font> shows sibling rooftops for the same base part."
    )
)
story.append(p("Measured engineering proof (as of 2026-07-31)", "H2"))
story.append(
    make_table(
        ["Check", "Result"],
        [
            ["Automated tests", "59 passed, 2 skipped (optional ST + live DB by design)"],
            ["Retrieval eval (default set)", "hit@5 = 12/12 (100%), MRR = 1.0, recall@5 = 1.0"],
            ["Mean eval latency (demo hardware)", "About 0.7 ms per query on core path"],
            ["API v1 modules loaded", "15 / 15 (0 failed)"],
            ["Core endpoints without Postgres", "/, /health, /query, /metrics available"],
            ["Frontend TypeScript", "tsc --noEmit clean"],
            ["Compose config", "Valid profiles: core, api, full, pgvector, obs"],
        ],
        [2.6 * inch, 4.4 * inch],
    )
)
story.append(Spacer(1, 8))
story.append(
    p(
        "Your pilot replaces the seed catalog with your data and rebuilds a golden query set you own.",
        "Small",
    )
)

story.append(PageBreak())

# 8
story.append(p("8. Ideal Fit and Disqualifiers", "H1"))
story.append(p("Strong fit", "H2"))
for t in [
    "Multi-rooftop groups (roughly 3–15 stores) with shared or loosely shared parts inventory",
    "Parts managers and fixed-ops leaders under pressure on speed-to-answer and CSI",
    "Groups burned by chatbots that invented stock",
    "Willingness to run a measured 30-day pilot with a golden query list",
]:
    story.append(bullet(t))
story.append(p("Usually a weak fit (for now)", "H2"))
for t in [
    "Single-store shops that only need basic e-commerce catalog search",
    "Buyers demanding fully autonomous ordering with zero humans on day one",
    "Prospects unwilling to measure quality or name a business owner",
    "Requests for open-source redistribution without agreement",
]:
    story.append(bullet(t))

story.append(PageBreak())

# 9
story.append(p("9. 30-Day Pilot Blueprint", "H1"))
story.append(
    make_table(
        ["Week", "Activities", "Exit artifact"],
        [
            ["0", "Kickoff, NDA if needed, rooftop list, owner names", "Charter + success metrics"],
            [
                "1",
                "Install core; index seed or sample export; draft golden queries",
                "Baseline hit-rate",
            ],
            ["2", "Shadow mode with counter/advisors; capture overrides", "Usage notes"],
            [
                "3",
                "Tune traffic-light; optional LLM wording; train cohort",
                "Updated thresholds",
            ],
            [
                "4",
                "Readout: quality, latency, overrides, go/no-go",
                "Decision + production plan",
            ],
        ],
        [0.7 * inch, 3.6 * inch, 2.7 * inch],
    )
)
story.append(Spacer(1, 10))
story.append(p("Suggested success criteria (negotiate per group)", "H2"))
for t in [
    "hit@5 at least 90% on the agreed golden query set",
    "Median latency under 2 seconds on agreed hardware for interactive use",
    "Yellow/red rate understood and staffable",
    "Counter cohort would use daily (simple survey)",
]:
    story.append(bullet(t))

story.append(PageBreak())

# 10
story.append(p("10. ROI Discussion Framework", "H1"))
story.append(
    p(
        "The following is a <b>discussion framework</b>, not a guarantee. "
        "Replace every input with dealer actuals."
    )
)
story.append(p("Status-quo cost drivers", "H2"))
story.append(
    make_table(
        ["Driver", "Example input", "Why it matters"],
        [
            ["Daily “do you have” events (group)", "200", "Volume of friction"],
            ["Minutes per event today", "4", "Labor sink"],
            ["Loaded labor $/hour", "$35", "Converts time to money"],
            ["Wrong-promise / comeback rate", "3%", "Hidden rework + CSI"],
            ["Cost per comeback", "$75", "Goodwill + rework"],
        ],
        [2.5 * inch, 1.5 * inch, 3.0 * inch],
    )
)
story.append(Spacer(1, 8))
story.append(
    p(
        "Illustrative only: 200 events times 4 minutes is about 13.3 hours/day — on the order of "
        "six figures/year in lookup labor before comeback costs. A conservative pilot that improves "
        "a fraction of events by a couple of minutes, plus a small drop in wrong promises, is often "
        "enough to justify a pilot fee — <b>if measured on your data</b>."
    )
)
story.append(
    p(
        "We sell the pilot on measurement: hit-rate, latency, override rate, and a before/after "
        "time sample — not on a magical ROI spreadsheet."
    )
)

story.append(PageBreak())

# 11
story.append(p("11. Security, Data and Licensing", "H1"))
for t in [
    "<b>Proprietary IP.</b> Parts is not open source. Copyright and trade-secret protections apply.",
    "<b>No implied license</b> from viewing this packet or a repository reference URL.",
    "<b>Auth modes:</b> demo for controlled demos; production mode expects JWT on wired mutating routes.",
    "<b>Network:</b> do not expose admin APIs publicly without authentication and controls.",
    "<b>Processors:</b> Stripe / EasyPost / LLM providers only when you supply keys and approve scope.",
    "<b>Customer data:</b> under NDA/MSA; no training unrelated public models on your catalog without agreement.",
    "<b>Deployment:</b> laptop pilot, on-prem/VPC, or controlled cloud — scoped in enterprise SOW.",
]:
    story.append(bullet(t))

story.append(PageBreak())

# 12
story.append(p("12. Implementation and Requirements", "H1"))
story.append(p("Technical prerequisites (pilot)", "H2"))
for t in [
    "Python 3.11+ environment (venv recommended)",
    "Optional: Node 20+ for web UI",
    "Optional: Docker Desktop for Postgres/pgvector full stack",
    "Named business owner (parts or fixed ops) + technical contact",
    "Location list and naming conventions",
    "Top 20–50 real availability questions (golden set)",
    "Sample catalog extract or agreement to start on demo catalog then swap",
]:
    story.append(bullet(t))
story.append(p("Quick start (technical evaluation)", "H2"))
story.append(
    p(
        "<font face='Courier' size='8'>"
        "git clone https://github.com/seanebones-lang/parts.git<br/>"
        "cd parts<br/>"
        "python3 -m venv .venv<br/>"
        "source .venv/bin/activate<br/>"
        "pip install -e \".[dev]\"<br/>"
        "python -m parrts ingest --force<br/>"
        "python -m parrts query \"brake pads for 2019 Honda Civic\" --no-llm<br/>"
        "pytest -q<br/>"
        "python scripts/eval_retrieval.py"
        "</font>"
    )
)

story.append(PageBreak())

# 13
story.append(p("13. FAQ", "H1"))
faqs = [
    (
        "Does this replace our DMS?",
        "No. It accelerates availability intelligence and can integrate over time via API.",
    ),
    (
        "Will it invent stock levels?",
        "Core design is retrieval-first with traffic-light gating. Weak results surface as yellow/red for humans.",
    ),
    (
        "Do we need cloud AI keys?",
        "Not for core lookup demos. Keys unlock optional answer wording and live processors.",
    ),
    (
        "How fast to first value?",
        "Same-day demo on sample catalog; pilot value measured in weeks.",
    ),
    (
        "Can it run in our VPC?",
        "Yes — architecture supports controlled deployment; scope in enterprise SOW.",
    ),
    (
        "Is the GitHub repo free to use?",
        "No. Proprietary. Access and use require NextEleven authorization.",
    ),
    (
        "What about payments and shipping?",
        "Mocked unless you connect Stripe/EasyPost and contract that scope.",
    ),
    (
        "Who owns the golden queries?",
        "You do. We help facilitate; parts leadership should own the list.",
    ),
]
for q, a in faqs:
    story.append(p(f"<b>Q: {q}</b>"))
    story.append(p(f"A: {a}"))

story.append(PageBreak())

# 14
story.append(p("14. Commercial Next Steps", "H1"))
story.append(p("Recommended path", "H2"))
for i, t in enumerate(
    [
        "Discovery call — rooftops, DMS, pain, owners (30 minutes)",
        "NDA if required by your legal team",
        "Live demo on your top questions (or seed catalog if export pending)",
        "Pilot SOW — 30 days, 1–3 rooftops, written metrics",
        "Readout and production decision (group license + optional integration SOW)",
    ],
    1,
):
    story.append(bullet(f"<b>Step {i}.</b> {t}"))

story.append(Spacer(1, 10))
story.append(p("Commercial framing (ranges set in formal quote)", "H2"))
story.append(
    make_table(
        ["Motion", "What it covers"],
        [
            ["Pilot", "Time-boxed fee, success criteria, limited rooftops"],
            ["Group subscription", "Annual license by rooftop band + support"],
            ["Enterprise integration", "DMS/SSO/VPC, SLA, training, custom feeds"],
        ],
        [1.8 * inch, 5.2 * inch],
    )
)
story.append(Spacer(1, 16))
story.append(
    p(
        "Contact your NextEleven LLC representative to schedule discovery.<br/>"
        "Engineering reference: https://github.com/seanebones-lang/parts<br/>"
        "Company: NextEleven LLC · Frisco, Texas · Proprietary and confidential"
    )
)

story.append(PageBreak())

# Appendix
story.append(p("Appendix A — Technical Health Snapshot (2026-07-31)", "H1"))
story.append(
    p(
        "Internal automated health check summary for sales engineering alignment. "
        "Not a third-party audit."
    )
)
story.append(
    make_table(
        ["Area", "Status", "Notes"],
        [
            ["Core hybrid RAG", "PASS", "Offline retrieval + traffic-light"],
            ["Pytest", "PASS", "59 passed / 2 skipped"],
            ["Backend /api/v1 boot", "PASS", "15/15 routers"],
            ["Frontend tsc", "PASS", "exit 0"],
            ["Retrieval eval", "PASS", "12/12 hit@5, MRR 1.0"],
            [
                "Docker live stack",
                "ENV BLOCKED",
                "Daemon off at check time; compose YAML valid",
            ],
            ["pgvector seed", "GRACEFUL SKIP", "Exit 0 when DB unreachable"],
            ["Live LLM/Stripe/EasyPost", "N/A", "Key-gated by design"],
            ["Ruff style", "WARN", "About 24 non-blocking style findings"],
        ],
        [1.8 * inch, 1.4 * inch, 3.8 * inch],
    )
)

story.append(Spacer(1, 12))
story.append(p("Appendix B — Sample Interaction (Illustrative)", "H1"))
story.append(p("<b>Input:</b> brake pads for 2019 Honda Civic"))
story.append(
    p(
        "<b>Output (conceptual):</b> ranked SKUs with location, stock, scores; "
        "traffic-light color; optional expand to other stores; optional natural-language "
        "summary if LLM keys present."
    )
)

story.append(Spacer(1, 12))
story.append(p("Appendix C — Document Control", "H1"))
story.append(
    make_table(
        ["Field", "Value"],
        [
            ["Document", "Parts Customer Sales Packet (PDF)"],
            ["Version", "1.0"],
            ["Date", "2026-07-31"],
            ["Audience", "Prospective dealer-group buyers and evaluators"],
            ["Owner", "NextEleven LLC"],
            ["Classification", "Confidential — customer evaluation"],
        ],
        [1.6 * inch, 5.4 * inch],
    )
)

story.append(Spacer(1, 16))
story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceBefore=8, spaceAfter=8))
story.append(
    p(
        "(c) 2026 NextEleven LLC. All rights reserved. This document does not grant any license "
        "to use, copy, modify, or distribute the Parts software or related intellectual property. "
        "Figures and pilot outcomes depend on customer data quality, configuration, and adoption. "
        "ROI examples are illustrative only.",
        "Small",
    )
)

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=letter,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.7 * inch,
    bottomMargin=0.85 * inch,
    title="Parts — Customer Sales Packet | NextEleven LLC",
    author="NextEleven LLC",
    subject="Multi-Location Dealership Parts Intelligence — Customer Sales Information",
)
doc.build(story, onFirstPage=footer_canvas, onLaterPages=footer_canvas)

r = PdfReader(str(OUT))
print(f"Wrote {OUT}")
print(f"Pages: {len(r.pages)}")
print(f"Size bytes: {OUT.stat().st_size}")
print("Page1 has PARTS:", "PARTS" in (r.pages[0].extract_text() or ""))
print("Page2 has Problem:", "Problem" in (r.pages[1].extract_text() or ""))
