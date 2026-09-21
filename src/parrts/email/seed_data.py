"""Demo inbound customer emails for the auto-answer desk.

Two verticals:
- DEMO_EMAILS — generic dealership parts (full PARTS UI)
- TRANSMISSION_DEMO_EMAILS — JP Transmission Parts Intelligence only
"""

from __future__ import annotations

DEMO_EMAILS: list[dict] = [
    {
        "message_id": "demo-quote-civic-brakes-001",
        "sender_email": "mike.torres@example.com",
        "sender_name": "Mike Torres",
        "subject": "Quote: brake pads for 2019 Honda Civic",
        "body": (
            "Hi parts team,\n\n"
            "Do you have front brake pads for a 2019 Honda Civic? "
            "Looking for a price and same-day pickup if possible. "
            "My number is 312-555-0142.\n\nThanks,\nMike"
        ),
    },
    {
        "message_id": "demo-order-oil-filter-002",
        "sender_email": "shop@northsideauto.example",
        "sender_name": "Northside Auto",
        "subject": "Please order oil filter Toyota Camry 2020",
        "body": (
            "Need to place an order for oil filter for 2020 Toyota Camry. "
            "Qty: 4. Dealer account Northside. Ship ground if not on shelf."
        ),
    },
    {
        "message_id": "demo-ship-tracking-003",
        "sender_email": "jen@example.com",
        "sender_name": "Jen Lee",
        "subject": "Tracking for my parts shipment?",
        "body": (
            "I ordered rotors last week — can you send the UPS tracking number? "
            "Order should be under Jen Lee."
        ),
    },
    {
        "message_id": "demo-pay-invoice-004",
        "sender_email": "ap@fleetco.example",
        "sender_name": "FleetCo AP",
        "subject": "Invoice copy and payment question",
        "body": (
            "Please resend invoice for last Thursday's parts pickup. "
            "Also confirm you received our card payment ending 4242."
        ),
    },
    {
        "message_id": "demo-complaint-005",
        "sender_email": "angry.customer@example.com",
        "sender_name": "Sam Rivera",
        "subject": "Unacceptable — wrong part twice",
        "body": (
            "This is a formal complaint. You sent the wrong brake rotor twice. "
            "I want a manager and a full refund now. This is unacceptable."
        ),
    },
    {
        "message_id": "demo-general-hours-006",
        "sender_email": "new.customer@example.com",
        "sender_name": "Alex Kim",
        "subject": "Parts counter hours and location",
        "body": "What are your hours and address for counter pickup?",
    },
    {
        "message_id": "demo-quote-f150-rotors-007",
        "sender_email": "dave@example.com",
        "sender_name": "Dave Chen",
        "subject": "Front rotors 2018 Ford F-150 — price check",
        "body": (
            "How much for front brake rotors on a 2018 Ford F-150? "
            "Need availability across your stores."
        ),
    },
    {
        "message_id": "demo-spark-ngk-008",
        "sender_email": "tech@quicklube.example",
        "sender_name": "Quick Lube Tech",
        "subject": "spark plugs NGK Civic availability",
        "body": "Looking for NGK spark plugs for Civic — do you stock them?",
    },
]


# JP Transmission vertical only — hard parts counter language.
# Uses known pilot catalog cues (6L80/6R80/10R80/4L80E, OEM 24264418, etc.).
TRANSMISSION_DEMO_EMAILS: list[dict] = [
    {
        "message_id": "tx-demo-quote-6l80-pump-001",
        "sender_email": "service@lakefronttrans.example",
        "sender_name": "Lake Front Transmissions",
        "subject": "Need price and availability on a 6L80 pump for a 2011 Tahoe",
        "body": (
            "Counter request: price and availability on a 6L80 pump for a 2011 Tahoe. "
            "Customer waiting for same-day if you have stock. Shop account Lake Front."
        ),
    },
    {
        "message_id": "tx-demo-quote-6r80-vb-002",
        "sender_email": "parts@midwestrebuild.example",
        "sender_name": "Midwest Rebuild",
        "subject": "Do you have a rebuilt 6R80 valve body?",
        "body": (
            "Looking for a rebuilt 6R80 valve body. Prefer rebuilt/core if new is out. "
            "Can pick up at counter this afternoon."
        ),
    },
    {
        "message_id": "tx-demo-order-10r80-drum-003",
        "sender_email": "buyer@precisionshift.example",
        "sender_name": "Precision Shift LLC",
        "subject": "Need 10R80 reaction drum ASAP — place order",
        "body": (
            "Please place an order for a 10R80 reaction drum ASAP. "
            "Qty 1. Ship overnight if not on the shelf. PO: PS-4412."
        ),
    },
    {
        "message_id": "tx-demo-oem-24264418-004",
        "sender_email": "tech@harborauto.example",
        "sender_name": "Harbor Auto Tech",
        "subject": "Do you have OEM 24264418?",
        "body": (
            "Do you have OEM 24264418 in stock? "
            "Need confirmation of qty and location before we send the runner."
        ),
    },
    {
        "message_id": "tx-demo-sub-6l90-vs-6l80-005",
        "sender_email": "chris@example.com",
        "sender_name": "Chris Nguyen",
        "subject": "Can I use a 6L90 pump instead of a 6L80?",
        "body": (
            "Customer asking: can I use a 6L90 pump instead of a 6L80? "
            "Please advise — do not ship until we confirm fitment."
        ),
    },
    {
        "message_id": "tx-demo-complaint-wrong-vb-006",
        "sender_email": "ops@alliedtrans.example",
        "sender_name": "Allied Trans Ops",
        "subject": "Customer says wrong valve body was shipped — need replacement",
        "body": (
            "Formal complaint: customer says the wrong valve body was shipped. "
            "Need replacement 6L80 valve body and a call back from a manager today."
        ),
    },
    {
        "message_id": "tx-demo-ship-tracking-007",
        "sender_email": "receiving@gearworks.example",
        "sender_name": "GearWorks Receiving",
        "subject": "Need tracking on my transmission parts order",
        "body": (
            "Need tracking on our transmission parts order from last week "
            "(pump and valve body). Account GearWorks. Please reply with carrier + tracking."
        ),
    },
    {
        "message_id": "tx-demo-inv-4l80e-drum-008",
        "sender_email": "counter@southside.example",
        "sender_name": "Southside Counter",
        "subject": "Do you have a 4L80E input drum on the shelf?",
        "body": (
            "Inventory check: do you have a 4L80E input drum on the shelf? "
            "If yes, how many and which location?"
        ),
    },
    {
        "message_id": "tx-demo-cs-hours-009",
        "sender_email": "newshop@example.com",
        "sender_name": "New Shop Buyer",
        "subject": "Transmission counter hours and will-call",
        "body": (
            "What are your transmission counter hours for will-call pickup? "
            "Also confirm if cores can be returned same day."
        ),
    },
    {
        "message_id": "tx-demo-ambiguous-pump-010",
        "sender_email": "tech2@example.com",
        "sender_name": "Jamie Ortiz",
        "subject": "Need a pump — not sure 6L80 or 6L90",
        "body": (
            "Need a pump for a truck transmission — customer said 6L80 or maybe 6L90. "
            "Not sure which. Can you help sort it out before we order?"
        ),
    },
]


def demo_emails_for_vertical(vertical: str | None = None) -> list[dict]:
    """Return seed rows for the requested demo vertical."""
    v = (vertical or "").strip().lower()
    if v in ("transmission", "jp", "jp_transmission", "tx"):
        return list(TRANSMISSION_DEMO_EMAILS)
    return list(DEMO_EMAILS)
