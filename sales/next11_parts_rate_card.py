#!/usr/bin/env python3
"""NextEleven Parts Inventory System — one-page rate card.

Pricing model (locked Aug 2026 v2.0) — best-value rooftop ladder:
  - Pilot $1,500 one-time (credited to first 3 production months)
  - First rooftop $495 / mo
  - Each additional rooftop $195 / mo
  - Growth lock 3–5 rooftops $799 / mo flat (beats stack)
  - Enterprise 6+ custom (~$150–200 blended / roof)

Rebuild:
  python3 ~/Desktop/Parrts-Dist-RAG/sales/next11_parts_rate_card.py
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parent / "NextEleven_Parts_Rate_Card.pdf"

NAVY = colors.HexColor("#0B1F33")
SLATE = colors.HexColor("#334155")
BODY = colors.HexColor("#1E293B")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#CBD5E1")
ZEBRA = colors.HexColor("#F1F5F9")
WHITE = colors.white
MINT = colors.HexColor("#ECFDF5")


def S():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "t", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=15,
            leading=17, textColor=NAVY, alignment=TA_CENTER, spaceAfter=1,
        ),
        "sub": ParagraphStyle(
            "s", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
            leading=10, textColor=SLATE, alignment=TA_CENTER, spaceAfter=1,
        ),
        "meta": ParagraphStyle(
            "m", parent=base["Normal"], fontName="Helvetica", fontSize=7,
            leading=9, textColor=MUTED, alignment=TA_CENTER, spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "h", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=9.5,
            leading=11, textColor=NAVY, spaceBefore=5, spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "b", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
            leading=9.5, textColor=BODY, alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "sm", parent=base["Normal"], fontName="Helvetica", fontSize=7,
            leading=8.5, textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "c", parent=base["Normal"], fontName="Helvetica", fontSize=7.2,
            leading=9, textColor=BODY,
        ),
        "cell_b": ParagraphStyle(
            "cb", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.2,
            leading=9, textColor=BODY,
        ),
        "th": ParagraphStyle(
            "th", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.2,
            leading=9, textColor=WHITE, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "f", parent=base["Normal"], fontName="Helvetica", fontSize=6.8,
            leading=8.5, textColor=MUTED, alignment=TA_CENTER,
        ),
    }


def P(text, style):
    return Paragraph(text, style)


def hdr(labels, st):
    return [P(x, st["th"]) for x in labels]


def cells(vals, st, bold0=True):
    out = []
    for i, v in enumerate(vals):
        out.append(P(v, st["cell_b"] if bold0 and i == 0 else st["cell"]))
    return out


def tstyle(bg, zebra=(), hi=None):
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
    ]
    for r in zebra:
        cmds.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    if hi is not None:
        cmds.append(("BACKGROUND", (0, hi), (-1, hi), MINT))
    return TableStyle(cmds)


def build():
    st = S()
    story = []

    story.append(P("NextEleven Parts Inventory System", st["title"]))
    story.append(P("Commercial Rate Card · Multi-location dealership fixed-ops", st["sub"]))
    story.append(
        P(
            "NextEleven LLC · Mansfield, Texas · Effective August 2026 · v2.0 · USD · Confidential under NDA",
            st["meta"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.1, color=NAVY, spaceAfter=4))
    story.append(
        P(
            "Plain-English multi-rooftop parts desk: counter search, email classify → draft → approve, "
            "inventory / orders / customers, inter-store transfers, human green/yellow/red gate. "
            "Priced by <b>rooftop</b>, not chatbot seats. Built to sit beside what you already run — "
            "not a CDK/Reynolds rip-and-replace.",
            st["body"],
        )
    )

    # Core
    story.append(P("Core pricing", st["h2"]))
    core = [
        hdr(["Package", "Rooftops", "Price", "What it is"], st),
        cells([
            "Pilot", "1–3", "$1,500 one-time",
            "30-day measured engagement on your traffic. <b>Fully credited</b> against first 3 months of production on conversion.",
        ], st),
        cells([
            "First rooftop", "1", "$495 / mo",
            "Full production desk for one store: search, email desk, inventory/orders/customers, transfers, human gate.",
        ], st),
        cells([
            "Each rooftop after", "2+", "$195 / mo each",
            "Same product surface on every additional store. No seat tax.",
        ], st),
        cells([
            "Growth lock", "3–5", "$799 / mo flat",
            "<b>Best value.</b> Beats stacking first+$195 at every size in the band (see examples).",
        ], st),
        cells([
            "Enterprise", "6+", "Custom quote",
            "Named contact + rollout path + VPC/on-prem options. Guide ~$150–$200 blended / rooftop / mo.",
        ], st),
    ]
    t = Table(core, colWidths=[1.15 * inch, 0.7 * inch, 1.15 * inch, 4.15 * inch])
    t.setStyle(tstyle(NAVY, zebra=(1, 3, 5), hi=4))
    story.append(t)
    story.append(Spacer(1, 2))
    story.append(
        P(
            "Simple path: <b>$495 first rooftop + $195 each additional</b>. "
            "Growth locks 3–5 stores at <b>$799 / mo</b> so a 5-store group is not punished vs a 3-store group. "
            "Take whichever is cheaper for you.",
            st["small"],
        )
    )

    # Worked examples
    story.append(P("Worked monthly examples (core only)", st["h2"]))
    ex = [
        hdr(["Rooftops", "1", "2", "3", "4", "5", "6+"], st),
        cells(["Stack path", "$495", "$690", "$885", "$1,080", "$1,275", "Custom"], st, bold0=True),
        cells(["You pay", "$495", "$690", "$799", "$799", "$799", "Quote"], st, bold0=True),
        cells(["Band", "First", "Stack", "Growth", "Growth", "Growth", "Enterprise"], st, bold0=True),
    ]
    te = Table(ex, colWidths=[0.95 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.95 * inch])
    te.setStyle(tstyle(SLATE, zebra=(2,)))
    te.setStyle(TableStyle([
        ("BACKGROUND", (3, 2), (5, 2), MINT),
        ("BACKGROUND", (3, 3), (5, 3), MINT),
    ]))
    story.append(te)
    story.append(Spacer(1, 2))
    story.append(
        P(
            "Growth savings vs stack: 3 rooftops <b>$86/mo</b> · 4 rooftops <b>$281/mo</b> · 5 rooftops <b>$476/mo</b>. "
            "Annual prepay: optional <b>10% off</b> core production.",
            st["small"],
        )
    )

    # Includes
    story.append(P("Included vs not included", st["h2"]))
    left = (
        "<b>Included in every production sub</b><br/>"
        "• NL multi-store search + hybrid retrieval<br/>"
        "• Traffic-light G/Y/R human gate<br/>"
        "• Email desk (classify → draft → approve)<br/>"
        "• DMS core: inventory, orders, customers<br/>"
        "• Inter-store transfers + approval threshold<br/>"
        "• Web UI + API + pilot eval harness<br/>"
        "• Std support (biz-hours email) + product updates<br/>"
        "• Deploy: embedded / server / controlled cloud"
    )
    right = (
        "<b>Not included / sold honestly</b><br/>"
        "• Not a DMS rip-and-replace / CDK parity claim<br/>"
        "• Live OEM only with <b>your</b> feed credentials<br/>"
        "• Stripe / EasyPost live only when keyed<br/>"
        "• Live IMAP/SMTP needs your mailbox creds<br/>"
        "• No “zero-human auto-order” SLA<br/>"
        "• SSO / bi-di DMS / migrations = services<br/>"
        "• Processor fees billed by Stripe/carriers<br/>"
        "• This card is not a software license grant"
    )
    inc = Table(
        [[P(left, st["body"]), P(right, st["body"])]],
        colWidths=[3.55 * inch, 3.55 * inch],
    )
    inc.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (0, 0), 0.4, LINE),
        ("BOX", (1, 0), (1, 0), 0.4, LINE),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFFBEB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
    ]))
    story.append(inc)

    # Add-ons
    story.append(P("Optional add-ons", st["h2"]))
    add = [
        hdr(["Add-on", "Price", "Description"], st),
        cells([
            "Mailbox ops (high volume)", "+$149 / mo",
            "Priority IMAP/SMTP ops support + higher practical volume. Base desk software already included.",
        ], st),
        cells([
            "Commerce module", "+$99 / mo flat",
            "Stripe + EasyPost path. Flat only — no revenue share, no % of parts sales.",
        ], st),
        cells([
            "Dedicated success manager", "+$199 / mo",
            "Named contact, priority queue, monthly readout (often included on Enterprise).",
        ], st),
        cells([
            "Professional services", "$150–$200 / hr or SOW",
            "Feed mapping, SSO, catalog migration, training, integration projects.",
        ], st),
    ]
    ta = Table(add, colWidths=[1.7 * inch, 1.35 * inch, 4.1 * inch])
    ta.setStyle(tstyle(SLATE, zebra=(2, 4)))
    story.append(ta)

    # Pilot credit
    story.append(P("Pilot credit on conversion · $1,500 one-time", st["h2"]))
    story.append(
        P(
            "Applied to production invoices until exhausted <b>or</b> three calendar months of production fees are covered "
            "(whichever first). Examples on core only: first rooftop 3-mo = <b>$1,485</b> (credit covers ~3 mo) · "
            "2 rooftops 3-mo = $2,070 (~2.2 mo) · Growth 3-mo = $2,397 (~1.9 mo).",
            st["body"],
        )
    )

    story.append(P("Commercial terms", st["h2"]))
    story.append(
        P(
            "• <b>Bill:</b> monthly in advance · optional <b>10% off</b> core for annual prepay · prices exclude tax<br/>"
            "• <b>Term:</b> month-to-month after pilot · 30-day written notice to cancel or drop rooftops<br/>"
            "• <b>Expand:</b> add rooftops at $195 / mo or move to Growth/Enterprise — no long-term lock required<br/>"
            "• <b>Quote validity:</b> 30 days · final numbers live on signed order form / SOW<br/>"
            "• <b>Buy path:</b> Discovery → NDA (if needed) → demo on your questions → 30-day pilot SOW → readout → production<br/>"
            "• <b>Contact:</b> nextelevenstudios@gmail.com · mothership-ai.com/parts/",
            st["body"],
        )
    )

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.55, color=LINE, spaceAfter=3))
    story.append(P(
        "NextEleven Parts Inventory System — fail-closed · transparent · best value per rooftop",
        st["footer"],
    ))
    story.append(P(
        "mothership-ai.com · nextelevenstudios@gmail.com · Sean McDonnell · Founder &amp; CTO · NextEleven LLC",
        st["footer"],
    ))
    story.append(P(
        "© 2026 NextEleven LLC. All rights reserved. Proprietary software. Not open source. "
        "Not a financial guarantee. Pricing subject to signed SOW.",
        st["footer"],
    ))

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.32 * inch,
        title="NextEleven Parts Inventory System — Rate Card",
        author="NextEleven LLC",
        subject="Commercial rate card — multi-location dealership parts OS",
        creator="NextEleven LLC",
    )
    doc.build(story)
    print(f"Wrote {OUT}")
    return OUT


if __name__ == "__main__":
    build()
