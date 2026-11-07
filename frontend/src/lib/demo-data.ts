export type Product = {
  id: string;
  name: string;
  price: number;
  category: string;
  description: string;
  features: string;
  warranty: string;
  delivery: string;
  returns: string;
  image: string;
  art: string;
  archived: boolean;
};
export type PostVersion = { id: string; body: string; createdAt: string };
export type Post = {
  id: string;
  productId: string;
  headline: string;
  body: string;
  offer: string;
  cta: string;
  hashtags: string;
  platform: string;
  versions: PostVersion[];
};
export type Persona = {
  id: string;
  name: string;
  role: string;
  age: string;
  location: string;
  need: string;
  budget: string;
  color: string;
  initials: string;
};
export type Audience = {
  location: string;
  age: string;
  interests: string;
  preferences: string;
  budget: string;
  needs: string;
};
export type Draft = {
  productId: string;
  post: Post;
  audience: Audience;
  personas: Persona[];
  language: "en" | "bn";
  failOne: boolean;
  step: number;
};
export const dimensions = [
  "Interest",
  "Relevance",
  "Value",
  "Price fit",
  "Trust",
  "Clarity",
  "Purchase intent",
] as const;
export type Reaction = {
  persona: Persona;
  scores: number[];
  score: number;
  status: "complete" | "failed";
  sentiment: "Interested" | "Has questions" | "Unconvinced";
  comment: string;
  reason: string;
  positive: string;
  question: string;
};
export type Report = {
  id: string;
  title: string;
  createdAt: string;
  product: Product;
  post: Post;
  audience: Audience;
  language: "en" | "bn";
  reactions: Reaction[];
  revised: string;
  applied: string[];
};
export type DemoState = {
  version: 1;
  products: Product[];
  posts: Post[];
  reports: Report[];
  draft: Draft;
  profile: { name: string; email: string };
  signedIn: boolean;
};

export const products: Product[] = [
  {
    id: "p-tote",
    name: "Nila everyday tote",
    price: 890,
    category: "Fashion & accessories",
    description:
      "An everyday companion, made with heavyweight cotton canvas. Room for your laptop, books, and everything in between.",
    features:
      "100% cotton canvas, inner pocket, 14-inch laptop friendly, natural and ocean blue",
    warranty: "30-day stitching warranty",
    delivery: "Dhaka: 2–3 days, ৳60. Outside Dhaka: 3–5 days, ৳120.",
    returns: "Exchange within 7 days for unused items.",
    image: "",
    art: "tote",
    archived: false,
  },
  {
    id: "p-audio",
    name: "Airwave wireless earbuds",
    price: 1890,
    category: "Electronics",
    description:
      "Lightweight wireless earbuds for commutes, calls, and a little quiet time.",
    features: "24-hour battery with case, USB-C charging, touch controls",
    warranty: "6-month replacement warranty",
    delivery: "Nationwide delivery in 3–5 days. Charge: ৳100.",
    returns: "7-day replacement for manufacturing defects.",
    image: "",
    art: "audio",
    archived: false,
  },
  {
    id: "p-kurta",
    name: "Dawn cotton panjabi",
    price: 1450,
    category: "Clothing",
    description:
      "Breathable cotton with subtle embroidery, made for everyday celebrations.",
    features: "Pure cotton, sizes S–XXL, three colours",
    warranty: "Quality checked before dispatch",
    delivery: "Dhaka: 1–2 days, ৳80. Nationwide: 3–5 days, ৳130.",
    returns: "Size exchange within 3 days of delivery.",
    image: "",
    art: "kurta",
    archived: false,
  },
];
export const personas: Persona[] = [
  {
    id: "budget",
    name: "Nadia",
    role: "Budget student",
    age: "18–24",
    location: "Dhaka",
    need: "Practical everyday essentials at a student-friendly price",
    budget: "High sensitivity",
    color: "peach",
    initials: "N",
  },
  {
    id: "cod",
    name: "Rafi",
    role: "COD-first buyer",
    age: "25–34",
    location: "Chattogram",
    need: "Payment on delivery and clear delivery coverage",
    budget: "Medium sensitivity",
    color: "blue",
    initials: "R",
  },
  {
    id: "skeptic",
    name: "Farhana",
    role: "Careful skeptic",
    age: "25–34",
    location: "Dhaka",
    need: "Authentic photos, customer reviews, and a clear return policy",
    budget: "Medium sensitivity",
    color: "lavender",
    initials: "F",
  },
  {
    id: "office",
    name: "Arif",
    role: "Busy professional",
    age: "25–34",
    location: "Dhaka",
    need: "Reliable quality and convenient delivery",
    budget: "Low sensitivity",
    color: "mint",
    initials: "A",
  },
  {
    id: "gift",
    name: "Tisha",
    role: "Thoughtful gift buyer",
    age: "25–34",
    location: "Sylhet",
    need: "Thoughtful packaging and delivery before a special occasion",
    budget: "Medium sensitivity",
    color: "rose",
    initials: "T",
  },
  {
    id: "impulse",
    name: "Sami",
    role: "Impulse shopper",
    age: "18–24",
    location: "Dhaka",
    need: "A distinctive product, a clear offer, and quick ordering",
    budget: "Low sensitivity",
    color: "sand",
    initials: "S",
  },
  {
    id: "bargain",
    name: "Mehedi",
    role: "Value seeker",
    age: "25–34",
    location: "Rajshahi",
    need: "Transparent pricing and a convincing reason to choose this product",
    budget: "High sensitivity",
    color: "blue",
    initials: "M",
  },
  {
    id: "repeat",
    name: "Ayesha",
    role: "Returning customer",
    age: "35–44",
    location: "Dhaka",
    need: "Consistent quality and a familiar shopping experience",
    budget: "Medium sensitivity",
    color: "peach",
    initials: "A",
  },
];
export const posts: Post[] = products.map((p, i) => ({
  id: `post-${p.id}`,
  productId: p.id,
  headline: [
    "A little room for your everyday.",
    "Your everyday, with a better soundtrack.",
    "Comfort for every celebration.",
  ][i],
  body: [
    "Meet your new everyday carry. Our Nila tote is made from heavyweight cotton canvas, with room for your laptop, books, and little essentials. Available in natural and ocean blue. Only ৳890. Inbox us to find your colour!",
    "Meet Airwave. Clear calls, rich sound, and 24 hours of battery life with the case. ৳1,890 with a 6-month replacement warranty. Cash on delivery nationwide. Order in our inbox.",
    "A fresh look for your next celebration. Soft cotton, subtle embroidery, and a fit that feels just right. Dawn panjabi, ৳1,450. S–XXL available. Message us for your size.",
  ][i],
  offer: "",
  cta: "Message us to order",
  hashtags: "#ShopLocal #MadeForEveryday",
  platform: "Facebook",
  versions: [],
}));
export const initialDraft: Draft = {
  productId: products[0].id,
  post: posts[0],
  audience: {
    location: "Dhaka, Bangladesh",
    age: "18–34",
    interests: "Local brands, sustainable fashion, everyday accessories",
    preferences: "Cash on delivery",
    budget: "Medium sensitivity",
    needs: "An affordable, practical everyday bag",
  },
  personas: personas.slice(0, 6),
  language: "en",
  failOne: false,
  step: 0,
};

