import { useEffect, useMemo, useRef, useState } from "react";
import { AlgorithmView } from "./components/AlgorithmView";
import { CmabCompare } from "./components/CmabCompare";
import { HandoverTimer } from "./components/HandoverTimer";
import { PhaseExplainer } from "./components/PhaseExplainer";
import { PlayerPane } from "./components/PlayerPane";
import { ProblemsFacedView } from "./components/ProblemsFacedView";
import type { Catalog, CatalogCell } from "./lib/types";

const PLAYER_ORDER_DEFAULT = ["old CMAB", "CMAB+", "L2A"];
const ACCENTS: Record<string, string> = {
  "old CMAB": "#c45c26",
  "CMAB+": "#2f6f4e",
  L2A: "#2a5f8f",
  Dynamic: "#8a6d3b",
  LoLP: "#5c4a7a",
};

const FAMILY_LABELS: Record<string, string> = {
  "cubic-clock": "CUBIC · paper clock targets",
  "bbr-clock-canonical": "BBR · paper clock (canonical)",
  "bbr-faulty-vs-fixed": "Faulty TRACE vs fixed CLOCK",
  capacity: "Capacity sweep · 8 / 4 / 1 Mbit",
  "clock-nonreg": "Clock non-regression",
  "capacity-4mbit-targets": "4 Mbit · latency targets",
  "trace-targets": "Starlink TRACE · stall guard on",
  "stall-guard-spots": "Stall-guard spot checks",
};

const PHASE_BLURBS: Record<number, string> = {
  1: "Review I baseline · CUBIC clock matrix",
  2: "Review II · BBR clock + TRACE fix",
  3: "Review III · CMAB+ hardening + stall guard",
};

/** Top-level nav: experiment phases, Algorithm textbook, or Problems ledger. */
type NavMode = number | "algorithm" | "problems";

function unique<T>(arr: T[]): T[] {
  return [...new Set(arr)];
}

