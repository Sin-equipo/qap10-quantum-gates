"""Pure browser-side transfer accounting used by the visual airport.

The animation clock is illustrative. Distances and the sum of individual
distances use the exact QAP convention: one flow unit per figure, i < k once.
This string is also executed by Node in the independent invariant tests.
"""

WALK_MODEL = r"""
const Walk = (() => {
  const SECONDS_PER_DISTANCE = 0.55;
  const EPSILON = 1e-9;

  function validAssignment(assignment, n) {
    return Array.isArray(assignment) && assignment.length === n &&
      assignment.every(g => Number.isInteger(g) && g >= 0 && g < n) &&
      new Set(assignment).size === n;
  }

  function readDistance(distances, assignment, i, k, n) {
    if (!validAssignment(assignment, n)) return null;
    const d = distances[assignment[i]]?.[assignment[k]];
    return typeof d === 'number' && Number.isFinite(d) && d >= 0 ? d : null;
  }

  function transfers(flows, distances, leftAssignment, rightAssignment) {
    const result = [], n = flows.length;
    for (let i = 0; i < n; i++) {
      for (let k = i + 1; k < n; k++) {
        const flow = flows[i][k];
        if (!(typeof flow === 'number' && flow > 0 && Number.isFinite(flow))) continue;
        const leftDistance = readDistance(distances, leftAssignment, i, k, n);
        const rightDistance = readDistance(distances, rightAssignment, i, k, n);
        const leftCost = leftDistance === null ? null : flow * leftDistance;
        const rightCost = rightDistance === null ? null : flow * rightDistance;
        result.push({id: `${i}-${k}`, i, k, flow, leftDistance, rightDistance,
          leftCost, rightCost,
          delta: leftCost === null || rightCost === null ? null : leftCost - rightCost});
      }
    }
    return result;
  }

  function people(flows, distances, assignment, pairId = null) {
    const result = [], n = flows.length;
    if (!validAssignment(assignment, n)) return result;
    const maxDistance = Math.max(1, ...distances.flat());
    let id = 0;
    for (let i = 0; i < n; i++) {
      for (let k = i + 1; k < n; k++) {
        const flow = flows[i][k];
        if (!Number.isInteger(flow) || flow < 0) {
          throw new RangeError('Each visual figure must represent one nonnegative integer flow unit.');
        }
        const d = readDistance(distances, assignment, i, k, n);
        if (flow > 0 && d === null) return [];
        for (let q = 0; q < flow; q++, id++) {
          if (pairId !== null && pairId !== `${i}-${k}`) continue;
          result.push({id, i, k, g: assignment[i], h: assignment[k], d,
            delay: ((i * 19 + k * 7 + q * 11) % 17) / 17 * 0.5,
            jitter: ((q % 5) - 2) * 3.2,
            mood: d / maxDistance > 2 / 3 ? 2 : d / maxDistance > 1 / 3 ? 1 : 0});
        }
      }
    }
    return result;
  }

  function progress(person, t) {
    const current = Number.isNaN(Number(t)) ? 0 : Number(t);
    const delay = person.delay ?? 0;
    const travelSeconds = person.d * SECONDS_PER_DISTANCE;
    if (current + EPSILON < delay) return 0;
    if (travelSeconds === 0 || current + EPSILON >= delay + travelSeconds) return 1;
    return Math.max(0, Math.min(1, (current - delay) / travelSeconds));
  }

  function duration(group) {
    return group.reduce((last, person) =>
      Math.max(last, (person.delay ?? 0) + person.d * SECONDS_PER_DISTANCE), 0);
  }

  function stats(group, t) {
    let arrived = 0, travelled = 0, totalDistance = 0;
    for (const person of group) {
      const fraction = progress(person, t);
      arrived += fraction === 1 ? 1 : 0;
      travelled += person.d * fraction;
      totalDistance += person.d;
    }
    return {total: group.length, arrived,
      travelled: Math.min(totalDistance, Math.max(0, travelled)),
      totalDistance, lastArrival: duration(group)};
  }

  return {transfers, people, duration, progress, stats};
})();
"""
