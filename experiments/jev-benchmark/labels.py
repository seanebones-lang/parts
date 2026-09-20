"""Canonical JEV benchmark taxonomy (lowercase snake_case, per decision).

Seven mutually-exclusive CONTENT classes. ``needs_human`` is a separate
boolean adjudication flag evaluated independently — it is NOT a classification
label (per decision #2).

Mapping notes vs the existing production taxonomy in
``parrts.email.classify.EMAIL_TYPES`` and the backend ``EmailClassifierAgent``:

- parts_availability  ~ quote_request / parts_order  (system folds "do you have")
- price_request       ~ quote_request               (system folds price into quote)
- compatibility_fitment ~ (no dedicated class)      -> genuine fine-grained new class
- order_status        ~ shipping_inquiry            (system lumps tracking/delivery)
- sell_part           ~ (no class; misroutes to general) -> genuinely missing
- general_question    ~ general_inquiry / customer_service
- spam_or_irrelevant  ~ (falls to unknown)          -> genuinely missing

Category gaps (deliberate, surfaced by this benchmark): a true NEW-part
purchase/order-placement intent has NO dedicated content class; billing /
payment and complaint/escalation inquiries have NO content class. Per
decision #2 these are folded to the nearest content class and carried by the
``needs_human`` flag. See corpus/README.md for the full mapping.
"""

# Ordered list of the seven content classes.
CLASSES = (
    "parts_availability",
    "price_request",
    "compatibility_fitment",
    "order_status",
    "sell_part",
    "general_question",
    "spam_or_irrelevant",
)

# Named intent cover: which production category each class best maps to
# (informational only, used by run_benchmark to explain label space).
PRODUCTION_MAP = {
    "parts_availability": "quote_request / parts_order",
    "price_request": "quote_request",
    "compatibility_fitment": "(none — new)",
    "order_status": "shipping_inquiry",
    "sell_part": "(none — new)",
    "general_question": "general_inquiry / customer_service",
    "spam_or_irrelevant": "(unknown fallback)",
}

# Classes that should commonly carry needs_human=True (adjudication reference).
ESCALATION_PRONE = ("spam_or_irrelevant",)