export default function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<NavMode>(3);
  const [family, setFamily] = useState("trace-targets");
  const [cellId, setCellId] = useState("p3-trace-cubic-t3");
  const [playing, setPlaying] = useState(false);
  const [demoTimeS, setDemoTimeS] = useState(0);
  const [speed, setSpeed] = useState(1);
  const tickRef = useRef<number | null>(null);
  const lastTs = useRef<number | null>(null);

  const isAlgorithm = mode === "algorithm";
  const isProblems = mode === "problems";
  const isDocMode = isAlgorithm || isProblems;
  const phase = typeof mode === "number" ? mode : 3;

  useEffect(() => {
    fetch("./catalog.json")
      .then((r) => {
        if (!r.ok) throw new Error(`catalog.json HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Catalog) => {
        setCatalog(data);
        const preferred =
          data.cells.find((c) => c.id === "p3-trace-cubic-t3") ||
          data.cells.find((c) => c.phase === 3 && c.family === "trace-targets") ||
          data.cells[0];
        if (preferred) {
          setMode(preferred.phase);
          setFamily(preferred.family);
          setCellId(preferred.id);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const phaseMeta = catalog?.phases.find((p) => p.id === phase);
  const families = phaseMeta?.families ?? [];
  const cellsInFamily = useMemo(
    () => (catalog?.cells || []).filter((c) => c.phase === phase && c.family === family),
    [catalog, phase, family]
  );
  const cell: CatalogCell | undefined = cellsInFamily.find((c) => c.id === cellId) || cellsInFamily[0];

  useEffect(() => {
    if (!cellsInFamily.length) return;
    if (!cellsInFamily.some((c) => c.id === cellId)) {
      setCellId(cellsInFamily[0].id);
    }
  }, [cellsInFamily, cellId]);

  useEffect(() => {
    if (!families.includes(family) && families[0]) {
      setFamily(families[0]);
    }
  }, [families, family]);

  const playerNames = useMemo(() => {
    if (!cell) return PLAYER_ORDER_DEFAULT;
    const names = Object.keys(cell.players);
    const preferred = PLAYER_ORDER_DEFAULT.filter((p) => names.includes(p));
    const rest = names.filter((p) => !preferred.includes(p));
    return [...preferred, ...rest];
  }, [cell]);

  const maxDuration = 300;

  // Wall-clock interval (not rAF) so demo time keeps advancing even when the
  // tab is backgrounded / throttled — pause still freezes via `playing`.
  useEffect(() => {
    if (!playing || isAlgorithm) {
      if (tickRef.current != null) window.clearInterval(tickRef.current);
      tickRef.current = null;
      lastTs.current = null;
      return;
    }
    lastTs.current = performance.now();
    tickRef.current = window.setInterval(() => {
      const now = performance.now();
      const prev = lastTs.current ?? now;
      lastTs.current = now;
      const dt = ((now - prev) / 1000) * speed;
      setDemoTimeS((t) => {
        const next = t + dt;
        if (next >= maxDuration) {
          setPlaying(false);
          return maxDuration;
        }
        return next;
      });
    }, 50);
    return () => {
      if (tickRef.current != null) window.clearInterval(tickRef.current);
      tickRef.current = null;
    };
  }, [playing, speed, maxDuration, isAlgorithm]);

  function goPhase(id: number) {
    setMode(id);
    const meta = catalog?.phases.find((p) => p.id === id);
    if (meta?.families[0]) setFamily(meta.families[0]);
    setPlaying(false);
    setDemoTimeS(0);
  }

  function goAlgorithm() {
    setMode("algorithm");
    setPlaying(false);
  }

  function goProblems() {
    setMode("problems");
    setPlaying(false);
  }

  if (error) {
    return (
      <div className="boot-error">
        <h1>Demo failed to load</h1>
        <p>{error}</p>
        <p>
          Run <code>npm run catalog</code> then <code>npm run dev</code>.
        </p>
      </div>
    );
  }

  if (!catalog || (!isDocMode && !cell)) {
    return <div className="boot-loading">Loading catalog…</div>;
  }

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead__brand">
          <span className="masthead__mark">CMAB+</span>
          <span className="masthead__sub">LEO live streaming · side-by-side ABR replay</span>
        </div>
        <nav className="phase-tabs" aria-label="Review phases">
          {catalog.phases.map((p) => (
            <button
              key={p.id}
              type="button"
              className={mode === p.id ? "is-active" : ""}
              title={PHASE_BLURBS[p.id]}
              onClick={() => goPhase(p.id)}
            >
              {p.name}
            </button>
          ))}
          <button
            type="button"
            className={isAlgorithm ? "is-active" : ""}
            title="CMAB+ textbook algorithm (rules 1–5)"
            onClick={goAlgorithm}
          >
            Algorithm
          </button>
          <button
            type="button"
            className={isProblems ? "is-active" : ""}
            title="Failures and recoveries across Reviews I–III"
            onClick={goProblems}
          >
            Problems we faced
          </button>
        </nav>
      </header>

      {isAlgorithm ? (
        <main className="stage stage--algo">
          <AlgorithmView />
        </main>
      ) : isProblems ? (
        <main className="stage stage--algo">
          <ProblemsFacedView />
        </main>
      ) : (
        <>
          <div className="control-rail">
            <div className="family-row">
              {families.map((f) => (
                <button
                  key={f}
                  type="button"
                  className={family === f ? "chip is-active" : "chip"}
                  onClick={() => {
                    setFamily(f);
                    setPlaying(false);
                    setDemoTimeS(0);
                  }}
                >
                  {FAMILY_LABELS[f] || f}
                </button>
              ))}
            </div>

            {phase === 3 && <PhaseExplainer family={family} />}

            <div className="cell-row">
              <label className="cell-select">
                <span>Session cell</span>
                <select
                  value={cell!.id}
                  onChange={(e) => {
                    setCellId(e.target.value);
                    setPlaying(false);
                    setDemoTimeS(0);
                  }}
                >
                  {cellsInFamily.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                      {c.placeholder ? " (placeholder)" : ""}
                    </option>
                  ))}
                </select>
              </label>

              <div className="transport-pill">{cell!.transport || "—"}</div>

              <div className="playback-controls">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setPlaying(true)}
                  disabled={cell!.placeholder || playing}
                >
                  Play
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setPlaying(false)}
                  disabled={!playing}
                >
                  Pause
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    setPlaying(false);
                    setDemoTimeS(0);
                  }}
                >
                  Reset
                </button>
                <label className="speed">
                  Speed
                  <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                    <option value={1}>1×</option>
                    <option value={2}>2×</option>
                    <option value={5}>5×</option>
                    <option value={10}>10×</option>
                  </select>
                </label>
                <span className="playback-hint">
                  {playing ? "Playing" : "Paused"} · t={demoTimeS.toFixed(1)}s — Pause freezes
                  here; Play resumes
                </span>
              </div>
            </div>

            <HandoverTimer demoTimeS={demoTimeS} playing={playing} />
          </div>

          <main className="stage">
            <div className={`players players--${Math.min(playerNames.length, 4)}`}>
              {playerNames.map((name) => (
                <PlayerPane
                  key={`${cell!.id}-${name}`}
                  entry={cell!.players[name]}
                  demoTimeS={demoTimeS}
                  playing={playing}
                  accent={ACCENTS[name] || "#6b7280"}
                />
              ))}
            </div>

            <aside className="cell-note">
              <div className="cell-note__title">{cell!.label}</div>
              {cell!.note && <p>{cell!.note}</p>}
              {cell!.placeholder && (
                <p className="warn">
                  This cell is scaffolded — local session JSON was missing when the catalog
                  was built.
                </p>
              )}
              <p className="fine">
                Metrics: trim first 20% · rebuffer = playback buffer ≤ 0.05 s · round{" "}
                {unique(
                  Object.values(cell!.players)
                    .map((p) => p.round)
                    .filter((r): r is number => r != null)
                ).join("/") || "—"}{" "}
                · catalog {catalog.summary.wired}/{catalog.summary.cells} wired
              </p>
            </aside>

            <CmabCompare />
          </main>
        </>
      )}
    </div>
  );
}
