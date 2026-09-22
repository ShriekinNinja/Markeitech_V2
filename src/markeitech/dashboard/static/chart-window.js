"use strict";
// Bounded presentation window; timestamps and OHLC values remain provider-owned.
const DashboardWindow = (() => {
  function visibleIndices(bars, range) {
    if (!bars.length || !range) return null;
    const first = Math.max(0, Math.min(bars.length - 1, Math.floor(range.from)));
    const last = Math.max(first, Math.min(bars.length - 1, Math.ceil(range.to)));
    return {first, last};
  }
  function room(bars, range, maximum, direction) {
    const visible = visibleIndices(bars, range);
    if (!visible) return maximum;
    const evictable = direction === "older" ? bars.length - visible.last - 1 : visible.first;
    return Math.max(0, maximum - bars.length + evictable);
  }
  function retain(all, before, range, maximum, direction) {
    const visible = visibleIndices(before, range);
    const index = new Map(all.map((bar, i) => [bar.time, i]));
    const left = visible ? index.get(before[visible.first].time) : undefined;
    const right = visible ? index.get(before[visible.last].time) : undefined;
    const lastStart = Math.max(0, all.length - maximum);
    let start = direction === "older" ? 0 : direction === "newer" ? lastStart
      : (index.get(before[0]?.time) ?? lastStart);
    if (left !== undefined && right !== undefined) {
      // Keep every visible candle. Prefer eviction on the side away from navigation.
      start = Math.max(Math.max(0, right - maximum + 1), Math.min(start, left));
    }
    start = Math.max(0, Math.min(start, lastStart));
    const bars = all.slice(start, start + maximum);
    const shift = left === undefined ? 0 : left - start - visible.first;
    return {bars, range: range ? {from: range.from + shift, to: range.to + shift} : null};
  }
  return {retain, room};
})();
