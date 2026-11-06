/**
 * CMAB+ decision helpers (pure, unit-tested).
 *
 * Hardened mode:
 *   - during the same post-handover window, probes the highest feasible rung
 *     (bitrate <= safe throughput), never the absolute top of the ladder
 *   - when the current rung is faster than measured throughput, the choice steps
 *     down one rung and cannot rise on that decision
 *   - otherwise the throughput-clamped suggestion is used, including a climb to the
 *     highest feasible rung. Being a little over the latency target is not a cut
 *   - an upward switch that was cut down to safe throughput uses DEFAULT
 *     priority. A downward switch stays STRONG, including when the buffer is thin
 *   - a stall guard, separate from latency: when the playback buffer is empty,
 *     hold the bottom rung and do not climb until the buffer has stayed healthy
 *     for a long run of decisions. A healthy buffer leaves this guard off, so the
 *     paper clock and a flat 4 Mbit link keep the throughput clamp.
 *
 * Throughput unit: kbps, same as dash.js getSafeAverageThroughput / bitrateList.bandwidth/1000.
 */

export const BUFFER_FLOOR_SEC = 0.5;

// Same threshold as the reported rebuffer ratio. Startup (quality still -1) does not count.
export const STALL_BUFFER_SEC = 0.05;
// Leave the guard only after the buffer has stayed at or above this level
// for a long stretch. Three decisions was enough to climb back between
// Starlink loss spikes.
export const STALL_RECOVER_BUFFER_SEC = 1.0;
export const STALL_RECOVER_DECISIONS = 12;
// Cap uses the worst sample in this window, not the single latest download.
export const STALL_WORST_WINDOW = 8;

// A healthy player sits a little above the target (L2A ~3.1 s at a 3 s target).
// Stepping down for any latency above the target walks the ladder to the bottom and stays there.
export const LATENCY_LATE_MARGIN_SEC = 1.0;

/**
 * @param {boolean} hardened
 * @param {number} decisionsAlreadyInSlot
 * @param {number} armCount
 * @param {number} linTsArm
 * @returns {number}
 */
export function shouldForceMaxArm(hardened, decisionsAlreadyInSlot, armCount) {
    return !hardened && armCount > 1 && decisionsAlreadyInSlot < armCount - 1;
}

/**
 * CMAB+ fills the same post-handover window as the paper, but the probe target
 * is maxFeasible (kbps <= safe throughput), not the top ladder index.
 *
 * @param {boolean} hardened
 * @param {number} decisionsAlreadyInSlot
 * @param {number} armCount
 * @returns {boolean}
 */
export function shouldProbeFeasibleArm(hardened, decisionsAlreadyInSlot, armCount) {
    return !!hardened && armCount > 1 && decisionsAlreadyInSlot < armCount - 1;
}

export function chooseSuggestedArm(hardened, decisionsAlreadyInSlot, armCount, linTsArm, maxFeasible) {
    if (shouldForceMaxArm(hardened, decisionsAlreadyInSlot, armCount)) {
        return Math.max(0, armCount - 1);
    }
    if (shouldProbeFeasibleArm(hardened, decisionsAlreadyInSlot, armCount) && Number.isFinite(maxFeasible)) {
        return clampIndex(maxFeasible, armCount);
    }
    return clampIndex(linTsArm, armCount);
}

/**
 * Highest ladder index whose bitrate (kbps) is <= throughputKbps.
 * Non-finite or non-positive throughput maps to arm 0.
 *
 * @param {Array<{bandwidth: number}>} bitrateList
 * @param {number} throughputKbps
 * @returns {number}
 */
export function maxFeasibleArm(bitrateList, throughputKbps) {
    if (!bitrateList || bitrateList.length === 0) {
        return 0;
    }
    if (!Number.isFinite(throughputKbps) || throughputKbps <= 0) {
        return 0;
    }
    let idx = 0;
    for (let i = 0; i < bitrateList.length; i++) {
        const kbps = bitrateList[i].bandwidth / 1000.0;
        if (kbps <= throughputKbps) {
            idx = i;
        }
    }
    return idx;
}

/**
 * @param {number} suggestedArm
 * @param {Array<{bandwidth: number}>} bitrateList
 * @param {number} throughputKbps
 * @param {boolean} hardened
 * @returns {{arm: number, clamped: boolean, maxFeasible: number}}
 */
export function applyFeasibilityClamp(suggestedArm, bitrateList, throughputKbps, hardened) {
    const armCount = bitrateList ? bitrateList.length : 0;
    const suggested = clampIndex(suggestedArm, armCount);
    if (!hardened) {
        return { arm: suggested, clamped: false, maxFeasible: suggested };
    }
    const maxFeasible = maxFeasibleArm(bitrateList, throughputKbps);
    const arm = Math.min(suggested, maxFeasible);
    return { arm, clamped: arm !== suggested, maxFeasible };
}

/**
 * Live latency is late when it is more than LATENCY_LATE_MARGIN_SEC above the target.
 * A few tenths over the target is the normal operating point, not a reason to step down.
 *
 * @param {number} currentLiveLatency
 * @param {number} targetLatencySec
 * @returns {boolean}
 */
export function isLatencyLate(currentLiveLatency, targetLatencySec) {
    const live = Number(currentLiveLatency);
    const target = Number(targetLatencySec);
    return Number.isFinite(live) && Number.isFinite(target) && target > 0 && live > target + LATENCY_LATE_MARGIN_SEC;
}

/**
 * True when the rung already playing is faster than measured throughput.
 * An unknown quality (-1) or a non-positive bitrate does not count.
 *
 * @param {number} currentBitrateKbps
 * @param {number} throughputKbps
 * @param {number} currentQuality
 * @returns {boolean}
 */