export type Recommendation = {
  id: string;
  title: string;
  detail: string;
  priority: string;
  addition: string;
};
export function recommendations(
  report: Pick<Report, "post" | "product">,
): Recommendation[] {
  const body = report.post.body.toLowerCase();
  return [
    ...(!/delivery|ডেলিভারি/.test(body)
      ? [
          {
            id: "delivery",
            title: "Make delivery details easy to find",
            detail:
              "Buyers need to know the delivery charge and when their order will arrive.",
            priority: "High priority",
            addition: report.product.delivery,
          },
        ]
      : []),
    ...(!/cash on delivery|cod|ক্যাশ অন/.test(body)
      ? [
          {
            id: "payment",
            title: "Clarify payment options",
            detail:
              "COD-first buyers want to understand how they can pay. Confirm availability before publishing.",
            priority: "High priority",
            addition: "Payment: [add your verified payment methods].",
          },
        ]
      : []),
    ...(!/exchange|return|রিটার্ন|বিনিময়/.test(body)
      ? [
          {
            id: "returns",
            title: "Include your exchange policy",
            detail:
              "A clear policy can address hesitation before buyers message you.",
            priority: "Medium priority",
            addition: report.product.returns,
          },
        ]
      : []),
    {
      id: "proof",
      title: "Add proof buyers can check",
      detail:
        "Include an authentic product photo or a real customer review. Never invent testimonials.",
      priority: "Medium priority",
      addition:
        "[Attach an authentic product photo or a verified customer review.]",
    },
  ];
}

