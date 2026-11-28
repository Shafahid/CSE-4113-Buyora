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

# Behavioral priorities are explicit fictional preferences, never inferred from
# age, gender, name, location or a claim about real Bangladeshi customers.
EXTRA = [
    (
        "delivery_cost",
        "Shuvo",
        "Total-cost planner",
        "Know the delivered total including courier fees before choosing a price",
        "মোট খরচ হিসাব করা ক্রেতা",
        "কুরিয়ার চার্জসহ হাতে পাওয়া পর্যন্ত মোট খরচ জানতে চান",
        "High",
    ),
    (
        "hurry",
        "Nabila",
        "Deadline buyer",
        "Confirm a realistic dispatch date and arrival window for an urgent need",
        "সময়সীমা মেনে কেনা ক্রেতা",
        "জরুরি প্রয়োজনে পাঠানোর তারিখ ও পৌঁছানোর সময় নিশ্চিত করতে চান",
        "Medium",
    ),
    (
        "sizing",
        "Rony",
        "Fit and measurement checker",
        "See exact dimensions, size options and how measurements match the "
        "intended use",
        "মাপ যাচাই করা ক্রেতা",
        "সঠিক দৈর্ঘ্য, আকারের বিকল্প ও ব্যবহার অনুযায়ী মাপ মিলিয়ে দেখতে চান",
        "Medium",
    ),
    (
        "materials",
        "Faria",
        "Material-detail reader",
        "Read the seller's stated composition and surface details without "
        "assuming authenticity",
        "উপাদানের বিবরণ দেখা ক্রেতা",
        "সত্যতা ধরে না নিয়ে বিক্রেতার দেওয়া উপাদান ও পৃষ্ঠের বিবরণ জানতে চান",
        "Low",
    ),
    (
        "specs",
        "Adnan",
        "Specification researcher",
        "Compare documented technical capacity, included accessories and "
        "operating requirements",
        "কারিগরি তথ্য যাচাইকারী",
        "ঘোষিত ক্ষমতা, সঙ্গে থাকা উপকরণ ও চালানোর শর্ত তুলনা করতে চান",
        "Medium",
    ),
    (
        "demonstration",
        "Mitu",
        "Demonstration-first shopper",
        "Watch an unedited demonstration of the exact item doing its stated task",
        "ডেমো দেখে সিদ্ধান্ত নেওয়া ক্রেতা",
        "একই পণ্য ঘোষিত কাজটি করছে এমন সম্পাদনাহীন ডেমো দেখতে চান",
        "Medium",
    ),
    (
        "durability",
        "Imran",
        "Long-use planner",
        "Understand care needs, repair options and documented durability "
        "limitations for repeated use",
        "দীর্ঘদিন ব্যবহারের পরিকল্পনাকারী",
        "বারবার ব্যবহারের জন্য যত্ন, মেরামত ও ঘোষিত স্থায়িত্বের সীমা জানতে চান",
        "Low",
    ),
    (
        "returns",
        "Sadia",
        "Exchange-process checker",
        "Know the exchange deadline, eligibility and who pays return "
        "shipping before ordering",
        "এক্সচেঞ্জের প্রক্রিয়া যাচাইকারী",
        "এক্সচেঞ্জের সময়সীমা, শর্ত ও ফেরত পাঠানোর খরচ কে দেবেন জানতে চান",
        "Medium",
    ),
    (
        "privacy",
        "Rashed",
        "Privacy-conscious buyer",
        "Understand which contact details are needed and whether discreet "
        "packaging is offered",
        "গোপনীয়তা সচেতন ক্রেতা",
        "কোন যোগাযোগের তথ্য লাগবে ও সাধারণ মোড়কের ব্যবস্থা আছে কি না জানতে চান",
        "Medium",
    ),
    (
        "accessibility",
        "Lamia",
        "Plain-information reader",
        "Find readable text, descriptive images and simple steps without "
        "relying on a video alone",
        "সহজ তথ্য পছন্দ করা ক্রেতা",
        "শুধু ভিডিওর ওপর নির্ভর না করে পড়ার মতো লেখা, ছবির বিবরণ ও সহজ ধাপ চান",
        "Medium",
    ),
    (
        "care",
        "Ovi",
        "Maintenance-cost checker",
        "Learn cleaning instructions, recurring consumable needs and "
        "storage conditions",
        "রক্ষণাবেক্ষণের খরচ দেখা ক্রেতা",
        "পরিষ্কারের নিয়ম, নিয়মিত লাগা উপকরণ ও সংরক্ষণের শর্ত জানতে চান",
        "High",
    ),
    (
        "low_waste",
        "Rima",
        "Low-waste shopper",
        "Ask about reusable packaging and service life without assuming "
        "environmental certification",
        "অপচয় কমাতে আগ্রহী ক্রেতা",
        "পরিবেশগত সনদ ধরে না নিয়ে পুনর্ব্যবহারযোগ্য মোড়ক ও ব্যবহারকাল জানতে চান",
        "Medium",
    ),
    (
        "bulk",
        "Tanvir",
        "Quantity-order planner",
        "Check minimum quantity, per-unit pricing and whether all pieces "
        "have the same specifications",
        "একাধিক পণ্য কেনার পরিকল্পনাকারী",
        "ন্যূনতম সংখ্যা, প্রতি পিসের দাম ও সব পণ্যের একই বৈশিষ্ট্য আছে কি না দেখেন",
        "High",
    ),
    (
        "compatibility",
        "Safa",
        "Compatibility checker",
        "Verify exact device, connector or existing-item compatibility "
        "before accepting a recommendation",
        "সামঞ্জস্য যাচাই করা ক্রেতা",
        "পরামর্শ মেনে কেনার আগে নির্দিষ্ট যন্ত্র, সংযোগ বা আগের পণ্যের সঙ্গে মিল যাচাই চান",
        "Medium",
    ),
    (
        "after_sales",
        "Mahin",
        "Support-first buyer",
        "Know how to contact support, its response hours and the "
        "documented warranty claim process",
        "বিক্রয়োত্তর সেবা দেখা ক্রেতা",
        "সহায়তায় যোগাযোগের উপায়, সময় ও ওয়ারেন্টি দাবির ঘোষিত প্রক্রিয়া জানতে চান",
        "Low",
    ),
    (
        "availability",
        "Nusaiba",
        "Stock-clarity checker",
        "Confirm the specific color or variant is available rather than "
        "substituting another item",
        "স্টক ও বিকল্প নিশ্চিত করা ক্রেতা",
        "অন্য পণ্য বদলে না দিয়ে নির্দিষ্ট রং বা ধরনটি আছে কি না নিশ্চিত হতে চান",
        "Medium",
    ),
    (
        "pickup",
        "Fahim",
        "Pickup planner",
        "Ask whether collection is available, where it happens and what "
        "inspection is permitted",
        "নিজে সংগ্রহের পরিকল্পনাকারী",
        "নিজে নেওয়ার ব্যবস্থা, ঠিকানা ও কীভাবে পণ্য দেখা যাবে জানতে চান",
        "High",
    ),
    (
        "family",
        "Sumi",
        "Shared-use organizer",
        "Check whether one item meets several stated household uses "
        "without guessing family traits",
        "একাধিক কাজে ব্যবহার করতে চাওয়া ক্রেতা",
        "পরিবার সম্পর্কে অনুমান না করে নিজের উল্লেখ করা একাধিক কাজে পণ্যটি চলবে কি না দেখেন",
        "Medium",
    ),
    (
        "safety",
        "Nafis",
        "Instruction and warning reader",
        "Look for operating instructions, age-use warnings and stated "
        "limitations without accepting safety guarantees",
        "ব্যবহারের সতর্কতা পড়া ক্রেতা",
        "নিরাপত্তার নিশ্চয়তা ধরে না নিয়ে নির্দেশনা, ব্যবহারসীমা ও সতর্কতা পড়তে চান",
        "Medium",
    ),
]
EXTRA_BANGLA = {pid: (role_bn, need_bn) for pid, _, _, _, role_bn, need_bn, _ in EXTRA}
CATALOG.extend(
    (pid, name, role, "Adult", "Bangladesh", need, budget, "blue")
    for pid, name, role, need, _, _, budget in EXTRA
)


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
