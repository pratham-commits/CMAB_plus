import assert from 'node:assert/strict';
import {
    applyFeasibilityClamp,
    applyLatencyStep,
    chooseSuggestedArm,
    chooseSwitchPriority,
    isLatencyLate,
    maxFeasibleArm,
    shouldForceMaxArm,
    shouldProbeFeasibleArm,
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

// While late, drop one rung from the current quality and do not jump back up.
assert.equal(isLatencyLate(4.9, 3), true);
assert.equal(isLatencyLate(3.17, 3), false);
assert.equal(isLatencyLate(3, 3), false);
assert.equal(isLatencyLate(1, 0), false);
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

// DEFAULT only for a clamped upward switch. A downswitch stays STRONG.
assert.equal(chooseSwitchPriority(true, true, priority, 4, 2).priority, DEFAULT);
assert.equal(chooseSwitchPriority(true, true, priority, 2, 6).priority, STRONG);
assert.equal(chooseSwitchPriority(true, false, priority, 5, 2).priority, STRONG);
assert.equal(chooseSwitchPriority(false, true, priority, 4, 2).priority, STRONG);

console.log('cmabPlusPolicy: all assertions passed');
