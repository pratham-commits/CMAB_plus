import type { ReactNode } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

/** Inline / block math via KaTeX. Source of truth: review-3/ALGORITHM.md */
function Math({ tex, block = false }: { tex: string; block?: boolean }) {
  const html = katex.renderToString(tex, {
    throwOnError: false,
    displayMode: block,
    strict: "ignore",
  });
  return (
    <span
      className={block ? "algo-math algo-math--block" : "algo-math"}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function Kw({ children }: { children: ReactNode }) {
  return <span className="algo-kw">{children}</span>;
}

type AlgoLine = {
  n: number;
  indent?: number;
  content: ReactNode;
  comment?: ReactNode;
};

function AlgorithmBox({
  number,
  title,
  input,
  output,
  lines,
}: {
  number: number;
  title: string;
  input: ReactNode;
  output: ReactNode;
  lines: AlgoLine[];
}) {
  return (
    <figure className="algo-box" aria-labelledby={`algo-box-${number}`}>
      <figcaption className="algo-box__caption" id={`algo-box-${number}`}>
        <span className="algo-box__label">Algorithm {number}</span>
        <span className="algo-box__name">{title}</span>
      </figcaption>
      <div className="algo-box__io">
        <p>
          <Kw>Input:</Kw> {input}
        </p>
        <p>
          <Kw>Output:</Kw> {output}
        </p>
      </div>
      <ol className="algo-box__lines">
        {lines.map((line) => (
          <li
            key={line.n}
            className="algo-box__line"
            style={{ ["--indent" as string]: String(line.indent ?? 0) }}
            value={line.n}
          >
            <span className="algo-box__num" aria-hidden="true">
              {line.n}
            </span>
            <span className="algo-box__stmt">
              {line.content}
              {line.comment ? (
                <span className="algo-box__comment">▷ {line.comment}</span>
              ) : null}
            </span>
          </li>
        ))}
      </ol>
    </figure>
  );
}

const NOTATION = [
  {
    symbol: "A",
    tex: "A = \\{0,\\ldots,|A|-1\\}",
    meaning:
      "Quality ladder indices. Higher index = higher bitrate (≈300…6000 kbps on livesim).",
  },
  {
    symbol: "r_i",
    tex: "r_i",
    meaning: "Bitrate of arm i, in kbps.",
  },
  {
    symbol: "T̂",
    tex: "\\hat{T}",
    meaning:
      "dash.js getSafeAverageThroughput (kbps, already ×0.9). Do not scale again.",
  },
  {
    symbol: "q",
    tex: "q",
    meaning: "Quality already playing (index in A); r_q is its bitrate.",
  },
  {
    symbol: "n",
    tex: "n",
    meaning:
      "ABR decisions so far in the current 15 s slot ({12, 27, 42, 57} wall-clock).",
  },
  {
    symbol: "i★",
    tex: "i^{\\star}",
    meaning: (
      <>
        Feasible top rung: <Math tex="i^{\star}=\max\{i\in A:r_i\le\hat{T}\}" /> (arm 0 if{" "}
        <Math tex="\hat{T}" /> missing or ≤0).
      </>
    ),
  },
];

const OLD_CMAB_LINES: AlgoLine[] = [
  {
    n: 1,
    content: (
      <>
        <Kw>if</Kw> <Math tex="n < |A|-1" /> <Kw>then</Kw>
      </>
    ),
  },
  {
    n: 2,
    indent: 1,
    content: (
      <>
        <Math tex="a \leftarrow |A|-1" />
      </>
    ),
    comment: "force top rung",
  },
  {
    n: 3,
    content: <Kw>else</Kw>,
  },
  {
    n: 4,
    indent: 1,
    content: (
      <>
        <Math tex="a \leftarrow" /> LinTS.Select()
      </>
    ),
  },
  {
    n: 5,
    content: <Kw>end if</Kw>,
  },
  {
    n: 6,
    content: (
      <>
        priority <Math tex="\leftarrow" /> STRONG
      </>
    ),
  },
  {
    n: 7,
    content: (
      <>
        play <Math tex="a" />; record reward; <Math tex="n \leftarrow n+1" />
      </>
    ),
  },
  {
    n: 8,
    content: (
      <>
        <Kw>return</Kw> <Math tex="a" />, priority
      </>
    ),
  },
];

const CMAB_PLUS_LINES: AlgoLine[] = [
  {
    n: 1,
    content: (
      <>
        <Kw>if</Kw> <Math tex="\hat{T}" /> is missing or <Math tex="\hat{T} \le 0" />{" "}
        <Kw>then</Kw>
      </>
    ),
  },
  {
    n: 2,
    indent: 1,
    content: (
      <>
        <Math tex="i^{\star} \leftarrow 0" />
      </>
    ),
  },
  {
    n: 3,
    content: <Kw>else</Kw>,
  },
  {
    n: 4,
    indent: 1,
    content: (
      <>
        <Math tex="i^{\star} \leftarrow \max\{i \in A : r_i \le \hat{T}\}" />
      </>
    ),
  },
  {
    n: 5,
    content: <Kw>end if</Kw>,
  },
  {
    n: 6,
    content: (
      <>
        <Kw>if</Kw> <Math tex="n < |A|-1" /> <Kw>then</Kw>
      </>
    ),
    comment: "feasible probe",
  },
  {
    n: 7,
    indent: 1,
    content: (
      <>
        suggested <Math tex="\leftarrow i^{\star}" />
      </>
    ),
  },
  {
    n: 8,
    content: <Kw>else</Kw>,
  },
  {
    n: 9,
    indent: 1,
    content: (
      <>
        suggested <Math tex="\leftarrow" /> LinTS.Select()
      </>
    ),
  },
  {
    n: 10,
    content: <Kw>end if</Kw>,
  },
  {
    n: 11,
    content: (
      <>
        <Math tex="a \leftarrow \min(\mathrm{suggested},\, i^{\star})" />
      </>
    ),
    comment: "throughput clamp",
  },
  {
    n: 12,
    content: (
      <>
        clamped <Math tex="\leftarrow (a \neq \mathrm{suggested})" />
      </>
    ),
  },
  {
    n: 13,
    content: (
      <>
        <Kw>if</Kw> <Math tex="r_q > \hat{T}" /> and <Math tex="q" /> is a real quality{" "}
        <Kw>then</Kw>
      </>
    ),
    comment: "step-down",
  },
  {
    n: 14,
    indent: 1,
    content: (
      <>
        <Math tex="a \leftarrow \min(a,\, \max(0,\, q-1))" />
      </>
    ),
  },
  {
    n: 15,
    content: <Kw>end if</Kw>,
  },
  {
    n: 16,
    content: (
      <>
        <Kw>if</Kw> <Math tex="q" /> is a real quality and <Math tex="B \le 0.05" />{" "}
        <Kw>then</Kw>
      </>
    ),
  },
  {
    n: 17,
    indent: 1,
    content: (
      <>
        stall <Math tex="\leftarrow" /> <Kw>true</Kw>
      </>
    ),
  },
  {
    n: 18,
    content: <Kw>end if</Kw>,
  },
  {
    n: 19,
    content: (
      <>
        <Kw>if</Kw> stall <Kw>then</Kw>
      </>
    ),
    comment: "stall guard",
  },
  {
    n: 20,
    indent: 1,
    content: (
      <>
        <Math tex="a \leftarrow \min\!\big(a,\, q,\, \max\{i \in A : r_i \le \min(\tau_1,\ldots,\tau_8)\}\big)" />
      </>
    ),
  },
  {
    n: 21,
    content: <Kw>end if</Kw>,
  },
  {
    n: 22,
    content: (
      <>
        <Kw>if</Kw> clamped and <Math tex="a > q" /> <Kw>then</Kw>
      </>
    ),
    comment: "switch priority",
  },
  {
    n: 23,
    indent: 1,
    content: (
      <>
        priority <Math tex="\leftarrow" /> DEFAULT
      </>
    ),
  },
  {
    n: 24,
    content: <Kw>else</Kw>,
  },
  {
    n: 25,
    indent: 1,
    content: (
      <>
        priority <Math tex="\leftarrow" /> STRONG
      </>
    ),
  },
  {
    n: 26,
    content: <Kw>end if</Kw>,
  },
  {
    n: 27,
    content: (
      <>
        play <Math tex="a" />; record reward; <Math tex="n \leftarrow n+1" />
      </>
    ),
  },
  {
    n: 28,
    content: (
      <>
        <Kw>return</Kw> <Math tex="a" />, priority
      </>
    ),
  },
];

const STALL_GUARD_LINES: AlgoLine[] = [
  {
    n: 1,
    content: (
      <>
        <Kw>if</Kw> stall <Kw>then</Kw>
      </>
    ),
  },
  {
    n: 2,
    indent: 1,
    content: (
      <>
        <Kw>if</Kw> <Math tex="B \ge 1" /> <Kw>then</Kw>
      </>
    ),
  },
  {
    n: 3,
    indent: 2,
    content: (
      <>
        <Math tex="c \leftarrow c + 1" />
      </>
    ),
  },
  {
    n: 4,
    indent: 2,
    content: (
      <>
        <Kw>if</Kw> <Math tex="c \ge 12" /> <Kw>then</Kw>
      </>
    ),
  },
  {
    n: 5,
    indent: 3,
    content: (
      <>
        stall <Math tex="\leftarrow" /> <Kw>false</Kw>
      </>
    ),
  },
  {
    n: 6,
    indent: 3,
    content: (
      <>
        <Math tex="c \leftarrow 0" />
      </>
    ),
  },
  {
    n: 7,
    indent: 2,
    content: <Kw>end if</Kw>,
  },
  {
    n: 8,
    indent: 1,
    content: <Kw>else</Kw>,
  },
  {
    n: 9,
    indent: 2,
    content: (
      <>
        <Math tex="c \leftarrow 0" />
      </>
    ),
  },
  {
    n: 10,
    indent: 1,
    content: <Kw>end if</Kw>,
  },
  {
    n: 11,
    content: <Kw>end if</Kw>,
  },
  {
    n: 12,
    content: (
      <>
        <Kw>return</Kw> stall, <Math tex="c" />
      </>
    ),
  },
];

const BRIEF_RULES = [
  {
    id: 1,
    title: "Feasible probe",
    text: (
      <>
        First <Math tex="|A|-1" /> decisions of a slot request <Math tex="i^{\star}" />, not
        the ladder top. Skip LinTS in that window.
      </>
    ),
  },
  {
    id: 2,
    title: "Throughput clamp",
    text: (
      <>
        After the window, LinTS still cannot exceed <Math tex="i^{\star}" />.
      </>
    ),
  },
  {
    id: 3,
    title: "Step-down",
    text: (
      <>
        Only when <Math tex="r_q > \hat{T}" />: no rise, at most <Math tex="q-1" />. Latency
        alone does not trigger this.
      </>
    ),
  },
  {
    id: 4,
    title: "Switch priority",
    text: <>DEFAULT only for an upward switch that the clamp reduced; else STRONG.</>,
  },
  {
    id: 5,
    title: "Stall guard",
    text: (
      <>
        Off while buffer &gt; 0.05 s. When active, no rise and cap by worst of last 8
        throughputs; clears after 12 decisions with buffer ≥ 1 s.
      </>
    ),
  },
];

export function AlgorithmView() {
  return (
    <article className="algo" aria-labelledby="algo-heading">
      <header className="algo__header">
        <p className="algo__eyebrow">Formal algorithms · review-3/ALGORITHM.md</p>
        <h1 id="algo-heading">CMAB+ algorithm</h1>
        <p className="algo__lede">
          The player that produced the 4 Mbit result. Flag{" "}
          <code>cmabHardened=true</code> on <code>abrCMAB</code> only. LinTS, QoE reward,
          15 s slots, and catch-up are unchanged from Zhao &amp; Pan (MMSys &apos;24). At a
          slot boundary, reset <Math tex="n" /> and LinTS history for that slot.
        </p>
      </header>

      <section className="algo__section" aria-labelledby="algo-notation">
        <h2 id="algo-notation">Notation</h2>
        <dl className="algo-notation">
          {NOTATION.map((row) => (
            <div key={row.symbol} className="algo-notation__row">
              <dt>
                <Math tex={row.tex} />
              </dt>
              <dd>{row.meaning}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="algo__section" aria-labelledby="algo-formal">
        <h2 id="algo-formal">Algorithms</h2>
        <p className="algo__intro">
          Paper baseline first, then the full CMAB+ decision and the stall-guard helper.
        </p>

        <AlgorithmBox
          number={1}
          title="Old CMAB decision"
          input={
            <>
              ladder <Math tex="A" />, throughput <Math tex="\hat{T}" />, current quality{" "}
              <Math tex="q" />, slot decision count <Math tex="n" />, LinTS
            </>
          }
          output={
            <>
              arm <Math tex="a" />, switch priority
            </>
          }
          lines={OLD_CMAB_LINES}
        />

        <AlgorithmBox
          number={2}
          title="CMAB+ decision"
          input={
            <>
              ladder <Math tex="A" />, throughput <Math tex="\hat{T}" />, current quality{" "}
              <Math tex="q" />, slot decision count <Math tex="n" />, LinTS, buffer{" "}
              <Math tex="B" />, stall flag, recent segment throughputs{" "}
              <Math tex="\tau_1,\ldots,\tau_8" />
            </>
          }
          output={
            <>
              arm <Math tex="a" />, switch priority
            </>
          }
          lines={CMAB_PLUS_LINES}
        />

        <AlgorithmBox
          number={3}
          title="Stall-guard state update"
          input={
            <>
              buffer <Math tex="B" />, stall flag, consecutive-good counter <Math tex="c" />
            </>
          }
          output={
            <>
              stall, <Math tex="c" />
            </>
          }
          lines={STALL_GUARD_LINES}
        />
      </section>

      <section className="algo__section" aria-labelledby="algo-intuition">
        <h2 id="algo-intuition">Intuition — five rules</h2>
        <p className="algo__intro">
          Compact reading of Algorithm 2. The formal lines above are authoritative.
        </p>
        <ol className="algo-rules-brief">
          {BRIEF_RULES.map((rule) => (
            <li key={rule.id}>
              <strong>
                {rule.id}. {rule.title}.
              </strong>{" "}
              {rule.text}
            </li>
          ))}
        </ol>
      </section>

      <section className="algo__section algo__section--split" aria-labelledby="algo-not">
        <div>
          <h2 id="algo-not">What this is not</h2>
          <ul className="algo-bullets">
            <li>Not a new bandit — LinTS and the QoE reward are the paper&apos;s.</li>
            <li>
              Does not step down because live latency is 1 s over target (tried in trials
              3–7; cut bitrate on links that could still carry the current quality).
            </li>
            <li>
              Does not keep a spare gap under <Math tex="\hat{T}" /> — a rung just below
              the measurement is allowed (~888 kbps on 1 Mbit CUBIC).
            </li>
          </ul>
        </div>
        <div>
          <h2 id="algo-map">Mapping to the 4 Mbit result</h2>
          <p>
            On a 4 Mbit link, <Math tex="i^{\star}" /> is the 1500 kbps rung. Old CMAB
            (Alg. 1) still forces 6000 kbps post-handover and rebuffers. CMAB+ (Alg. 2)
            probes 1500 kbps, clamps later LinTS choices there, and lands at about
            3.54–3.62 s latency with 0% rebuffer.
          </p>
        </div>
      </section>
    </article>
  );
}
