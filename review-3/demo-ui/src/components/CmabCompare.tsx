/** Side-by-side old CMAB vs CMAB+ — wording from review-3/ALGORITHM.md */

const OLD_CMAB = [
  {
    id: "probe",
    title: "Post-handover probe",
    body: "After each 15 s LEO slot starts, for the first |A|−1 decisions force the top ladder rung (≈6000 kbps) at STRONG priority.",
  },
  {
    id: "lints",
    title: "Then LinTS",
    body: "After that window, LinTS picks the arm. There is no throughput cap — a 4 Mbit link can still request 6000 kbps.",
  },
  {
    id: "priority",
    title: "Switch priority",
    body: "Forced top-rung probes apply at STRONG priority so the player switches up aggressively after every handover.",
  },
];

const CMAB_PLUS = [
  {
    id: "feasible",
    title: "Feasible probe",
    highlight: true,
    body: "In the same first |A|−1 decisions, request the highest rung that still fits measured throughput T̂ — not the top of the ladder. If T̂ is missing, use arm 0.",
  },
  {
    id: "clamp",
    title: "Throughput clamp",
    highlight: true,
    body: "After the window, LinTS still cannot exceed that feasible rung i★ = max { i : r_i ≤ T̂ }.",
  },
  {
    id: "stepdown",
    title: "Step-down",
    highlight: true,
    body: "Only when the current quality is above T̂: the applied arm cannot rise, and is at most one rung down. Live latency alone does not trigger this cut.",
  },
  {
    id: "priority",
    title: "Switch priority",
    highlight: true,
    body: "DEFAULT only for an upward switch that the clamp reduced. A downward switch stays STRONG.",
  },
  {
    id: "stall",
    title: "Stall guard",
    highlight: true,
    body: "When playback buffer ≤ 0.05 s, the rung cannot rise and is capped by the worst of the last 8 segment throughputs. Guard clears after 12 decisions with buffer ≥ 1 s. Inactive on paper-clock / flat 4 Mbit spots.",
  },
];

export function CmabCompare() {
  return (
    <section className="compare" aria-labelledby="compare-heading">
      <div className="compare__intro">
        <h2 id="compare-heading">Old CMAB vs CMAB+</h2>
        <p>
          Same LinTS bandit, QoE reward, 15 s LEO slots, and catch-up controller as Zhao &amp; Pan
          (MMSys &apos;24). CMAB+ adds four hardened rules on top of the paper player.
        </p>
      </div>

      <div className="compare__grid">
        <article className="compare__col compare__col--old">
          <header>
            <h3>Old CMAB</h3>
            <p className="compare__tag">Paper baseline</p>
          </header>
          <ol className="compare__list">
            {OLD_CMAB.map((item) => (
              <li key={item.id} className="compare__item">
                <strong>{item.title}</strong>
                <span>{item.body}</span>
              </li>
            ))}
          </ol>
        </article>

        <article className="compare__col compare__col--plus">
          <header>
            <h3>CMAB+</h3>
            <p className="compare__tag">Highlighted = added / changed</p>
          </header>
          <ol className="compare__list">
            {CMAB_PLUS.map((item) => (
              <li
                key={item.id}
                className={item.highlight ? "compare__item compare__item--new" : "compare__item"}
              >
                <strong>{item.title}</strong>
                <span>{item.body}</span>
              </li>
            ))}
          </ol>
        </article>
      </div>
    </section>
  );
}
