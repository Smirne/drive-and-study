/* Deterministic answer matcher: turns a recognised utterance into 1..n, "repeat", "skip" or null.
 *
 * Two ways to answer:
 *  - by number: "number two", "two", "option three", "4"
 *  - by content: words from an option, e.g. "business scenarios" or "architecture vision"
 *
 * Content matching weighs each option word by how many options contain it (a word unique to one
 * option counts 1, a word shared by two counts 1/2, ...), tolerates small recognition errors on
 * longer words, and only answers when one option clearly wins. Loose number homophones ("to",
 * "for") count only in short utterances, so "to prepare the organization" is not answer 2.
 *
 * Shared by app/template.html (inlined at build) and tests/test_matcher.js (Node).
 */
const MATCHER = (() => {
  const STRICT = { 1: ["1", "one", "first"], 2: ["2", "two", "second"], 3: ["3", "three", "third"], 4: ["4", "four", "fourth"] };
  const LOOSE = { 1: ["won", "wan", "juan", "van"], 2: ["to", "too", "tu"], 3: ["tree", "free"], 4: ["for", "fore", "ford"] };
  const CMD = { repeat: ["repeat", "again", "pardon"], skip: ["skip", "pass"] };
  const SHORT = 3;   // utterances up to this many words may use the loose homophones

  const STOP = new Set(("a an the of and or to in on is it its it's for with by as at be are was were this that these those " +
    "which what who from into than then so if not no all any each one some do does done can could should would will " +
    "there their them they we you your our i me my number option answer think say said um uh er").split(" "));

  function words(text) {
    return text.toLowerCase().replace(/[’']/g, "").replace(/[^a-z0-9 ]+/g, " ").split(/\s+/).filter(Boolean);
  }
  function stem(w) {
    if (w.length > 4 && w.endsWith("ies")) return w.slice(0, -3) + "y";
    if (w.length > 3 && w.endsWith("s") && !w.endsWith("ss")) return w.slice(0, -1);
    return w;
  }
  // content tokens: no stop words; single letters kept except "a" and "i" (e.g. "Phase B")
  function tokens(text) {
    return words(text).filter(w => !STOP.has(w) && (w.length > 1 || /^[b-hj-z]$/.test(w))).map(stem);
  }
  function lev(a, b, max) {
    if (Math.abs(a.length - b.length) > max) return max + 1;
    let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      let best = cur[0];
      for (let j = 1; j <= b.length; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
        best = Math.min(best, cur[j]);
      }
      if (best > max) return max + 1;
      prev = cur;
    }
    return prev[b.length];
  }
  function sameWord(a, b) {
    if (a === b) return true;
    const n = Math.min(a.length, b.length);
    if (n >= 8) return lev(a, b, 2) <= 2;
    if (n >= 5) return lev(a, b, 1) <= 1;
    return false;
  }

  function byNumber(ws, loose) {
    const found = new Set();
    for (const w of ws) {
      for (const k in STRICT) if (STRICT[k].includes(w)) found.add(+k);
      if (loose) for (const k in LOOSE) if (LOOSE[k].includes(w)) found.add(+k);
    }
    return found.size === 1 ? [...found][0] : (found.size > 1 ? "ambiguous" : null);
  }
  function byCommand(ws) {
    const found = new Set();
    for (const w of ws) for (const k in CMD) if (CMD[k].includes(w)) found.add(k);
    return found.size === 1 ? [...found][0] : null;
  }

  // Returns {value, score, second} or null. value is 1-based.
  function byContent(text, options) {
    const said = [...new Set(tokens(text))];
    if (!said.length || !options || !options.length) return null;
    const optTok = options.map(o => [...new Set(tokens(o))]);
    const df = new Map();
    optTok.forEach(ts => ts.forEach(t => df.set(t, (df.get(t) || 0) + 1)));
    const scores = optTok.map(ts => {
      let s = 0, strong = false;
      for (const t of ts) {
        if (df.get(t) >= options.length) continue;            // in every option: says nothing
        if (said.some(w => sameWord(w, t))) {
          s += 1 / df.get(t);
          if (df.get(t) === 1 && t.length >= 3) strong = true;
        }
      }
      return { s, strong };
    });
    const order = scores.map((x, i) => i).sort((a, b) => scores[b].s - scores[a].s);
    const best = scores[order[0]], second = scores[order[1]] || { s: 0 };
    // accept: at least one word unique to the winner, a total of 1, and a clear lead
    if (best.strong && best.s >= 1 && best.s >= 2 * second.s)
      return { value: order[0] + 1, score: +best.s.toFixed(2), second: +second.s.toFixed(2) };
    // or: what was said is exactly one option's words ("Conformant" vs "Fully conformant")
    const exact = optTok.map((ts, i) => i).filter(i =>
      optTok[i].length && optTok[i].every(t => said.some(w => sameWord(w, t))) &&
      said.every(w => optTok[i].some(t => sameWord(w, t))));
    if (exact.length === 1) return { value: exact[0] + 1, score: 1, second: 0, exact: true };
    return null;
  }

  // Main entry. options: current question's option texts (optional).
  function parse(text, options) {
    const ws = words(text);
    if (!ws.length) return null;
    const short = ws.length <= SHORT;
    const cmd = byCommand(ws);
    if (short) {
      const n = byNumber(ws, true);
      if (typeof n === "number") return { value: n, how: "number" };
      if (n === "ambiguous") return null;
      if (cmd) return { value: cmd, how: "command" };
    }
    const c = byContent(text, options);
    if (c) return { value: c.value, how: "content", score: c.score, second: c.second };
    if (!short) {
      const n = byNumber(ws, false);
      if (typeof n === "number") return { value: n, how: "number" };
      if (cmd) return { value: cmd, how: "command" };
    }
    return null;
  }

  return { parse, byContent, tokens };
})();
if (typeof module !== "undefined") module.exports = MATCHER;
