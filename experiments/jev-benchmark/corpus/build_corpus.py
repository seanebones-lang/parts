"""Build the JEV benchmark gold corpus (independent ground truth).

Gold labels are assigned BY HAND in this file. They are never derived from
``parrts.email.classify.classify_email`` output (decision #12) — the corpus is
the ground truth the three approaches compete against.

Sources (decision #3/#4):
  - DEMO_EMAILS      -> source="seed_data"
  - test fixtures    -> source="test_fixture"   (recreated here; test file not imported)
  - synthetic        -> source="synthetic"      (hand-authored, deliberately hard)

Writes experiments/jev-benchmark/corpus/gold_labels.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path

from parrts.email.seed_data import DEMO_EMAILS  # stdlib-only import; read-only

HERE = Path(__file__).resolve().parent


def _demo_rows() -> list[dict]:
    """DEMO_EMAILS -> corpus rows, gold labels hand-assigned."""
    rows = []
    for e in DEMO_EMAILS:
        d = e["body"].lower()
        # assign gold label + needs_human independently of the classifier
        if "complaint" in d and "refund" in d:
            label, nh = "general_question", True   # escalation, folded to general + flag
        elif "tracking" in d or "shipment" in e["subject"].lower():
            label, nh = "order_status", False
        elif "invoice" in d or "payment" in d:
            label, nh = "general_question", False  # billing gap -> general + flag
        elif "hours" in d or "address" in d:
            label, nh = "general_question", False
        else:
            # price/parts intent from seed data
            label, nh = "price_request", False
        rows.append(
            {
                "subject": e["subject"],
                "body": e["body"],
                "sender_email": e["sender_email"],
                "label": label,
                "needs_human": nh,
                "source": "seed_data",
                "message_id": e["message_id"],
            }
        )
    return rows


def _fixture_rows() -> list[dict]:
    """Reproduce the inline fixtures from tests/test_email_desk.py."""
    return [
        {
            "subject": "Quote brake pads 2019 Honda Civic",
            "body": "How much for front brake pads?",
            "sender_email": "a@b.com",
            "label": "price_request",
            "needs_human": False,
            "source": "test_fixture",
            "message_id": "fix-quote-pads",
        },
        {
            "subject": "Unacceptable wrong part",
            "body": "This is a formal complaint I want a refund now manager",
            "sender_email": "x@y.com",
            "label": "general_question",  # complaint -> general + escalation flag
            "needs_human": True,
            "source": "test_fixture",
            "message_id": "fix-complaint",
        },
        {
            "subject": "oil filter Toyota",
            "body": "Need oil filter for 2020 Toyota Camry price please",
            "sender_email": "z@example.com",
            "label": "price_request",
            "needs_human": False,
            "source": "test_fixture",
            "message_id": "fix-oil-price",
        },
    ]


def _synthetic_rows() -> list[dict]:
    """Hand-authored examples covering all 7 classes + deliberate edge cases."""
    S = []  # (label, needs_human, subject, body)

    # --- parts_availability ---
    S += [
        ("parts_availability", False, "Do you stock these?", "Do you have this and how much is it? front brake pads 2019 civic"),
        ("parts_availability", False, "brake pads 2019 Honda Civic avail", "Looking for rear brake pads for a 2019 Honda Civic. Do you have any in stock?"),
        ("parts_availability", False, "oil filter 2020 Camry", "Do you carry oil filters for a 2020 Toyota Camry?"),
        ("parts_availability", True, "rotor availability F150", "Got front rotors for a 2018 F-150? need across all your stores pls"),
        ("parts_availability", False, "spark plug stock", "Spark plugs for Civic — in stock?"),
        ("parts_availability", False, "cabin filter RAV4", "Is the cabin air filter for 2021 RAV4 available?"),
        ("parts_availability", True, "vague part stock", "do u have the filter i asked about yest"),
        ("parts_availability", False, "alternator 2019 accord", "Do you carry an alternator for the 2019 Honda Accord?"),
        ("parts_availability", False, "typos what stock", "wud up need brke pads 2017 honda civic n stock pls"),
        ("parts_availability", False, "very short have?", "you have this?"),
        ("parts_availability", False, "brake rotor stock f150", "Do you have front rotors for a 2018 Ford F-150 on the shelf?"),
        ("parts_availability", False, "water pump avail", "In stock? Water pump for a 2016 Chevy Silverado."),
        ("parts_availability", False, "timing belt kit", "Got a timing belt kit for the 2019 Accord?"),
        ("parts_availability", True, "incomplete vehicle avail", "do you stock the filter for it, its the v6 model"),
        ("parts_availability", False, "wiper blades stock", "Wiper blades for my 2021 RAV4, do you have them?"),
        ("parts_availability", False, "clutch avail", "Do you carry a clutch kit for the civic si?"),
        ("parts_availability", True, "multi part avail", "Looking for pads and rotors and fluid for a 2019 civic — all in stock?"),
        ("parts_availability", False, "short have pads", "pads?"),
        ("parts_availability", False, "hcavily typo", "do u hav frnt rottors 2018 f150 n stck"),
        ("parts_availability", False, "fuel filter avail", "Fuel filter for a 2020 Camry gas, you got one?"),
        ("parts_availability", False, "thermostat avail", "Is the thermostat for the 2019 accord available?"),
        ("parts_availability", True, "vague what part avail", "need the part, do you have it in dallas?"),
    ]

    # --- price_request ---
    S += [
        ("price_request", False, "how much pads", "How much for front brake pads on a 2019 Honda Civic?"),
        ("price_request", False, "price rotors F150", "Price for front brake rotors, 2018 Ford F-150?"),
        ("price_request", True, "price + fitment same msg", "Does this pad fit the 2019 Civic and how much?"),
        ("price_request", False, "quote oil filter", "Can I get a price on the oil filter for 2020 Camry?"),
        ("price_request", False, "ngk civic price", "NGK spark plugs for the Civic, what's the going price?"),
        ("price_request", False, "alternator cost", "Cost of an alternator for the 2019 Accord please"),
        ("price_request", False, "typo price plt", "how mutch for the rottors for my truck"),
        ("price_request", False, "msrp", "MSRP on rear brake pads 2021 RAV4?"),
        ("price_request", True, "vague price", "how much??"),
        ("price_request", False, "price ack", "could u send a quote for those parts we talked about"),
        ("price_request", False, "brake pad quote civic", "quote me front pads 2019 civic please"),
        ("price_request", False, "rotor pricing F150", "what do front rotors cost for the 2018 F-150"),
        ("price_request", False, "oil filter pricing camry", "price on the camry oil filter, 2020"),
        ("price_request", False, "spark plug price civic", "spark plug price civic ngk"),
        ("price_request", True, "typo price + fit", "prce for the rottor that fets 2019 civc"),
        ("price_request", False, "short price?", "how much?"),
        ("price_request", False, "f150 rotor quote all", "need a quote on front rear rotors for my f150"),
        ("price_request", False, "alternator invoice", "how much for alternator invoice me"),
        ("price_request", False, "bulk price pads", "price for 10 sets of brake pads civic 2019"),
        ("price_request", False, "freight quote rotor", "whats the price plus freight on rotors"),
        ("price_request", True, "vague what cost", "what would that cost"),
    ]

    # --- compatibility_fitment ---
    S += [
        ("compatibility_fitment", False, "will it fit", "Will these fit my 2019 Honda Civic?"),
        ("compatibility_fitment", False, "fit 2020 camry", "Does the 2020 oil filter also fit the 2021 Camry?"),
        ("compatibility_fitment", False, "interchange", "Is part #1123 compatible with the 2018 F-150?"),
        ("compatibility_fitment", True, "fit + vague part", "will this work on my car"),
        ("compatibility_fitment", False, "cross reference", "Can you cross-reference this SKU against OEM 04465-33290?"),
        ("compatibility_fitment", False, "fit alternate model", "Rotor for 2019 Accord — fits 2020 too?"),
        ("compatibility_fitment", False, "fitment no year", "fitment for the accord brake pads, forgot the year"),
        ("compatibility_fitment", True, "vague fit fit", "compatible?"),
        ("compatibility_fitment", False, "f150 rotor fit", "do front rotors for the f150 fit the f250 too"),
        ("compatibility_fitment", False, "civic pad fit si", "will civic pads fit the si trim brakes"),
        ("compatibility_fitment", False, "oem cross", "is this the same as oem part 45251-SDA-A05"),
        ("compatibility_fitment", True, "incomplete fit", "would the one for the 2.0 engine fit the 1.5, same car"),
        ("compatibility_fitment", False, "filter fitment", "does the 2019 filter also fit the 2021 model"),
        ("compatibility_fitment", False, "alternator fit mod", "will the camry alternator fit the lexus es"),
        ("compatibility_fitment", False, "pads fit 6cyl", "will these pads work on the v6 accord or just the 4 cyl"),
        ("compatibility_fitment", True, "typo fit", "wll ths fit my car 2019 civc"),
    ]

    # --- order_status ---
    S += [
        ("order_status", False, "where's my order", "Where is my order? It was supposed to ship last week."),
        ("order_status", False, "tracking number", "Can you send me the tracking number for my order please?"),
        ("order_status", True, "vague existing order", "just checking on my order, any update?"),
        ("order_status", False, "order 2001 status", "Status on order 2001 — did it go out yet?"),
        ("order_status", False, "did it ship", "Did my brake pads ship?"),
        ("order_status", True, "typo order stat", "woot bout my order wher it at"),
        ("order_status", False, "short status", "my order?"),
        ("order_status", False, "delivery eta", "What's the delivery ETA for my rotors?"),
        ("order_status", False, "tracking 2002", "tracking number for order 2002 please"),
        ("order_status", True, "vague of order", "any word on it yet"),
        ("order_status", False, "cancelled?", "has my order shipped or cancelled"),
        ("order_status", True, "typo order wher", "wher is mu order"),
        ("order_status", False, "update doors", "any update on the doors i ordered two weeks ago?"),
        ("order_status", False, "short eta", "eta?"),
    ]

    # --- sell_part ---
    S += [
        ("sell_part", False, "selling used rotors", "Hi, I have a set of used rotors I'd like to sell to you."),
        ("sell_part", False, "trade in parts", "Do you buy used parts or take trade-ins?"),
        ("sell_part", False, "sell alternator", "Want to sell my old alternator, are you buying?"),
        ("sell_part", False, "sell unused pads", "I have some unused brake pads to offload, interested?"),
        ("sell_part", True, "vague sell part", "can you take parts off my hands"),
        ("sell_part", False, "sell catalytic", "Do you purchase used catalytic converters?"),
        ("sell_part", False, "sell wheels", "I have a set of take-off factory wheels to sell."),
        ("sell_part", False, "trade in alternator", "would you take my old alternator as trade-in"),
        ("sell_part", False, "sell starter", "selling a used starter, are you in the market?"),
        ("sell_part", True, "typo sell", "seling sum parts u buy"),
        ("sell_part", False, "sell brake pads used", "got some used brake pads, want them for cheap?"),
        ("sell_part", False, "sell turbos", "do you buy turbos, i have two"),
        ("sell_part", True, "vague offload", "taking offers on some parts i have"),
        ("sell_part", False, "sell calipers", "looking to sell a set of calipers, interested?"),
    ]

    # --- general_question ---
    S += [
        ("general_question", False, "store hours", "What are your store hours?"),
        ("general_question", False, "locations", "Which of your locations has the parts counter?"),
        ("general_question", False, "return policy", "What's your return policy on parts?"),
        ("general_question", False, "complaint + parts", "This rotor is wrong, and by the way do you have the correct one and refund me?"),
        ("general_question", True, "escalate to manager", "I want to speak to a manager, this has gone on too long."),
        ("general_question", False, "incomplete vehicle", "do you have parts for my car, it's a 2016"),
        ("general_question", False, "typo short hi", "hii do u do labor here"),
        ("general_question", False, "directions", "how do i get to the counter, directions?"),
        ("general_question", False, "contact", "is there a phone number to call for parts?"),
        ("general_question", False, "methods", "do you take apple pay?"),
        ("general_question", True, "escalate billing", "your billing is a mess, get me a supervisor"),
        ("general_question", False, "open questions", "are you open saturdays for pickup?"),
        ("general_question", False, "shipping policy", "where do you ship parts and how long does ground take?"),
    ]

    # --- spam_or_irrelevant ---
    S += [
        ("spam_or_irrelevant", False, "congrats prize", "Congratulations! You've been selected to receive a $500 gift card, click here to claim."),
        ("spam_or_irrelevant", False, "extended warranty scam", "Act now about your vehicle's warranty, it's about to expire! Reply immediately."),
        ("spam_or_irrelevant", False, "marketing disguised", "As a leading parts supplier, we'd love to feature your dealership in our directory. Sign up today."),
        ("spam_or_irrelevant", False, "cold email spam", "This is John from a digital marketing agency. We offer SEO for auto shops and saw you have a parts desk."),
        ("spam_or_irrelevant", False, "phishing", "URGENT: verify your account details or your order will be cancelled. Login now to confirm."),
        ("spam_or_irrelevant", False, "typo spam", "gr8 deal on car insurance call 555-1234 today"),
        ("spam_or_irrelevant", False, "irrelevant reply", "no thanks not interested in your newsletter"),
        ("spam_or_irrelevant", False, "MLM pitch", "be part of our team and earn from home, p.m this number"),
        ("spam_or_irrelevant", False, "fraud alert scam", "FLASH SALE 90% OFF ALL OEM PARTS, enter cc to reserve"),
        ("spam_or_irrelevant", False, "random text spam", "asdf qwerty 1234532 test"),
        ("spam_or_irrelevant", False, "reverse scam", "you have unpaid invoice bill it to this card now"),
        ("spam_or_irrelevant", False, "forum junk", "=== %s %s normal message ==="),
        ("spam_or_irrelevant", False, "investor spam", "I represent funds looking to acquire auto parts dealerships, reply for a meeting"),
    ]

    out = []
    for i, (label, nh, subj, body) in enumerate(S, start=1):
        out.append(
            {
                "subject": subj,
                "body": body,
                "sender_email": f"synth{len(out)+1:03d}@example.net",
                "label": label,
                "needs_human": nh,
                "source": "synthetic",
                "message_id": f"synth-{label}-{i:03d}",
            }
        )
    return out


def build() -> list[dict]:
    rows = _demo_rows() + _fixture_rows() + _synthetic_rows()
    # integrity: label must be a known class
    known = {
        "parts_availability", "price_request", "compatibility_fitment",
        "order_status", "sell_part", "general_question", "spam_or_irrelevant",
    }
    for r in rows:
        assert r["label"] in known, f"bad label {r['label']!r}"
        assert isinstance(r["needs_human"], bool), r
    return rows


if __name__ == "__main__":
    rows = build()
    out_file = HERE / "gold_labels.jsonl"
    with out_file.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    # distribution report
    from collections import Counter

    dist = Counter(r["label"] for r in rows)
    nh = Counter(("needs_human" if r["needs_human"] else "auto") for r in rows)
    print(f"total={len(rows)}")
    print("per_class=" + dict(dist).__str__())
    print("needs_human_ratio=" + dict(nh).__str__())
    print(f"wrote {out_file}")