"""Generate a completely blind 200-example holdout corpus.

All examples and gold labels are created without reference to any classifier output
or the original 124-example development set.

This file is run once, then the resulting holdout_labels.jsonl is frozen.
"""
import json
import random
from pathlib import Path

CLASSES = [
    "parts_availability",
    "price_request",
    "compatibility_fitment",
    "order_status",
    "sell_part",
    "general_question",
    "spam_or_irrelevant",
]

def generate_examples(n=200):
    examples = []
    random.seed(42)  # for reproducibility of the generation process only

    # Distribution target (roughly balanced with needs_human ~25%)
    target = {
        "parts_availability": 32,
        "price_request": 35,
        "compatibility_fitment": 28,
        "order_status": 25,
        "sell_part": 22,
        "general_question": 30,
        "spam_or_irrelevant": 28,
    }

    # Very diverse templates (none copied from development set)
    templates = {
        "parts_availability": [
            ("do u got the thing for my truck", False),
            ("2018 f150 front brake pads in stock anywhere", False),
            ("need oil filter 2021 rav4, u have it?", False),
            ("spark plugs for civic 2017 — got any left", False),
            ("alternator for 2015 accord, do you carry", False),
            ("water pump 2019 silverado 5.3 — in dallas?", False),
            ("timing belt kit for 2014 camry hybrid", False),
            ("clutch for 2016 civic si, any in the back", False),
            ("cabin filter for 2020 accord — stock?", False),
            ("do you still have the one i called about yesterday", True),
        ],
        "price_request": [
            ("how much for front rotors on a 2018 f150", False),
            ("price on brake pads 2019 civic please", False),
            ("what does an oil filter for 2021 rav4 cost", False),
            ("ngk spark plugs for civic, how much", False),
            ("alternator price for 2015 accord", False),
            ("how much shipped for water pump 2019 silverado", False),
            ("timing belt kit price 2014 camry", False),
            ("clutch kit cost for 2016 civic si", False),
            ("cabin filter price 2020 accord", False),
            ("can you quote me on those parts we talked about last week", True),
        ],
        "compatibility_fitment": [
            ("will these pads fit my 2019 civic", False),
            ("does the 2020 filter also fit the 2021 rav4", False),
            ("is this rotor the same as oem 45251-sda-a05", False),
            ("will the camry alternator work on a lexus es350", False),
            ("do the 2019 accord pads fit the 2020 model", False),
            ("is part 1123 interchangeable with my 2018 f150", False),
            ("will the 2.0 engine one fit the 1.5t", True),
            ("does the si clutch fit a regular civic", False),
            ("are these pads the right ones for my 6 cylinder accord", False),
            ("fitment for the brake kit on a 2017 civic", False),
        ],
        "order_status": [
            ("where is my order from last week", False),
            ("can you send the tracking for order 28491", False),
            ("has my rotors shipped yet", False),
            ("any update on the parts i ordered tuesday", True),
            ("did the brake pads go out already", False),
            ("tracking number for the water pump", False),
            ("when will my order arrive", False),
            ("order 39201 status please", False),
            ("is my shipment still in transit", False),
            ("did you cancel my order or is it coming", True),
        ],
        "sell_part": [
            ("i have some used rotors i want to sell you", False),
            ("do you buy used alternators", False),
            ("got a set of take off wheels for sale", False),
            ("interested in buying my old clutch", False),
            ("would you take these brake pads off my hands", False),
            ("selling a used water pump, you buying?", False),
            ("do you purchase catalytic converters", False),
            ("i have some oem parts i dont need anymore", False),
            ("trade in value on my old alternator", False),
            ("anyone want to buy these used pads cheap", False),
        ],
        "general_question": [
            ("what time does the parts counter close", False),
            ("do you take apple pay at the counter", False),
            ("where is your location in arlington", False),
            ("what is your return policy on electrical parts", False),
            ("can i pick up an order after 5", False),
            ("do you have a phone number for parts", False),
            ("are you open on saturdays", False),
            ("how long does ground shipping usually take", False),
            ("do you do any labor or just sell parts", False),
            ("is there a manager i can speak with about an order", True),
        ],
        "spam_or_irrelevant": [
            ("congratulations you won a $500 gift card click here", False),
            ("act now your vehicles warranty is about to expire", False),
            ("we can get you more customers for your dealership", False),
            ("this is john from digital marketing we saw your site", False),
            ("verify your account or your order will be cancelled", False),
            ("earn from home be your own boss call this number", False),
            ("90 percent off all oem parts today only", False),
            ("random text message about car insurance", False),
            ("we represent investors looking to acquire auto shops", False),
            ("flash sale on brake pads enter your card now", False),
        ],
    }

    for label, count in target.items():
        for i in range(count):
            tmpl, risky = random.choice(templates[label])
            # add realistic messiness
            if random.random() < 0.25:
                tmpl = tmpl.upper()
            if random.random() < 0.15:
                tmpl = tmpl.replace(" ", "")  # run-on
            if random.random() < 0.2:
                tmpl = tmpl + " thx"

            needs_human = risky or (random.random() < 0.12 and label != "spam_or_irrelevant")

            examples.append({
                "subject": tmpl[:60],
                "body": tmpl,
                "sender_email": f"holdout{random.randint(10000,99999)}@example.com",
                "label": label,
                "needs_human": needs_human,
                "source": "holdout_synthetic",
                "message_id": f"holdout-{label}-{i:03d}",
            })

    random.shuffle(examples)
    return examples[:n]


if __name__ == "__main__":
    exs = generate_examples(200)
    out = Path(__file__).parent / "holdout_labels.jsonl"
    with out.open("w") as f:
        for e in exs:
            f.write(json.dumps(e) + "\n")
    print(f"wrote {len(exs)} examples to {out}")