"""Add a profile here without changing graph nodes, prompts or DB schemas."""

from app.schemas.execution import PersonaProfile

CATALOG = [
    (
        "budget",
        "Nadia",
        "Budget student",
        "18–24",
        "Dhaka",
        "Practical everyday essentials at a student-friendly price",
        "High",
        "peach",
    ),
    (
        "cod",
        "Rafi",
        "COD-first buyer",
        "25–34",
        "Chattogram",
        "Payment on delivery and clear delivery coverage",
        "Medium",
        "blue",
    ),
    (
        "skeptic",
        "Farhana",
        "Careful skeptic",
        "25–34",
        "Dhaka",
        "Authentic photos, customer reviews, and a clear return policy",
        "Medium",
        "lavender",
    ),
    (
        "office",
        "Arif",
        "Busy professional",
        "25–34",
        "Dhaka",
        "Reliable quality and convenient delivery",
        "Low",
        "mint",
    ),
    (
        "gift",
        "Tisha",
        "Thoughtful gift buyer",
        "25–34",
        "Sylhet",
        "Thoughtful packaging and delivery before a special occasion",
        "Medium",
        "rose",
    ),
    (
        "impulse",
        "Sami",
        "Impulse shopper",
        "18–24",
        "Dhaka",
        "A distinctive product, a clear offer, and quick ordering",
        "Low",
        "sand",
    ),
    (
        "bargain",
        "Mehedi",
        "Value seeker",
        "25–34",
        "Rajshahi",
        "Transparent pricing and a convincing reason to choose this product",
        "High",
        "blue",
    ),
    (
        "repeat",
        "Ayesha",
        "Returning customer",
        "35–44",
        "Dhaka",
        "Consistent quality and a familiar shopping experience",
        "Medium",
        "peach",
    ),
    (
        "trend",
        "Raisa",
        "Trend follower",
        "18–24",
        "Chattogram",
        "Current styles, relevant product variants, and evidence the item matches "
        "a trend; checks social appeal before committing",
        "Medium",
        "rose",
    ),
    (
        "genz",
        "Maya",
        "Digital-native Gen Z",
        "18–24",
        "Dhaka",
        "Mobile-friendly product details, useful creator demonstrations, and a "
        "smooth digital ordering experience; researches usability before buying",
        "Medium",
        "lavender",
    ),
    (
        "traditional",
        "Karim",
        "Old-school buyer",
        "45–60",
        "Khulna",
        "Plain-language details, a phone number or physical shop address, and "
        "personal help placing an order; prefers familiar buying steps",
        "Medium",
        "mint",
    ),
]


def profiles():
    return [
        PersonaProfile(
            id=pid,
            name=name,
            role=role,
            age=age,
            location=location,
            need=need,
            budget=budget + " sensitivity",
            color=color,
            initials=name[0],
        )
        for pid, name, role, age, location, need, budget, color in CATALOG
    ]