export function isCurrentAboveThroughput(currentBitrateKbps, throughputKbps, currentQuality) {
    const quality = Number(currentQuality);
    const current = Number(currentBitrateKbps);
    const throughput = Number(throughputKbps);
    return Number.isFinite(quality) && quality >= 0
        && Number.isFinite(current) && current > 0
        && Number.isFinite(throughput)
        && current > throughput;
}

/**
 * Above throughput: one rung down, and no rise. Otherwise the throughput-clamped
 * suggestion stands, including a climb to the feasible rung. A suggestion below
 * the current quality is kept.
 *
 * @param {number} arm
 * @param {number} currentQuality
 * @param {number} armCount
 * @param {boolean} aboveThroughput
 * @returns {{arm: number, steppedDown: boolean}}
 */
export function applyLatencyStep(arm, currentQuality, armCount, aboveThroughput) {
    const chosen = clampIndex(arm, armCount);
    if (!aboveThroughput || !Number.isFinite(Number(currentQuality))) {
        return { arm: chosen, steppedDown: false };
    }
    const current = clampIndex(currentQuality, armCount);
    const capped = Math.min(chosen, Math.max(0, current - 1));
    return { arm: capped, steppedDown: capped !== chosen };
}

/**
 * DEFAULT only for an upward switch that the throughput clamp reduced.
 * Downward switches stay STRONG so a late player can leave a high rung quickly.
 *
 * @param {boolean} hardened
 * @param {boolean} clamped
 * @param {{STRONG: number, DEFAULT: number}} priority
 * @param {number} nextQuality
 * @param {number} currentQuality
 * @returns {{priority: number, reason: string}}
 */
export function createStallGuardState() {
    return { active: false, healthyDecisions: 0 };
}

/**
 * Enter when a real quality is playing and the buffer is at or below STALL_BUFFER_SEC.
 * Leave only after STALL_RECOVER_DECISIONS decisions with buffer >= STALL_RECOVER_BUFFER_SEC.
 * Latency is not an input. An unknown buffer does not change the guard.
 *
 * @param {{active: boolean, healthyDecisions: number}} state
 * @param {number} bufferLevelSec
 * @param {number} currentQuality
 * @returns {{active: boolean, healthyDecisions: number}}
 */
export function updateStallGuard(state, bufferLevelSec, currentQuality) {
    const next = {
        active: !!(state && state.active),
        healthyDecisions: state && Number.isFinite(state.healthyDecisions) ? state.healthyDecisions : 0,
    };
    const buffer = Number(bufferLevelSec);
    if (!Number.isFinite(buffer)) {
        return next;
    }
    const quality = Number(currentQuality);
    const playing = Number.isFinite(quality) && quality >= 0;
    if (playing && buffer <= STALL_BUFFER_SEC) {
        return { active: true, healthyDecisions: 0 };
    }
    if (!next.active) {
        return next;
    }
    if (buffer >= STALL_RECOVER_BUFFER_SEC) {
        next.healthyDecisions += 1;
        if (next.healthyDecisions >= STALL_RECOVER_DECISIONS) {
            return { active: false, healthyDecisions: 0 };
        }
        return next;
    }
    next.healthyDecisions = 0;
    return next;
}

/**
 * Lowest finite sample. An empty list is missing data, not zero throughput.
 *
 * @param {Array<number>} samplesKbps
 * @returns {number}
 */
export function worstRecentThroughput(samplesKbps) {
    if (!samplesKbps || samplesKbps.length === 0) {
        return Number.NaN;
    }
    let worst = Number.POSITIVE_INFINITY;
    let found = false;
    for (let i = 0; i < samplesKbps.length; i++) {
        const sample = Number(samplesKbps[i]);
        if (!Number.isFinite(sample)) {
            continue;
        }
        found = true;
        if (sample < worst) {
            worst = sample;
        }
    }
    return found ? worst : Number.NaN;
}

/**
 * While the guard is on, hold arm 0. The worst-throughput number is ignored:
 * a stall means the smoothed estimate was already too high. The guard is off
 * when the buffer is healthy, so this does not apply on the paper clock or a
 * flat 4 Mbit link.
 *
 * @param {number} arm
 * @param {Array<{bandwidth: number}>} bitrateList
 * @param {number} worstThroughputKbps
 * @param {boolean} guardActive
 * @param {number} currentQuality
 * @returns {{arm: number, stalled: boolean, dropped: boolean}}
 */
export function applyStallGuard(arm, bitrateList, worstThroughputKbps, guardActive, currentQuality) {
    const armCount = bitrateList ? bitrateList.length : 0;
    const chosen = clampIndex(arm, armCount);
    if (!guardActive) {
        return { arm: chosen, stalled: false, dropped: false };
    }
    return { arm: 0, stalled: true, dropped: chosen !== 0 };
}

export function chooseSwitchPriority(hardened, clamped, priority, nextQuality, currentQuality) {
    const upward = Number.isFinite(Number(nextQuality))
        && Number.isFinite(Number(currentQuality))
        && Number(nextQuality) > Number(currentQuality);
    if (hardened && clamped && upward) {
        return { priority: priority.DEFAULT, reason: 'CMAB+ clamped upward switch' };
    }
    return { priority: priority.STRONG, reason: 'Switch bitrate based on CMAB' };
}

function clampIndex(arm, armCount) {
    if (!armCount) {
        return 0;
    }
    const n = Number(arm);
    if (!Number.isFinite(n)) {
        return 0;
    }
    const rounded = Math.round(n);
    if (rounded < 0) {
        return 0;
    }
    if (rounded > armCount - 1) {
        return armCount - 1;
    }
    return rounded;
}
