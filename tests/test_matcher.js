// Unit test for app/matcher.js against the real question bank.  Run: node tests/test_matcher.js
const M = require("../app/matcher.js");
const qs = require("../content/togaf-foundation/questions.json");
let fail = 0;
function eq(label, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) { fail++; console.log("FAIL", label, "got", got, "want", want); }
}
const v = (t, o) => { const r = M.parse(t, o); return r ? r.value : null; };

// numbers and commands
const o0 = qs[0].o;
eq("number two", v("number two", o0), 2);
eq("two", v("two", o0), 2);
eq("digit", v("4", o0), 4);
eq("number for", v("number for", o0), 4);
eq("option three", v("option three", o0), 3);
eq("ambiguous", v("two or three", o0), null);
eq("repeat", v("repeat please", o0), "repeat");
eq("skip", v("skip", o0), "skip");
eq("nothing", v("hello there", o0), null);
// loose homophones must not hijack content answers
const prep = qs[0].o.findIndex(o => /prepare the organization/i.test(o)) + 1;
eq("to prepare... is content, not 2", v("to prepare the organization for architecture work", o0), prep);

// content: every option, three ways of saying it
const STOP = new Set("a an the of and or to in on is it its for with by as at be are this that which what from into all any each".split(" "));
let right = 0, wrong = 0, none = 0;
const wrongs = [], nones = [];
qs.forEach((q, qi) => q.o.forEach((opt, j) => {
  const ws = opt.replace(/[.,]/g, "").split(/\s+/);
  const content = ws.filter(w => !STOP.has(w.toLowerCase()));
  // distinctive: content words not present in any other option
  const others = q.o.filter((_, k) => k !== j).join(" ").toLowerCase();
  const distinct = content.filter(w => !others.includes(w.toLowerCase().replace(/s$/, "")));
  const sayings = {
    full: opt,
    opening: content.slice(0, 3).join(" "),
    keywords: (distinct.length ? distinct : content).slice(0, 2).join(" "),
  };
  for (const [kind, text] of Object.entries(sayings)) {
    const got = v(text, q.o);
    if (got === j + 1) right++;
    else if (got === null) { none++; nones.push(`Q${qi + 1}.${j + 1} ${kind}: "${text}"`); }
    else { wrong++; wrongs.push(`Q${qi + 1}.${j + 1} ${kind}: "${text}" -> ${got}`); }
  }
}));
const total = right + wrong + none;
console.log(`content: ${right}/${total} right, ${none} not understood (asks again), ${wrong} WRONG`);
if (nones.length) console.log("not understood (sample):\n  " + nones.filter(x => !x.startsWith("Q6.")).join("\n  "));
if (wrongs.length) console.log("wrong:\n  " + wrongs.join("\n  "));

// recognition errors on longer words
const bs = qs.findIndex(q => q.o.some(o => /business scenarios/i.test(o)));
if (bs >= 0) {
  const want = qs[bs].o.findIndex(o => /business scenarios/i.test(o)) + 1;
  eq("misheard: business senarios", v("business senarios", qs[bs].o), want);
}
if (wrong) fail++;
console.log(fail ? `${fail} failure(s)` : "all matcher checks passed");
process.exit(fail ? 1 : 0);
