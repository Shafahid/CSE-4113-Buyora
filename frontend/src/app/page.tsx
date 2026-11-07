import Link from "next/link";
import {
  Avatar,
  Badge,
  Brand,
  ButtonLink,
  Icon,
  ProductArt,
  ThemeToggle,
} from "@/components/ui";
import { ReactionMap } from "@/components/reaction-map";
import { personas, products } from "@/lib/demo-data";
import { Footer } from "@/components/footer";
import { LandingReveals } from "@/components/landing-reveals";
import { ScrollToTop } from "@/components/scroll-to-top";

const heroBuyers = [
  { id: "cod", label: "COD buyer" },
  { id: "budget", label: "Budget student" },
  { id: "skeptic", label: "Scam skeptic" },
  { id: "impulse", label: "Impulse buyer" },
  { id: "gift", label: "Gift buyer" },
].map((buyer) => ({
  ...buyer,
  persona: personas.find((persona) => persona.id === buyer.id)!,
}));

export default function Home() {
  return (
    <LandingReveals>
      <header className="landing-nav">
        <Brand />
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#preview">Explore a report</a>
          <Link href="/dashboard">Your workspace</Link>
        </nav>
        <div className="row">
          <ThemeToggle />
          <Link className="landing-signin" href="/login">
            Sign in
          </Link>
          <ButtonLink href="/simulate">
            Try a simulation <Icon name="arrow" size={16} />
          </ButtonLink>
        </div>
      </header>
      <main id="main-content">
        <section className="landing-hero">
          <div className="hero-glow" />
          <h1 data-landing-reveal>
            Test buyer reactions with
            <br />
            <span>AI Personas.</span>
          </h1>
          <p data-landing-reveal>
            Buyora helps Bangladeshi e-commerce sellers simulate trust,
            virality, comments, and boost readiness before publishing or
            boosting a post.
          </p>
          <div
            className="hero-buyer-personas"
            aria-label="Simulated buyer personas"
            data-landing-stagger
          >
            {heroBuyers.map((buyer) => (
              <figure key={buyer.id} data-landing-reveal>
                <Avatar persona={buyer.persona} />
                <figcaption>{buyer.label}</figcaption>
              </figure>
            ))}
          </div>
          <div className="hero-actions" data-landing-reveal>
            <ButtonLink href="/simulate">
              Run simulation <Icon name="arrow" size={18} />
            </ButtonLink>
            <ButtonLink href="/history" secondary>
              View saved reports
            </ButtonLink>
          </div>
        </section>
        <section
          className="hero-preview container"
          id="preview"
          data-landing-reveal
        >
          <div className="preview-toolbar">
            <div className="row">
              <span className="small-brand-mark" />
              <span>Agentic AI Based Simulation</span>
            </div>
            <Badge tone="blue">Sample simulation</Badge>
          </div>
          <div className="preview-body">
            <div className="preview-product">
              <div className="row spread">
                <span className="section-kicker">The product post</span>
                <Icon name="file" size={17} />
              </div>
              <ProductArt product={products[0]} />
              <h3>Nila everyday bag</h3>
              <p>A little room for your everyday.</p>
              <div className="row spread">
                <strong>৳890</strong>
                <Badge>Facebook post</Badge>
              </div>
              <div className="mini-caption">
                “Made for your laptop, your books, and other accessories.”
              </div>
            </div>
            <ReactionMap compact />
            <div className="preview-takeaway">
              <span className="section-kicker">The takeaway</span>
              <span className="large-spark">
                <Icon name="spark" size={24} />
              </span>
              <h3>
                Good Result.
                <br />A few improvaments.
              </h3>
              <p>
                Your product has a clear appeal. Make the next step easier for
                cautious buyers.
              </p>
              <div className="takeaway-line">
                <Icon name="check" size={15} />
                <span>A clear everyday use case</span>
              </div>
              <div className="takeaway-line">
                <Icon name="chat" size={15} />
                <span>Add delivery and payment details</span>
              </div>
              <Link href="/reports/sample-1" className="text-link">
                See the full picture <Icon name="arrow" size={16} />
              </Link>
            </div>
          </div>
          <div className="preview-footer">
            <span>
              <span className="status-dot" />6 buyer perspectives explored
            </span>
            <span>Illustrative demo data</span>
          </div>
        </section>
        <section className="built-for container">
          <p data-landing-reveal>Built for Bangladeshi social e-commerce.</p>
          <div data-landing-stagger>
            <span className="audience-box" data-landing-reveal>
              Facebook sellers
            </span>
            <span className="audience-box" data-landing-reveal>
              Local brands
            </span>
            <span className="audience-box" data-landing-reveal>
              Student entrepreneurs
            </span>
            <span className="audience-box" data-landing-reveal>
              Social e-commerce teams
            </span>
          </div>
        </section>
        <section className="how-section container" id="how-it-works">
          <div className="section-intro" data-landing-reveal>
            <div>
              <span className="section-kicker">How it works</span>
              <h2>
                <span className="landing-emphasis"><b>4 steps</b></span> buyer
                <br />
                simulation process
              </h2>
            </div>
            <p>
              Buyora turns a product post into an explainable simulation flow
              helping you understand how different people percieves the product.
            </p>
          </div>
          <div className="steps-grid" data-landing-stagger>
            {[
              {
                icon: "file",
                title: "Submit your post",
                text: "Add your product, price, caption, and the details buyers should know.",
              },
              {
                icon: "chat",
                title: "Simulate the personas",
                text: "Choose and customize a mix of buyer perspectives for your audience.",
              },
              {
                icon: "network",
                title: "Explore the reactions",
                text: "Compare interest, trust, questions, and purchase intent in one report.",
              },
              {
                icon: "badge-check",
                title: "Fix before boost",
                text: "Use practical suggestions to revise your post before you publish.",
              },
            ].map((s, i) => (
              <article key={s.title} data-landing-reveal>
                <div className="step-visual">
                  <span className="step-circle">
                    <span className="step-icon">
                      <Icon name={s.icon} size={27} />
                    </span>
                    <svg
                      className="step-hover-ring"
                      viewBox="0 0 100 100"
                      aria-hidden="true"
                      focusable="false"
                    >
                      <circle
                        cx="50"
                        cy="50"
                        r="47.75"
                        pathLength="100"
                        transform="rotate(-90 50 50)"
                      />
                    </svg>
                  </span>
                </div>
                <div className="step-number">
                  Step {String(i + 1).padStart(2, "0")}
                </div>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="perspective-section container">
          <div data-landing-reveal>
            <Badge tone="blue">
              <Icon name="people" size={13} /> Diverse buyer Personas
            </Badge>
            <h2>
              Each <span className="landing-emphasis">Persona</span>
              <br />
              is a <span className="landing-emphasis">unique</span> buyer
            </h2>
            <p>
              The student watching their budget. The buyer who only pays on
              delivery. The skeptic looking for a little proof. Give each
              perspective a seat at the table.
            </p>
            <ButtonLink href="/simulate">
              Meet your buyer personas <Icon name="arrow" size={17} />
            </ButtonLink>
          </div>
          <div className="perspective-cards" data-landing-stagger>
            {personas.slice(0, 3).map((p, i) => (
              <div
                className={`perspective-card card-${i}`}
                key={p.id}
                data-landing-reveal
              >
                <Avatar persona={p} />
                <div>
                  <h3>{p.role}</h3>
                  <p>
                    {
                      [
                        "“What’s the total with delivery?”",
                        "“Is cash on delivery available?”",
                        "“Can I see a real customer photo?”",
                      ][i]
                    }
                  </p>
                </div>
                <Badge tone={i === 1 ? "blue" : "amber"}>
                  {i === 1 ? "Payment" : i === 0 ? "Price fit" : "Trust"}
                </Badge>
              </div>
            ))}
          </div>
        </section>
        <section className="landing-cta container" data-landing-reveal>
          <span className="small-brand-mark" />
          <h2>
            Your products deserves
            <br />
            to reach an wider audience
          </h2>
          <p>
            Start with a draft. Leave with a clearer idea of what to improve.
          </p>
          <ButtonLink href="/simulate">
            Try your first simulation <Icon name="arrow" size={18} />
          </ButtonLink>
          <span className="cta-note">Explore our AI personas</span>
        </section>
      </main>
      <Footer />
      <ScrollToTop />
    </LandingReveals>
  );
}