// Deterministic placeholder scores for UI development. This is not an AI evaluation.
export function evaluate(
  persona: Persona,
  product: Product,
  post: Post,
  language: "en" | "bn",
  index = 0,
): Reaction {
  const body = post.body.toLowerCase();
  const clarity = Math.min(
    95,
    45 +
      (body.length > 100 ? 14 : 0) +
      (/৳|bdt|price|টাকা|\d{3}/.test(body) ? 14 : 0) +
      (post.cta ? 10 : 0),
  );
  const trust =
    38 +
    (/delivery|ডেলিভারি/.test(body) ? 14 : 0) +
    (/return|exchange|বিনিময়/.test(body) ? 15 : 0) +
    (/warranty|review|ওয়ারেন্টি/.test(body) ? 14 : 0) +
    (/cod|cash on delivery/.test(body) ? 12 : 0);
  const budget =
    persona.budget === "High sensitivity"
      ? 58
      : persona.budget === "Low sensitivity"
        ? 86
        : 73;
  const variation = (index * 7 + (post.body.length % 13)) % 18;
  const scores = [
    Math.min(96, 73 + variation),
    Math.min(95, 72 + variation),
    Math.min(92, budget + 6),
    Math.max(35, budget - (product.price > 1500 ? 10 : 0)),
    Math.max(25, trust - (persona.id === "skeptic" ? 12 : 0)),
    clarity,
    Math.round((trust + budget + clarity) / 3),
  ];
  const score = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  const questions: Record<string, [string, string]> = {
    budget: [
      "Is there a student discount? What is the total with delivery?",
      "স্টুডেন্ট ডিসকাউন্ট আছে? ডেলিভারিসহ মোট কত হবে?",
    ],
    cod: [
      "Can I pay cash on delivery outside Dhaka?",
      "ঢাকার বাইরে কি ক্যাশ অন ডেলিভারি হবে?",
    ],
    skeptic: [
      "Can I see real photos and the exchange policy?",
      "আসল ছবি আর এক্সচেঞ্জ পলিসি দেখতে পারি?",
    ],
    office: [
      "Can you deliver to my office? How many days will it take?",
      "অফিসে ডেলিভারি হবে? কত দিন লাগবে?",
    ],
    gift: [
      "Do you offer gift packaging and scheduled delivery?",
      "গিফট প্যাকেজিং আর নির্দিষ্ট দিনে ডেলিভারি হবে?",
    ],
    impulse: [
      "Love the look! How do I place an order?",
      "দেখতে দারুণ! অর্ডার করব কীভাবে?",
    ],
    bargain: [
      "What makes this better value than other options?",
      "অন্যগুলোর চেয়ে এটার বিশেষত্ব কী?",
    ],
    repeat: [
      "Is the quality the same as my previous order?",
      "আগের অর্ডারের মতো একই মানের হবে?",
    ],
  };
  const question = (questions[persona.id] || [
    "Can you share more product details?",
    "পণ্যের আরও তথ্য দিতে পারবেন?",
  ])[language === "bn" ? 1 : 0];
  return {
    persona: { ...persona },
    scores,
    score,
    status: "complete",
    sentiment:
      score >= 76
        ? "Interested"
        : score >= 60
          ? "Has questions"
          : "Unconvinced",
    comment: question,
    question,
    reason:
      language === "bn"
        ? `${persona.need} — এই চাহিদার ভিত্তিতে নমুনা প্রতিক্রিয়া।`
        : `${persona.role} prioritizes ${persona.need.toLowerCase()}. ${trust < 65 ? "The caption leaves payment or policy questions unanswered." : "The caption provides useful reassurance about the purchase."}`,
    positive:
      language === "bn"
        ? "পণ্যের বিবরণ এবং স্পষ্ট দাম সহায়ক।"
        : `${product.name} has a clear use case. ${/৳|\d{3}/.test(body) ? "The visible price makes comparison easier." : "A visible price would make comparison easier."}`,
  };
}
export function makeReport(
  draft: Draft,
  product: Product,
  id: string,
  date: string,
): Report {
  return {
    id,
    title: product.name,
    createdAt: date,
    product: { ...product },
    post: { ...draft.post, versions: [...draft.post.versions] },
    audience: { ...draft.audience },
    language: draft.language,
    reactions: draft.personas.map((p, i) => ({
      ...evaluate(p, product, draft.post, draft.language, i),
      status:
        draft.failOne && i === draft.personas.length - 1
          ? "failed"
          : "complete",
    })),
    revised: "",
    applied: [],
  };
}
export function overall(report: Report, dimension?: number): number {
  const done = report.reactions.filter((r) => r.status === "complete");
  return done.length
    ? Math.round(
        done.reduce(
          (sum, r) =>
            sum + (dimension === undefined ? r.score : r.scores[dimension]),
          0,
        ) / done.length,
      )
    : 0;
}
const seedReports = products.map((product, i) =>
  makeReport(
    {
      ...initialDraft,
      productId: product.id,
      post: posts[i],
      personas: personas.slice(0, 6 + i),
    },
    product,
    `sample-${i + 1}`,
    `2026-11-0${6 - i}T10:30:00.000Z`,
  ),
);
export const initialState: DemoState = {
  version: 1,
  products,
  posts,
  reports: seedReports,
  draft: initialDraft,
  profile: { name: "Soma Rahman", email: "soma@example.com" },
  signedIn: false,
};
export const uid = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
export function savePostVersion(
  existing: Post | undefined,
  next: Post,
  now = new Date().toISOString(),
): Post {
  const versions = existing?.versions || next.versions;
  const changed = existing && existing.body !== next.body;
  return {
    ...next,
    versions: changed
      ? [...versions, { id: uid(), body: existing.body, createdAt: now }]
      : [...versions],
  };
}
export const money = (n: number) => `৳${n.toLocaleString("en-BD")}`;
export const dateLabel = (date: string) =>
  new Date(date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Dhaka",
  });
