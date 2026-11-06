import assert from 'node:assert/strict';
import {
    applyFeasibilityClamp,
    applyLatencyStep,
    applyStallGuard,
    chooseSuggestedArm,
    chooseSwitchPriority,
    createStallGuardState,
    isCurrentAboveThroughput,
    isLatencyLate,
    maxFeasibleArm,
    shouldForceMaxArm,
    shouldProbeFeasibleArm,
    STALL_RECOVER_DECISIONS,
    updateStallGuard,
    worstRecentThroughput,
} from '../dash.js/src/streaming/rules/abr/cmab/cmabPlusPolicy.js';

const ladder = [200, 500, 1000, 2000, 4000, 6000].map((kbps) => ({ bandwidth: kbps * 1000 }));
const STRONG = 1;
const DEFAULT = 0.5;
const priority = { STRONG, DEFAULT };

// Old CMAB forces the top arm until |A|-1 decisions exist.
assert.equal(shouldForceMaxArm(false, 0, 8), true);
assert.equal(shouldForceMaxArm(false, 6, 8), true);
assert.equal(shouldForceMaxArm(false, 7, 8), false);
assert.equal(chooseSuggestedArm(false, 0, 8, 2), 7);

// CMAB+ never forces the absolute top. It probes maxFeasible in that same window.
assert.equal(shouldForceMaxArm(true, 0, 8), false);
assert.equal(shouldProbeFeasibleArm(true, 0, 6), true);
assert.equal(shouldProbeFeasibleArm(true, 5, 6), false);
assert.equal(chooseSuggestedArm(true, 0, 6, 0, maxFeasibleArm(ladder, 1500)), 2);
assert.equal(chooseSuggestedArm(false, 0, 6, 0, maxFeasibleArm(ladder, 1500)), 5);
assert.equal(chooseSuggestedArm(true, 5, 6, 2), 2);
assert.equal(chooseSuggestedArm(true, 5, 6, 99), 5);
assert.equal(chooseSuggestedArm(true, 5, 6, -3), 0);

// Clamp uses kbps and does not request above throughput.
assert.equal(maxFeasibleArm(ladder, 1500), 2);
assert.equal(maxFeasibleArm(ladder, 6000), 5);
assert.equal(maxFeasibleArm(ladder, 0), 0);
assert.equal(maxFeasibleArm(ladder, Number.NaN), 0);
{
    const d = applyFeasibilityClamp(5, ladder, 1500, true);
    assert.equal(d.arm, 2);
    assert.equal(d.clamped, true);
}
{
    const d = applyFeasibilityClamp(2, ladder, 1500, true);
    assert.equal(d.arm, 2);
    assert.equal(d.clamped, false);
}
{
    const d = applyFeasibilityClamp(5, ladder, 100, false);
    assert.equal(d.arm, 5);
    assert.equal(d.clamped, false);
}

// Latency can sit a little over the target. That alone is not the step-down.
assert.equal(isLatencyLate(4.9, 3), true);
assert.equal(isLatencyLate(3.17, 3), false);
assert.equal(isLatencyLate(3, 3), false);
assert.equal(isLatencyLate(1, 0), false);

// Step down only when the rung already playing is faster than measured throughput.
assert.equal(isCurrentAboveThroughput(4900, 3000, 5), true);
assert.equal(isCurrentAboveThroughput(1500, 3000, 4), false);
assert.equal(isCurrentAboveThroughput(3000, 3000, 4), false);
assert.equal(isCurrentAboveThroughput(4900, 3000, -1), false);
assert.equal(isCurrentAboveThroughput(0, 100, 0), false);
assert.equal(isCurrentAboveThroughput(4900, Number.NaN, 5), false);
{
    const stepped = applyLatencyStep(7, 7, 8, true);
    assert.equal(stepped.arm, 6);
    assert.equal(stepped.steppedDown, true);
}
{
    const held = applyLatencyStep(2, 7, 6, true);
    assert.equal(held.arm, 2);
    assert.equal(held.steppedDown, false);
}
assert.equal(applyLatencyStep(5, 7, 6, false).arm, 5);
assert.equal(applyLatencyStep(5, 0, 6, true).arm, 0);
// Current rung still fits: the throughput-clamped suggestion stands, including a jump up.
assert.equal(applyLatencyStep(7, 2, 8, false).arm, 7);
// A lower suggestion is kept when the current rung fits.
assert.equal(applyLatencyStep(1, 4, 8, false).arm, 1);

// DEFAULT only for a clamped upward switch. A downswitch stays STRONG.
assert.equal(chooseSwitchPriority(true, true, priority, 4, 2).priority, DEFAULT);
assert.equal(chooseSwitchPriority(true, true, priority, 2, 6).priority, STRONG);
assert.equal(chooseSwitchPriority(true, false, priority, 5, 2).priority, STRONG);
assert.equal(chooseSwitchPriority(false, true, priority, 4, 2).priority, STRONG);

// Stall guard ignores latency and a healthy buffer. Startup (quality -1) does not enter.
{
    let state = createStallGuardState();
    state = updateStallGuard(state, 0, -1);
    assert.equal(state.active, false);
    state = updateStallGuard(state, 2.0, 4);
    assert.equal(state.active, false);
    assert.equal(applyStallGuard(4, ladder, 200, false, 4).arm, 4);
}
// Empty buffer while playing enters, even if latency is only slightly over the target.
{
    const state = updateStallGuard(createStallGuardState(), 0.05, 4);
    assert.equal(state.active, true);
    const dropped = applyStallGuard(4, ladder, 200, true, 4);
    assert.equal(dropped.arm, 0);
    assert.equal(dropped.dropped, true);
    // Do not climb back to the smoothed-throughput suggestion while the guard is on.
    const held = applyStallGuard(4, ladder, 5000, true, 2);
    assert.equal(held.arm, 2);
}
// A missing sample does not force the bottom rung.
assert.equal(applyStallGuard(3, ladder, Number.NaN, true, 4).arm, 3);
// The cap uses the worst sample in the window, not the latest high one.
assert.equal(worstRecentThroughput([5000, 180, 4000]), 180);
assert.equal(Number.isNaN(worstRecentThroughput([])), true);
assert.equal(applyStallGuard(4, ladder, worstRecentThroughput([5000, 180, 4000]), true, 4).arm, 0);
assert.equal(STALL_RECOVER_DECISIONS >= 12, true);
// Leave only after several healthy buffers. A dip in between resets the streak.
{
    let state = updateStallGuard(createStallGuardState(), 0.0, 3);
    assert.equal(state.active, true);
    for (let i = 0; i < STALL_RECOVER_DECISIONS - 1; i++) {
        state = updateStallGuard(state, 1.2, 3);
        assert.equal(state.active, true);
    }
    state = updateStallGuard(state, 0.4, 3);
    assert.equal(state.active, true);
    assert.equal(state.healthyDecisions, 0);
    for (let i = 0; i < STALL_RECOVER_DECISIONS - 1; i++) {
        state = updateStallGuard(state, 1.2, 3);
    }
    state = updateStallGuard(state, 1.2, 3);
    assert.equal(state.active, false);
}

console.log('cmabPlusPolicy: all assertions passed');
