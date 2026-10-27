/**
 * CMAB+ decision helpers (pure, unit-tested).
 *
 * Hardened mode:
 *   - does not force the top ladder rung after a handover timeslot
 *   - never requests a rung above safe throughput (already × bandwidthSafetyFactor)
 *   - drops STRONG priority when the arm was clamped or the buffer is thin
 *
 * Throughput unit: kbps, same as dash.js getSafeAverageThroughput / bitrateList.bandwidth/1000.
 */

export const BUFFER_FLOOR_SEC = 0.5;

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

export function chooseSuggestedArm(hardened, decisionsAlreadyInSlot, armCount, linTsArm) {
    if (shouldForceMaxArm(hardened, decisionsAlreadyInSlot, armCount)) {
        return Math.max(0, armCount - 1);
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
 * @param {boolean} hardened
 * @param {boolean} clamped
 * @param {number|null} bufferLevelSec
 * @param {{STRONG: number, DEFAULT: number}} priority
 * @returns {{priority: number, reason: string}}
 */
export function chooseSwitchPriority(hardened, clamped, bufferLevelSec, priority) {
    const bufferUnsafe = Number.isFinite(bufferLevelSec) && bufferLevelSec < BUFFER_FLOOR_SEC;
    if (hardened && clamped) {
        return { priority: priority.DEFAULT, reason: 'CMAB+ clamped to safe throughput' };
    }
    if (hardened && bufferUnsafe) {
        return { priority: priority.DEFAULT, reason: 'CMAB+ thin buffer' };
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
