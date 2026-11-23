"""Behavior-based duplicate checks; names and ages do not establish diversity."""

import re
import unicodedata
from difflib import SequenceMatcher


def normalized(value):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def duplicate_perspectives(profiles):
    duplicates = []
    for index, profile in enumerate(profiles):
        left = normalized(profile["need"])
        for other in profiles[:index]:
            right = normalized(other["need"])
            a, b = set(left.split()), set(right.split())
            overlap = len(a & b) / max(1, len(a | b))
            if (
                left == right
                or overlap >= 0.88
                or SequenceMatcher(None, left, right).ratio() >= 0.94
            ):
                duplicates.append((other["id"], profile["id"]))
    return duplicates
