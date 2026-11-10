// Runs every conformance vector through web/engine.js and prints {suite: {id: result}} as JSON.
// Invoked by tests/test_conformance.py; the vectors live in conformance/*.json.
import { readFileSync } from "node:fs";
import { checkRequires, applySets } from "../web/engine.js";

const SUITES = {
  requires: (c) => checkRequires(c.requires, c.state),
  sets: (c) => applySets(c.sets, c.state),
};

const out = {};
for (const [suite, run] of Object.entries(SUITES)) {
  const file = new URL(`../conformance/${suite}.json`, import.meta.url);
  const { cases } = JSON.parse(readFileSync(file, "utf-8"));
  out[suite] = Object.fromEntries(cases.map((c) => [c.id, run(c)]));
}
console.log(JSON.stringify(out));
