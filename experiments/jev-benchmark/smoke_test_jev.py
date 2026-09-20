"""Jev smoke test - 3 cases only (Phase 6)"""
import asyncio
import time
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul

STATE = {
    "subject": "{subject}",
    "body": "{body}",
    "sender_email": "{sender_email}"
}

QUESTIONS = {
    "category": Choice(
        instructions="Determine the primary operational intent of this incoming automotive-parts/customer-service inquiry. Select exactly one category based on the customer's main requested action or purpose.",
        criteria={
            "parts_availability": "The customer primarily wants to know whether a specific part or relevant item is available, in stock, obtainable, or can be sourced.",
            "price_request": "The customer primarily wants a price, quote, estimate, or cost for a part or parts.",
            "compatibility_fitment": "The customer primarily wants to know whether a part fits, matches, cross-references, or is compatible with a specific vehicle, configuration, model, or other part.",
            "order_status": "The customer primarily wants information about an existing order, shipment, delivery, tracking status, pickup status, fulfillment, or order progress.",
            "sell_part": "The customer primarily wants to sell, trade, consign, dispose of, or offer parts/items to the business rather than buy them.",
            "general_question": "A legitimate customer inquiry that does not fit the other operational categories, such as hours, location, policies, general service information, or broad questions.",
            "spam_or_irrelevant": "Unsolicited marketing, scams, unrelated solicitations, clearly irrelevant content, malicious/fraudulent outreach, or content that is not a legitimate automotive-parts/customer-service inquiry.",
        },
    ),
    "needs_human": Noul(
        instructions="Does this inquiry require human review rather than safe automatic routing or handling?",
        criteria={
            "true": "Human review is warranted because of meaningful operational risk or customer impact. Examples of the TYPE of situation include serious complaints, safety concerns, fraud or payment disputes, legal/threatening language, explicit request for a manager or person, ambiguous high-impact requests, or situations where automated handling could materially harm the customer or business.",
            "false": "The inquiry can reasonably be routed or handled automatically without meaningful safety, financial, legal, customer-relations, or operational risk requiring immediate human judgment.",
        },
    ),
}

async def run_smoke(name, subject, body, sender_email):
    state = {"subject": subject, "body": body, "sender_email": sender_email}
    t0 = time.perf_counter()
    async with AsyncTypeSafeClient() as client:
        resp = await client.system_one(
            model="jev-latest",
            state=state,
            questions=QUESTIONS,
        )
    latency = time.perf_counter() - t0

    cat = resp.answers.get("category")
    nh = resp.answers.get("needs_human")

    print(f"\n=== {name} ===")
    print(f"Latency: {latency:.2f}s")
    print(f"Category: {cat.choice if cat else None}")
    print(f"Category confidence: {getattr(cat, 'confidence', None)}")
    if cat and hasattr(cat, 'probabilities'):
        probs = sorted(cat.probabilities.items(), key=lambda x: -x[1])[:3]
        print(f"Top probabilities: {probs}")
    print(f"Noul probability: {getattr(nh, 'noul', None)}")
    if hasattr(resp, 'usage'):
        print(f"Usage: {resp.usage}")
    return resp

async def main():
    tests = [
        ("Price Request", "Quote on front brake pads", "How much for front brake pads for a 2019 Honda Civic?", "customer@example.com"),
        ("Sell Part", "Want to sell used parts", "I have some used rotors and want to sell them to you.", "seller@example.com"),
        ("Serious Complaint", "Safety issue + refund demand", "The brake pads you sold me are defective and almost caused an accident. I want a full refund and to speak to a manager immediately.", "angry@example.com"),
    ]
    for name, subj, body, email in tests:
        await run_smoke(name, subj, body, email)

if __name__ == "__main__":
    asyncio.run(main())