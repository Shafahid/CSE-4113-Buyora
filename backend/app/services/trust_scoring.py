"""Versioned information-completeness rubric, never a sales probability.

Structured seller facts and visible caption claims are distinguished. A stated
negative policy is clear information; it is not silently converted to a benefit.
"""

import re

from app.schemas.execution import PROMPT_VERSION, RULES_VERSION, Verdict

DIMENSIONS = (
    "Interest",
    "Relevance",
    "Value",
    "Price fit",
    "Trust",
    "Clarity",
    "Purchase intent",
)
FOCUS = {
    "budget": ("price", "delivery_cost"),
    "bargain": ("price", "details"),
    "cod": ("payment", "delivery"),
    "skeptic": ("returns", "details"),
    "office": ("delivery", "ordering"),
    "gift": ("delivery", "details"),
    "impulse": ("ordering", "price"),
    "repeat": ("details", "returns"),
    "trend": ("details", "proof"),
    "genz": ("proof", "ordering"),
    "traditional": ("contact", "ordering"),
    "delivery_cost": ("delivery_cost", "price"),
    "hurry": ("delivery", "contact"),
    "sizing": ("details", "returns"),
    "materials": ("details", "proof"),
    "specs": ("details", "warranty"),
    "demonstration": ("proof", "details"),
    "durability": ("warranty", "details"),
    "returns": ("returns", "delivery_cost"),
    "privacy": ("contact", "delivery"),
    "accessibility": ("ordering", "details"),
    "care": ("details", "price"),
    "low_waste": ("details", "proof"),
    "bulk": ("price", "ordering"),
    "compatibility": ("details", "returns"),
    "after_sales": ("contact", "warranty"),
    "availability": ("details", "contact"),
    "pickup": ("contact", "delivery_cost"),
    "family": ("details", "price"),
    "safety": ("details", "warranty"),
}
LABELS = {
    "price": ("price", "দাম"),
    "delivery": ("delivery coverage and timing", "ডেলিভারির এলাকা ও সময়"),
    "delivery_cost": ("delivery charges", "ডেলিভারি চার্জ"),
    "returns": ("return or exchange policy", "রিটার্ন বা এক্সচেঞ্জ নীতি"),
    "warranty": ("warranty terms", "ওয়ারেন্টির শর্ত"),
    "payment": ("payment methods", "পেমেন্ট পদ্ধতি"),
    "details": ("product details", "পণ্যের বিবরণ"),
    "ordering": ("ordering instructions", "অর্ডারের পদ্ধতি"),
    "contact": ("seller contact options", "বিক্রেতার সাথে যোগাযোগের উপায়"),
    "proof": (
        "product demonstration or review information",
        "পণ্যের ডেমো বা রিভিউয়ের তথ্য",
    ),
}
CUES = {
    "delivery": r"delivery|courier|ডেলিভারি|ডেলিভারী|পৌঁছ|delivari",
    "delivery_cost": (
        r"delivery (?:charge|fee|cost)|shipping (?:charge|fee|cost)|"
        r"ডেলিভারি (?:চার্জ|খরচ)|delivery khoroch"
    ),
    "returns": r"return|exchange|রিটার্ন|ফেরত|এক্সচেঞ্জ|বিনিময়|ferot",
    "warranty": r"warranty|guarantee|ওয়ারেন্টি|গ্যারান্টি|ওয়ারেন্টী",
    "payment": (
        r"\bcod\b|cash on delivery|payment|b[kK]ash|nagad|"
        r"পেমেন্ট|ক্যাশ অন|বিকাশ|নগদ"
    ),
    "details": (
        r"material|canvas|cotton|size|battery|capacity|উপাদান|সুতি|"
        r"মাপ|সাইজ|ব্যাটারি|ক্যানভাস"
    ),
    "ordering": r"order|message|inbox|অর্ডার|মেসেজ|ইনবক্স|যোগাযোগ|যোগাযোগ",
    "contact": r"phone|call|shop|address|ফোন|কল|দোকান|ঠিকানা|\+?8801[3-9]\d{8}",
    "proof": r"demo|review|photo|video|ডেমো|রিভিউ|ছবি|ভিডিও",
    "price": (
        r"(?:৳|\bbdt\b|\btk\b|\btaka\b|\bprice\b|\bdam\b|দাম|টাকা)"
        r"\s*[:=–-]?\s*[\d০-৯]|[\d০-৯][\d০-৯,.]*\s*(?:টাকা|taka|tk)\b"
    ),
}
PRODUCT_FIELDS = {
    "price": "price",
    "delivery": "delivery_info",
    "returns": "return_policy",
    "warranty": "warranty",
    "details": "description",
}


def strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in strings(item)]
    return []


def trust_signals(inputs):
    product, post = inputs["product"], inputs["post"]
    fragments = [
        fragment.strip()
        for text in strings(post)
        for fragment in re.split(r"[\n।;]+|(?<=[.!?])\s+", text)
        if fragment.strip()
    ]
    result = {}
    for key, cue in CUES.items():
        visible = [
            text
            for text in fragments
            if re.search(cue, text, re.I)
            and not text.endswith("?")
            and not re.search(
                r"coming soon|to be confirmed|not specified|জানানো হবে|পরে জানাব",
                text,
                re.I,
            )
        ]
        supplied = product.get(PRODUCT_FIELDS.get(key, ""))
        if key == "details":
            supplied = supplied or product.get("features")
        source = "post" if visible else "product" if supplied else None
        evidence = visible[:3] or strings(supplied)[:3]
        negative = any(
            re.search(
                r"\bno\b|not (?:available|offered|accepted)|unavailable|"
                r"নেই|হবে না|হয় না|nai|deya hoy na",
                text,
                re.I,
            )
            for text in evidence
        )
        result[key] = {
            "supplied": bool(evidence),
            "visible": bool(visible),
            "negative": negative,
            "source": source,
            "evidence": evidence,
        }
    return result


