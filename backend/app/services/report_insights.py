"""Ground recommendations in snapshots and group recurring buyer objections."""

import re

from app.core.persona_diversity import normalized
from app.services.trust_scoring import CUES, LABELS, trust_signals

TITLES = {
    "price": ("Make the price explicit", "দাম স্পষ্ট করুন"),
    "delivery": ("Clarify delivery coverage and timing", "ডেলিভারির এলাকা ও সময় স্পষ্ট করুন"),
    "delivery_cost": ("Show the total delivery cost", "ডেলিভারি চার্জ স্পষ্ট করুন"),
    "returns": ("Explain the return or exchange policy", "রিটার্ন বা এক্সচেঞ্জ নীতি জানান"),
    "warranty": ("State the warranty terms", "ওয়ারেন্টির শর্ত জানান"),
    "payment": ("Clarify payment options", "পেমেন্ট পদ্ধতি জানান"),
    "details": ("Answer product-detail questions", "পণ্যের বিবরণের প্রশ্নগুলোর উত্তর দিন"),
    "ordering": ("Give buyers a clear ordering step", "অর্ডারের পদ্ধতি স্পষ্ট করুন"),
    "contact": ("Make seller contact easy to find", "যোগাযোগের উপায় স্পষ্ট করুন"),
    "proof": ("Provide product evidence buyers can check", "যাচাইযোগ্য পণ্যের তথ্য দিন"),
}


def objection_groups(rows):
    groups = {}
    for row in rows:
        if row.status != "completed" or not row.output:
            continue
        output = row.output
        questions = output.get("objections") or [output.get("question", "")]
        for question in questions:
            topics = [
                key
                for key, pattern in CUES.items()
                if re.search(
                    pattern if key != "price" else r"price|cost|দাম|মূল্য|dam|taka",
                    question,
                    re.I,
                )
            ]
            if "delivery_cost" in topics and "delivery" in topics:
                topics.remove("delivery")
            if not topics:
                topics = ["other:" + normalized(question)]
            for key in topics:
                group = groups.setdefault(
                    key,
                    {"topic": key, "persona_ids": [], "questions": [], "evidence": []},
                )
                pid = row.profile["id"]
                if pid not in group["persona_ids"]:
                    group["persona_ids"].append(pid)
                if normalized(question) not in {
                    normalized(q) for q in group["questions"]
                }:
                    group["questions"].append(question)
                group["evidence"] = list(
                    dict.fromkeys([*group["evidence"], *output.get("evidence", [])])
                )[:12]
    return sorted(
        [
            {**group, "frequency": len(group["persona_ids"])}
            for group in groups.values()
        ],
        key=lambda group: (-group["frequency"], group["topic"]),
    )


def recommendations(inputs, rows):
    signals = trust_signals(inputs)
    groups = {group["topic"]: group for group in objection_groups(rows)}
    bn = inputs.get("language") == "bn"
    result = []
    for key, signal in signals.items():
        if signal["visible"] and key not in groups:
            continue
        # Avoid adding speculative warranty benefits when nobody asked for one.
        if key == "warranty" and not signal["supplied"] and key not in groups:
            continue
        group = groups.get(key, {})
        count = group.get("frequency", 0)
        label = LABELS[key][int(bn)]
        detail = (
            (
                f"{count} জন সম্পন্ন ক্রেতা এই বিষয়ে জানতে চেয়েছেন। "
                if bn
                else f"{count} completed perspective(s) asked about this topic. "
            )
            if count
            else (
                "সংরক্ষিত ক্যাপশনে এই তথ্য পরিষ্কার নয়। "
                if bn
                else "This information is not explicit in the saved caption. "
            )
        )
        detail += (
            "বিক্রেতার তথ্য যাচাই করে প্রকাশ করুন।"
            if bn
            else "Verify the seller-supplied details before publishing."
        )
        facts = signal["evidence"] if signal["source"] == "product" else []
        addition = (f"{label}: " if bn else f"{label.capitalize()}: ") + (
            "; ".join(facts)
            if facts
            else (
                "[প্রকাশের আগে সঠিক তথ্য নিশ্চিত করুন]"
                if bn
                else "[confirm verified details before publishing]"
            )
        )
        result.append(
            {
                "id": key,
                "title": TITLES[key][int(bn)],
                "detail": detail,
                "priority": "High priority"
                if count >= 2 or key in {"price", "delivery_cost", "payment"}
                else "Medium priority",
                "addition": addition,
                "evidence": list(
                    dict.fromkeys([*signal["evidence"], *group.get("evidence", [])])
                )[:12],
                "persona_ids": group.get("persona_ids", []),
                "frequency": count,
            }
        )
    return sorted(
        result,
        key=lambda rec: (
            -rec["frequency"],
            rec["priority"] != "High priority",
            rec["id"],
        ),
    )


def revised_caption(inputs, selected, recs):
    allowed = {rec["id"]: rec for rec in recs}
    unknown = set(selected) - allowed.keys()
    if unknown:
        raise ValueError("Choose recommendations from this saved report")
    post = inputs["post"]
    parts = [post.get("body", "")]
    additions = [allowed[key]["addition"] for key in dict.fromkeys(selected)]
    if additions:
        parts.append(
            (
                "যাচাই করার জন্য অতিরিক্ত তথ্য:\n"
                if inputs.get("language") == "bn"
                else "Additional details to verify:\n"
            )
            + "\n".join(additions)
        )
    for key in ("offer", "call_to_action"):
        value = post.get(key)
        if value and value not in post.get("body", ""):
            parts.append(value)
    tags = " ".join(post.get("hashtags") or [])
    if tags and tags not in post.get("body", ""):
        parts.append(tags)
    return "\n\n".join(part for part in parts if part)
