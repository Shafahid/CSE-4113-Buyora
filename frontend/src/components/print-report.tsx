import { dateLabel, dimensions, money, overall, recommendations, type Report } from "@/lib/demo-data";
import { reportInsights } from "@/lib/report-insights";
import styles from "./print-report.module.css";

export function PrintReport({ report: r }: { report: Report }) {
  const insights = reportInsights(r);
  const recs = recommendations(r);
  const complete = r.reactions.filter((reaction) => reaction.status === "complete");
  const audience = [
    ["Location", r.audience.location], ["Age range", r.audience.age],
    ["Interests", r.audience.interests], ["Payment preference", r.audience.preferences],
    ["Budget", r.audience.budget], ["Needs", r.audience.needs],
  ].filter(([, value]) => value);
  return (
    <article className={`print-report ${styles.sheet}`} aria-label="Printable simulation report">
      <header className={styles.masthead}>
        <div className={styles.brand}><span className="brand-mark" aria-hidden="true" />buyora<span>.</span></div>
        <div className={styles.documentLabel}>Buyer perspective report<br /><span>{dateLabel(r.createdAt)}</span></div>
      </header>

      <div className={styles.titleBlock}>
        <p className={styles.eyebrow}>Before you publish</p>
        <h1>{r.title}</h1>
        <p className={styles.subtitle}>{r.post.platform} · {r.product.category} · {r.language === "bn" ? "Bangla" : "English"} assessment{r.post.versionNumber ? ` · Post version ${r.post.versionNumber}` : ""}</p>
      </div>

      <div className={styles.contents} aria-label="Report contents">
        <strong>In this report</strong>
        <p>01 Assessment · 02 Publishing checklist · 03 Persona scorecard<br />04 Buyer perspectives · 05 Saved inputs{r.revised ? " · 06 Revised caption" : ""}</p>
      </div>

      <section className={styles.summary} aria-label="Report at a glance">
        <div className={styles.mainScore}>
          <span className={styles.label}>Overall persona fit</span>
          <div>{insights.score === null ? <strong className={styles.unavailable}>Unavailable</strong> : <><strong>{insights.score}</strong><span>/100</span></>}</div>
          <p>Mean of completed persona scores</p>
        </div>
        <div className={styles.summaryFinding}>
          <h2>{insights.title}</h2>
          <p>{insights.explanation}</p>
          <div className={styles.facts}>
            <div><strong>{insights.completed} / {insights.total}</strong><span>perspectives completed</span></div>
            <div><strong>{insights.failed}</strong><span>missing perspectives</span></div>
            <div><strong>{money(r.product.price)}</strong><span>saved product price</span></div>
          </div>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeading}><span>01</span><h2>What the assessment shows</h2></div>
        <p className={styles.note}>Scores use a 0–100 scale. Incomplete evaluations are excluded from every average.</p>
        <div className={styles.dimensions}>
          {dimensions.map((dimension, index) => <div className={styles.dimension} key={dimension}>
            <span>{dimension}</span>
            <span className={styles.track} aria-hidden="true"><i style={{ width: `${complete.length ? overall(r, index) : 0}%` }} /></span>
            <strong>{complete.length ? overall(r, index) : "—"}</strong>
          </div>)}
        </div>
        {insights.weakest && insights.concern && <div className={styles.concern}>
          <p className={styles.label}>Lowest scoring area · {insights.weakest.label} · {insights.weakest.score}/100</p>
          <blockquote lang={r.language}>“{insights.concern.question}”</blockquote>
          <p>{insights.concern.persona.name} · {insights.concern.persona.role}</p>
        </div>}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeading}><span>02</span><h2>Checks before you publish</h2></div>
        <p className={styles.note}>A checklist based on the saved caption and product details.</p>
        <ol className={styles.checklist}>{recs.map((rec) => <li key={rec.id}>
          <div><h3>{rec.title}</h3><p>{rec.detail}</p></div><span>{rec.priority}</span>
        </li>)}</ol>
      </section>

      <p className={styles.disclosure}>Fictional buyer perspectives, not actual customer feedback. These scores do not predict sales or reach.{r.source !== "server" ? " This is an illustrative demo report." : ""}</p>

      <section className={`${styles.section} ${styles.newPage}`}>
        <div className={styles.sectionHeading}><span>03</span><h2>Persona scorecard</h2></div>
        <p className={styles.note}>{insights.completed} of {insights.total} selected perspectives completed. A dash means no assessment was available.</p>
        <table className={styles.scorecard}>
          <colgroup><col className={styles.personaColumn} />{dimensions.map((dimension) => <col key={dimension} />)}<col /></colgroup>
          <thead><tr><th scope="col">Buyer persona</th>{dimensions.map((dimension) => <th scope="col" key={dimension}>{dimension}</th>)}<th scope="col">Overall</th></tr></thead>
          <tbody>{r.reactions.map((reaction) => <tr key={reaction.persona.id}>
            <th scope="row"><strong>{reaction.persona.name}</strong><span>{reaction.persona.role}</span>{reaction.status === "failed" && <em>Incomplete</em>}</th>
            {dimensions.map((dimension, index) => <td key={dimension}>{reaction.status === "complete" ? reaction.scores[index] : "—"}</td>)}
            <td className={styles.overall}>{reaction.status === "complete" ? reaction.score : "—"}</td>
          </tr>)}</tbody>
        </table>
        <p className={styles.note}>Overall fit is the arithmetic mean of interest, relevance, value, price fit, trust, clarity, and purchase intent. Scores describe only the selected fictional personas.{insights.failed > 0 && " Completed results are preserved. Review incomplete perspectives in Audience insights in Buyora."}</p>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeading}><span>04</span><h2>Inside each buyer’s perspective</h2></div>
        {complete.length ? complete.map((reaction, index) => <article className={styles.perspective} key={reaction.persona.id}>
          <header className={styles.personHeading}>
            <span className={styles.personNumber}>{String(index + 1).padStart(2, "0")}</span>
            <div><h3>{reaction.persona.name} <span>· {reaction.persona.role}</span></h3><p>{reaction.persona.age} · {reaction.persona.location} · {reaction.persona.budget}</p></div>
            <div className={styles.personScore}><strong>{reaction.score}<small>/100</small></strong><span>{reaction.sentiment}</span></div>
          </header>
          <p className={styles.buyerNeed}><strong>Looking for</strong> {reaction.persona.need}</p>
          <blockquote lang={r.language}>“{reaction.comment}”</blockquote>
          <dl className={styles.reasoning} lang={r.language}>
            <div><dt>Why this reaction</dt><dd>{reaction.reason}</dd></div>
            <div><dt>What works</dt><dd>{reaction.positive}</dd></div>
            {reaction.question !== reaction.comment && <div><dt>Still wants to know</dt><dd>{reaction.question}</dd></div>}
          </dl>
          {!!reaction.evidence?.length && <div className={styles.evidence}><strong>Evidence from the saved input</strong><ul lang={r.language}>{reaction.evidence.map((quote, quoteIndex) => <li key={quoteIndex}>“{quote}”</li>)}</ul></div>}
        </article>) : <p className={styles.empty}>No buyer perspective completed. Reopen this report in Buyora to review next steps for the missing assessments.</p>}
      </section>

      <section className={`${styles.section} ${styles.newPage}`}>
        <div className={styles.sectionHeading}><span>05</span><h2>The saved product & post</h2></div>
        <p className={styles.note}>The inputs used for this assessment. Later edits do not change this snapshot.</p>
        <dl className={styles.productFacts}>
          {[["Product", r.product.name], ["Category", r.product.category], ["Price", money(r.product.price)], ["Description", r.product.description], ["Features", r.product.features], ["Delivery", r.product.delivery], ["Returns", r.product.returns], ["Warranty", r.product.warranty]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value || "Not supplied"}</dd></div>)}
        </dl>
        <div className={styles.caption} lang={r.language}>
          <p className={styles.label}>Original {r.post.platform} caption{r.post.versionNumber ? ` · Version ${r.post.versionNumber}` : ""}</p>
          <h3>{r.post.headline}</h3><p>{r.post.body}</p>
          {r.post.offer && <p><strong>Offer</strong> · {r.post.offer}</p>}
          {r.post.cta && <p><strong>Call to action</strong> · {r.post.cta}</p>}
          {r.post.hashtags && <p className={styles.hashtags}>{r.post.hashtags}</p>}
        </div>
        <h3 className={styles.subheading}>Audience settings</h3>
        {audience.length ? <dl className={styles.productFacts}>{audience.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : <p className={styles.note}>No additional audience settings supplied.</p>}
      </section>

      {r.revised && <section className={`${styles.section} ${styles.revisionSection}`}>
        <div className={styles.sectionHeading}><span>06</span><h2>Your revised caption</h2></div>
        <p className={styles.note}>An editable draft. Review bracketed placeholders and verify all claims before publishing.</p>
        <div className={styles.revision} lang={r.language}>{r.revised}</div>
      </section>}

      <footer className={styles.provenance}>
        <p>Report reference · {r.id}</p>
        {r.source === "server" && <p>{r.model && `Model: ${r.model}`}{r.model && r.rulesVersion && " · "}{r.rulesVersion && `Rubric: ${r.rulesVersion}`}</p>}
        <p>Prepared with Buyora · A second perspective before your next post goes live.</p>
      </footer>
    </article>
  );
}
