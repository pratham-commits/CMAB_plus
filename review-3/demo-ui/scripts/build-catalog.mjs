#!/usr/bin/env node
/**
 * Scan Review I/II/III session trees, pick one representative round per cell,
 * downsample timelines, and write public/catalog.json + public/sessions/*.json
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEMO_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(DEMO_ROOT, "../..");
const PUBLIC = path.join(DEMO_ROOT, "public");
const SESSIONS_OUT = path.join(PUBLIC, "sessions");
const CATALOG_OUT = path.join(PUBLIC, "catalog.json");

const REBUFFER_THRESH = 0.05;
const SAMPLE_HZ = 2; // downsample wall-clock Hz for browser

const SESSION_RE = /^(abr\w+)-.*-target-latency-(\d+)s-duration-(\d+)-bitrate-variable-(\d+)$/;

const PLAYER_MAP = {
  abrCMAB: "old CMAB",
  abrCMABPlus: "CMAB+",
  abrL2A: "L2A",
  abrDynamic: "Dynamic",
  abrLoLP: "LoLP",
};

const PHASE1_ROOTS = [
  path.join(
    process.env.HOME || "",
    "BITS/ACN/Project/review 1/mmsys24-starlink-livestreaming/figures/emulation"
  ),
];

const PHASE2_CANONICAL = path.join(
  REPO_ROOT,
  "review-ii-bbr-extension/deliverables/bbr-clock-160-deliverable-20261018-0535/figures/emulation-bbr-clock"
);
const PHASE2_FAULTY = path.join(
  REPO_ROOT,
  "review-ii-bbr-extension/BBR-Review-II-Deliverable/data/emulation-bbr"
);

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function trimValues(values) {
  return values.length >= 10 ? values.slice(Math.floor(values.length / 5)) : values;
}

function metricsFromSession(sessionDir) {
  const buffer = Object.values(readJson(path.join(sessionDir, "buffer.json"))).map(Number);
  const latency = Object.values(readJson(path.join(sessionDir, "playback_latency.json"))).map(
    Number
  );
  const bitrates = Object.values(readJson(path.join(sessionDir, "bitrates.json")))
    .map(Number)
    .filter((v) => v > 0);

  const bufT = trimValues(buffer);
  const latT = trimValues(latency);
  const brT = trimValues(bitrates);
  const rebuffer =
    bufT.length === 0
      ? 0
      : (100 * bufT.filter((v) => v <= REBUFFER_THRESH).length) / bufT.length;
  const mean = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);
  return {
    latency_s: mean(latT),
    rebuffer_pct: rebuffer,
    bitrate_kbps: mean(brT),
  };
}

function downsampleSession(sessionDir) {
  const bufferObj = readJson(path.join(sessionDir, "buffer.json"));
  const bitrateObj = readJson(path.join(sessionDir, "bitrates.json"));
  const latencyObj = readJson(path.join(sessionDir, "playback_latency.json"));
  const keys = Object.keys(bufferObj).sort();
  if (keys.length === 0) {
    return { t0: null, duration_s: 0, samples: [] };
  }
  const t0 = Date.parse(keys[0]);
  const samples = [];
  let nextEmit = 0;
  const step = 1 / SAMPLE_HZ;
  for (const key of keys) {
    const t = (Date.parse(key) - t0) / 1000;
    if (t + 1e-9 < nextEmit && samples.length > 0) continue;
    samples.push({
      t: Math.round(t * 1000) / 1000,
      buffer: Number(bufferObj[key] ?? 0),
      bitrate: Number(bitrateObj[key] ?? 0),
      latency: Number(latencyObj[key] ?? 0),
    });
    nextEmit = t + step;
  }
  const duration_s = samples.length ? samples[samples.length - 1].t : 0;
  return { t0: keys[0], duration_s, samples };
}

function listSessions(root) {
  if (!fs.existsSync(root)) return [];
  const found = [];
  const walk = (dir) => {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const ent of entries) {
      if (!ent.isDirectory()) continue;
      // skip macOS junk accidentally extracted into clock-nonreg-bbr
      if (
        ["Applications", "Library", "System", "Users", "etc", "tmp", "var", "home"].includes(
          ent.name
        )
      ) {
        continue;
      }
      const full = path.join(dir, ent.name);
      const m = ent.name.match(SESSION_RE);
      if (m && fs.existsSync(path.join(full, "buffer.json"))) {
        const [, abr, target, duration, round] = m;
        if (Number(duration) !== 300) continue;
        found.push({
          path: full,
          abr,
          player: PLAYER_MAP[abr] || abr,
          target_s: Number(target),
          round: Number(round),
          duration_s: Number(duration),
        });
      } else {
        walk(full);
      }
    }
  };
  walk(root);
  return found;
}

function pickRepresentative(sessions, playerLabel) {
  const pool = sessions.filter((s) => s.player === playerLabel);
  if (!pool.length) return null;
  pool.sort((a, b) => a.round - b.round);
  const round0 = pool.find((s) => s.round === 0);
  return round0 || pool[0];
}

function slug(...parts) {
  return parts
    .map((p) =>
      String(p)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "")
    )
    .filter(Boolean)
    .join("__");
}

function materializePlayer(cellId, playerLabel, session) {
  if (!session) {
    return {
      player: playerLabel,
      status: "missing",
      note: "No local session JSON for this player",
      metrics: null,
      timeline: null,
    };
  }
  const metrics = metricsFromSession(session.path);
  const timeline = downsampleSession(session.path);
  const fileId = slug(cellId, playerLabel);
  const outRel = `sessions/${fileId}.json`;
  const outAbs = path.join(PUBLIC, outRel);
  ensureDir(path.dirname(outAbs));
  fs.writeFileSync(
    outAbs,
    JSON.stringify({
      session: path.basename(session.path),
      source: path.relative(REPO_ROOT, session.path),
      round: session.round,
      metrics,
      ...timeline,
    })
  );
  return {
    player: playerLabel,
    status: "ok",
    round: session.round,
    session: path.basename(session.path),
    source: path.relative(REPO_ROOT, session.path),
    metrics,
    timeline: outRel,
  };
}

function makeCell({
  id,
  phase,
  family,
  label,
  transport,
  axis,
  axisValue,
  players,
  sessions,
  note,
  placeholder,
}) {
  const wanted = players || ["old CMAB", "CMAB+", "L2A"];
  const playerPayload = {};
  for (const p of wanted) {
    playerPayload[p] = materializePlayer(id, p, pickRepresentative(sessions, p));
  }
  const anyOk = Object.values(playerPayload).some((p) => p.status === "ok");
  return {
    id,
    phase,
    family,
    label,
    transport: transport || null,
    axis: axis || null,
    axisValue: axisValue ?? null,
    note: note || null,
    placeholder: Boolean(placeholder) || !anyOk,
    players: playerPayload,
  };
}

function buildPhase3() {
  const cells = [];
  const R3 = path.join(REPO_ROOT, "review-3/data");

  // Capacity 8/4/1 × CUBIC/BBR
  for (const cc of ["cubic", "bbr"]) {
    for (const cap of [8, 4, 1]) {
      const root = path.join(R3, `capacity-${cc}`, `emulation-capacity-${cc}-${cap}mbit`);
      const sessions = listSessions(root);
      cells.push(
        makeCell({
          id: `p3-capacity-${cc}-${cap}mbit`,
          phase: 3,
          family: "capacity",
          label: `Capacity ${cap} Mbit · ${cc.toUpperCase()}`,
          transport: cc.toUpperCase(),
          axis: "capacity_mbit",
          axisValue: cap,
          sessions,
        })
      );
    }
  }

  // Clock non-reg targets 3/4/5/6 × CUBIC/BBR
  for (const cc of ["cubic", "bbr"]) {
    const root =
      cc === "cubic"
        ? path.join(R3, "clock-nonreg-cubic", "emulation-clock-nonreg-cubic")
        : path.join(R3, "clock-nonreg-bbr");
    const all = listSessions(root);
    for (const target of [3, 4, 5, 6]) {
      const sessions = all.filter((s) => s.target_s === target);
      cells.push(
        makeCell({
          id: `p3-clock-${cc}-t${target}`,
          phase: 3,
          family: "clock-nonreg",
          label: `Clock non-reg · ${target}s · ${cc.toUpperCase()}`,
          transport: cc.toUpperCase(),
          axis: "target_s",
          axisValue: target,
          sessions,
        })
      );
    }
  }

  // 4 Mbit targets 3/4/5/6 × CUBIC/BBR
  for (const cc of ["cubic", "bbr"]) {
    const root = path.join(R3, `capacity-4mbit-targets-${cc}`);
    const all = listSessions(root);
    for (const target of [3, 4, 5, 6]) {
      const sessions = all.filter((s) => s.target_s === target);
      cells.push(
        makeCell({
          id: `p3-4mbit-${cc}-t${target}`,
          phase: 3,
          family: "capacity-4mbit-targets",
          label: `4 Mbit targets · ${target}s · ${cc.toUpperCase()}`,
          transport: cc.toUpperCase(),
          axis: "target_s",
          axisValue: target,
          sessions,
        })
      );
    }
  }

  // Trace targets (stall-guard ON) 3/4/5/6 × CUBIC/BBR
  for (const cc of ["cubic", "bbr"]) {
    const root = path.join(R3, `trace-targets-${cc}`);
    const all = listSessions(root);
    for (const target of [3, 4, 5, 6]) {
      const sessions = all.filter((s) => s.target_s === target);
      cells.push(
        makeCell({
          id: `p3-trace-${cc}-t${target}`,
          phase: 3,
          family: "trace-targets",
          label: `Trace · ${target}s · ${cc.toUpperCase()}`,
          transport: cc.toUpperCase(),
          axis: "target_s",
          axisValue: target,
          sessions,
          note: "Canonical stall-guard-on trace matrix",
        })
      );
    }
  }

  // Stall-guard spots tab: clock / 4mbit / trace × cubic/bbr
  // Full multi-target re-runs under stall guard were skipped for clock/4mbit;
  // wire representative sessions from matching trees and flag the gap.
  for (const cc of ["cubic", "bbr"]) {
    const spotDefs = [
      {
        spot: "clock",
        root:
          cc === "cubic"
            ? path.join(R3, "clock-nonreg-cubic", "emulation-clock-nonreg-cubic")
            : path.join(R3, "clock-nonreg-bbr"),
        note:
          "Spot representation from clock-nonreg tree (full stall-guard rematrix skipped; spots held).",
        target: 3,
      },
      {
        spot: "4mbit",
        root: path.join(R3, `capacity-4mbit-targets-${cc}`),
        note:
          "Spot representation from 4 Mbit targets tree (full stall-guard rematrix skipped; spots held).",
        target: 3,
      },
      {
        spot: "trace",
        root: path.join(R3, `trace-targets-${cc}`),
        note: "Canonical stall-guard-on trace data (3 s spot).",
        target: 3,
      },
    ];
    for (const def of spotDefs) {
      const sessions = listSessions(def.root).filter((s) => s.target_s === def.target);
      cells.push(
        makeCell({
          id: `p3-stallguard-${def.spot}-${cc}`,
          phase: 3,
          family: "stall-guard-spots",
          label: `Stall-guard spot · ${def.spot} · ${cc.toUpperCase()}`,
          transport: cc.toUpperCase(),
          axis: "spot",
          axisValue: def.spot,
          sessions,
          note: def.note,
        })
      );
    }
  }

  return cells;
}

function buildPhase2() {
  const cells = [];
  const canonical = listSessions(PHASE2_CANONICAL);
  const faulty = listSessions(PHASE2_FAULTY);
  const phase2Players = ["old CMAB", "L2A", "Dynamic", "LoLP"];

  for (const target of [3, 4, 5, 6]) {
    cells.push(
      makeCell({
        id: `p2-bbr-clock-t${target}`,
        phase: 2,
        family: "bbr-clock-canonical",
        label: `BBR clock (canonical) · ${target}s`,
        transport: "BBR",
        axis: "target_s",
        axisValue: target,
        players: phase2Players,
        sessions: canonical.filter((s) => s.target_s === target),
        note: canonical.length
          ? "Review II canonical SHAPER=clock (1017-0606)"
          : "Canonical BBR clock tree missing locally",
        placeholder: !canonical.length,
      })
    );
  }

  // Faulty vs fixed contrast at 3s if faulty data exists
  if (faulty.length) {
    cells.push(
      makeCell({
        id: "p2-bbr-faulty-trace-t3",
        phase: 2,
        family: "bbr-faulty-vs-fixed",
        label: "BBR faulty TRACE shaper · 3s (appendix)",
        transport: "BBR",
        axis: "target_s",
        axisValue: 3,
        players: phase2Players,
        sessions: faulty.filter((s) => s.target_s === 3),
        note: "Superseded SHAPER=trace run (1010-0432) — appendix contrast only",
      })
    );
    cells.push(
      makeCell({
        id: "p2-bbr-fixed-clock-t3",
        phase: 2,
        family: "bbr-faulty-vs-fixed",
        label: "BBR fixed CLOCK shaper · 3s",
        transport: "BBR",
        axis: "target_s",
        axisValue: 3,
        players: phase2Players,
        sessions: canonical.filter((s) => s.target_s === 3),
        note: "Canonical clock fix for side-by-side contrast with faulty TRACE",
      })
    );
  }

  return cells;
}

function buildPhase1() {
  const cells = [];
  let root = null;
  for (const candidate of PHASE1_ROOTS) {
    if (fs.existsSync(candidate)) {
      root = candidate;
      break;
    }
  }
  const phase1Players = ["old CMAB", "L2A", "Dynamic", "LoLP"];
  if (!root) {
    for (const target of [3, 4, 5, 6]) {
      cells.push(
        makeCell({
          id: `p1-cubic-clock-t${target}`,
          phase: 1,
          family: "cubic-clock",
          label: `Review I CUBIC clock · ${target}s`,
          transport: "CUBIC",
          axis: "target_s",
          axisValue: target,
          players: phase1Players,
          sessions: [],
          note:
            "Review I raw JSON not in this repo. Expected at ~/BITS/ACN/Project/review 1/.../figures/emulation",
          placeholder: true,
        })
      );
    }
    return cells;
  }

  const all = listSessions(root);
  for (const target of [3, 4, 5, 6]) {
    cells.push(
      makeCell({
        id: `p1-cubic-clock-t${target}`,
        phase: 1,
        family: "cubic-clock",
        label: `Review I CUBIC clock · ${target}s`,
        transport: "CUBIC",
        axis: "target_s",
        axisValue: target,
        players: phase1Players,
        sessions: all.filter((s) => s.target_s === target),
        note: `Wired from ${root} (prefix 0929-1424). CMAB+ did not exist in Review I.`,
      })
    );
  }
  return cells;
}

function main() {
  ensureDir(SESSIONS_OUT);
  // clear old sessions to avoid stale files
  for (const f of fs.readdirSync(SESSIONS_OUT)) {
    if (f.endsWith(".json")) fs.unlinkSync(path.join(SESSIONS_OUT, f));
  }

  const cells = [...buildPhase1(), ...buildPhase2(), ...buildPhase3()];
  const wired = cells.filter((c) => !c.placeholder).length;
  const placeholders = cells.filter((c) => c.placeholder).length;
  const sessionFiles = fs.readdirSync(SESSIONS_OUT).filter((f) => f.endsWith(".json")).length;

  const catalog = {
    generated_at: new Date().toISOString(),
    repo_root: REPO_ROOT,
    metrics: {
      trim: "drop first 20% of samples",
      rebuffer: "fraction of post-trim buffer ≤ 0.05 s",
      bitrate: "mean of post-trim positive bitrates",
      latency: "mean of post-trim playback_latency",
    },
    handover: {
      period_s: 15,
      slots_within_minute: [12, 27, 42, 57],
      description:
        "Paper LEO clock slots are wall-clock seconds {12,27,42,57} each minute (15 s period).",
    },
    video: "video/sports.mp4",
    summary: { cells: cells.length, wired, placeholders, session_timelines: sessionFiles },
    phases: [
      {
        id: 1,
        name: "Phase 1 / Review I",
        families: ["cubic-clock"],
      },
      {
        id: 2,
        name: "Phase 2 / Review II",
        families: ["bbr-clock-canonical", "bbr-faulty-vs-fixed"],
      },
      {
        id: 3,
        name: "Phase 3 / Review III",
        families: [
          "capacity",
          "clock-nonreg",
          "capacity-4mbit-targets",
          "trace-targets",
          "stall-guard-spots",
        ],
      },
    ],
    cells,
  };

  fs.writeFileSync(CATALOG_OUT, JSON.stringify(catalog, null, 2));
  console.log(
    `Catalog: ${cells.length} cells (${wired} wired, ${placeholders} placeholder), ${sessionFiles} timelines → ${path.relative(DEMO_ROOT, CATALOG_OUT)}`
  );
}

main();