def sensitivity(profile):
    value = profile.get("budget", "").casefold()
    return (
        "high"
        if "high" in value or "বেশি" in value or "উচ্চ" in value
        else "low"
        if "low" in value or "কম" in value
        else "medium"
    )


def deterministic_evaluation(inputs, profile, reason="provider_unavailable"):
    signals = trust_signals(inputs)
    bn = inputs.get("language") == "bn"
    banglish = inputs.get("writing_style") == "banglish"
    priorities = FOCUS.get(profile["id"], ("details", "price", "delivery"))
    missing = [
        key
        for key in priorities
        if not signals[key]["supplied"] or signals[key]["negative"]
    ]
    missing += [
        key
        for key in ("price", "delivery_cost", "payment", "returns", "ordering")
        if not signals[key]["supplied"] and key not in missing
    ]
    concern = missing[0] if missing else priorities[0]
    label = LABELS[concern][int(bn)]
    question = (
        f"{label} সম্পর্কে বিস্তারিত নিশ্চিত করবেন?"
        if bn
        else f"Can you confirm the {label}?"
    )
    if banglish:
        question = f"{label} ta ektu confirm korben?"
    present = sum(s["supplied"] for s in signals.values())
    visible = sum(s["visible"] for s in signals.values())
    clarity = min(90, 35 + 6 * visible + 3 * present)
    trust = min(
        85,
        35
        + 8
        * sum(
            signals[key]["supplied"]
            for key in ("delivery", "returns", "payment", "contact", "proof")
        ),
    )
    price = (
        45
        + 15 * signals["price"]["supplied"]
        + 10 * signals["delivery_cost"]["supplied"]
    )
    if sensitivity(profile) == "high" and not signals["delivery_cost"]["supplied"]:
        price -= 10
    relevance = 60 if signals["details"]["supplied"] else 40
    value = 45 + 15 * signals["details"]["supplied"] + 10 * signals["price"]["supplied"]
    interest = (
        45 + 15 * signals["details"]["supplied"] + 10 * signals["proof"]["supplied"]
    )
    penalty = 8 * sum(
        not signals[key]["supplied"] or signals[key]["negative"] for key in priorities
    )
    intent = min(75, round((trust + price + clarity) / 3) - penalty)
    if profile["id"] == "cod" and signals["payment"]["negative"]:
        intent = min(intent, 30)
    scores = [
        max(0, min(100, int(score)))
        for score in (interest, relevance, value, price, trust, clarity, intent)
    ]
    evidence = list(
        dict.fromkeys(
            quote for signal in signals.values() for quote in signal["evidence"]
        )
    )[:12]
    if not evidence:
        evidence = [profile["need"]]
    drivers = []
    groups = (
        ("details", "proof"),
        ("details",),
        ("details", "price"),
        ("price", "delivery_cost"),
        ("returns", "payment", "delivery"),
        ("ordering", "price", "contact"),
        priorities,
    )
    for dimension, keys in zip(DIMENSIONS, groups, strict=True):
        gaps = [
            LABELS[key][int(bn)]
            for key in keys
            if not signals[key]["supplied"] or signals[key]["negative"]
        ]
        text = (
            ("যাচাই প্রয়োজন: " if bn else "Needs confirmation: ") + ", ".join(gaps)
            if gaps
            else (
                "সংশ্লিষ্ট তথ্য দেওয়া আছে; দাবিগুলো স্বাধীনভাবে যাচাই করা হয়নি।"
                if bn
                else "Relevant information is supplied; seller claims are not "
                "independently verified."
            )
        )
        drivers.append(
            {
                "dimension": dimension,
                "reason": text,
                "evidence": list(
                    dict.fromkeys(q for key in keys for q in signals[key]["evidence"])
                )[:3],
            }
        )
        if banglish:
            drivers[-1]["reason"] = (
                "Confirm kora dorkar: " + ", ".join(gaps)
                if gaps
                else "Tothyo deoya ache; seller-er daabi alada kore jachai kora hoyni."
            )
    return Verdict(
        scores=scores,
        comment=question,
        question=question,
        reason=(
            "Eta deoya tothyo o buyer-er priority diye rule-based assessment; "
            "AI motamot ba bikrir forecast noy."
            if banglish
            else "সংরক্ষিত তথ্য ও এই ক্রেতার চাহিদার ভিত্তিতে নিয়মভিত্তিক মূল্যায়ন। "
            "এটি AI-এর মতামত বা বিক্রির পূর্বাভাস নয়।"
            if bn
            else "Rule-based assessment of the saved information and this buyer's "
            "priorities. This is not an AI verdict or a sales forecast."
        ),
        positive=(
            "Ponno niye kichu tothyo deoya ache; publish korar age jachai korun."
            if banglish
            else "পণ্যের সম্পর্কে কিছু তথ্য দেওয়া আছে; প্রকাশের আগে তথ্যগুলো যাচাই করুন।"
            if bn
            else "The saved input supplies product information "
            "to check before publishing."
        ),
        evidence=evidence,
        objections=[question] if missing else [],
        score_drivers=drivers,
        evaluation_source="fallback",
        fallback_reason=reason,
        prompt_version=None,
        rules_version=RULES_VERSION,
    ).model_dump()


def evaluation_metadata(source="ai"):
    return {
        "evaluation_source": source,
        "prompt_version": PROMPT_VERSION if source == "ai" else None,
        "rules_version": RULES_VERSION,
    }
