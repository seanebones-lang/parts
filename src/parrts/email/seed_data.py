"""Demo inbound customer emails for the auto-answer desk."""

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
