"use strict";

const assert = require("assert");
const {
  normalizeLabelIds,
  parseInvocation,
  getValue,
  cycleFilter,
  serializeCycle,
  localClock,
} = require("./linear_cli.js");

const uuid = "353fdde3-4428-46a7-a145-b88193b1e961";

assert.deepStrictEqual(normalizeLabelIds([uuid]), [uuid]);
assert.deepStrictEqual(normalizeLabelIds(`["${uuid}"]`), [uuid]);
assert.deepStrictEqual(normalizeLabelIds(`[${uuid}]`), [uuid]);
assert.deepStrictEqual(normalizeLabelIds(uuid), [uuid]);

const parsed = parseInvocation(["node", "linear_cli.js", "save_issue", "--labelIds", uuid]);
assert.deepStrictEqual(normalizeLabelIds(parsed.payload.labelIds), [uuid]);

const repeated = parseInvocation([
  "node",
  "linear_cli.js",
  "save_issue",
  "--id",
  "JPS-5",
  "--labelIds",
  uuid,
  "--labelIds",
  "second-label",
]);
assert.equal(repeated.payload.id, "JPS-5");
assert.deepStrictEqual(repeated.payload.labelIds, [uuid, "second-label"]);

const merged = parseInvocation([
  "node",
  "linear_cli.js",
  "get_issue",
  "--json",
  JSON.stringify({ id: "JPS-5", title: "from-json" }),
  "--title",
  "from-flag",
]);
assert.equal(merged.payload.id, "JPS-5");
assert.equal(merged.payload.title, "from-flag");

const flagsOnly = parseInvocation([
  "node",
  "linear_cli.js",
  "list_issues",
  "--team",
  "JPS",
  "--limit",
  "10",
]);
assert.equal(flagsOnly.payload.team, "JPS");
assert.equal(flagsOnly.payload.limit, 10);

const kebab = parseInvocation([
  "node",
  "linear_cli.js",
  "save_issue",
  "--due-date",
  "2026-09-15",
  "--project-id",
  "proj-1",
  "--label-ids",
  uuid,
]);
assert.equal(getValue(kebab.payload, ["dueDate"]), "2026-09-15");
assert.equal(getValue(kebab.payload, ["projectId"]), "proj-1");
assert.equal(getValue(kebab.payload, ["labelIds"]), uuid);

assert.deepStrictEqual(cycleFilter("current"), { isActive: { eq: true } });
assert.deepStrictEqual(cycleFilter("active"), { isActive: { eq: true } });
assert.deepStrictEqual(cycleFilter(true), { isActive: { eq: true } });
assert.deepStrictEqual(cycleFilter("next"), { isNext: { eq: true } });
assert.deepStrictEqual(cycleFilter("previous"), { isPrevious: { eq: true } });
assert.deepStrictEqual(cycleFilter(uuid), { id: { eq: uuid } });
assert.deepStrictEqual(cycleFilter(1), {
  or: [
    { name: { eq: "1" } },
    { number: { eq: 1 } },
    { name: { eq: "Week 01" } },
    { name: { eq: "Week 1" } },
  ],
});
assert.deepStrictEqual(cycleFilter("Week 01"), {
  or: [
    { name: { eq: "Week 01" } },
    { number: { eq: 1 } },
    { name: { eq: "Week 1" } },
  ],
});

const cycleFlag = parseInvocation([
  "node",
  "linear_cli.js",
  "list_issues",
  "--cycle",
  "current",
]);
assert.equal(cycleFlag.command, "list_issues");
assert.equal(cycleFlag.payload.cycle, "current");

const allIssues = parseInvocation(["node", "linear_cli.js", "all_issues", "--cycle", "Week 01"]);
assert.equal(allIssues.command, "all_issues");
assert.equal(allIssues.payload.cycle, "Week 01");

const currentCycle = parseInvocation(["node", "linear_cli.js", "current_cycle_issues"]);
assert.equal(currentCycle.command, "current_cycle_issues");

const nowCommand = parseInvocation(["node", "linear_cli.js", "now"]);
assert.equal(nowCommand.command, "now");

assert.deepStrictEqual(
  serializeCycle({
    id: "cyc-1",
    name: "Week 01",
    number: 1,
    startsAt: "2026-08-24T00:00:00.000Z",
    endsAt: "2026-08-31T00:00:00.000Z",
    isActive: true,
    isNext: false,
    isPrevious: false,
  }),
  {
    id: "cyc-1",
    name: "Week 01",
    number: 1,
    startsAt: "2026-08-24T00:00:00.000Z",
    endsAt: "2026-08-31T00:00:00.000Z",
    isActive: true,
    isNext: false,
    isPrevious: false,
  }
);
assert.equal(serializeCycle(null), null);

const frozen = new Date("2026-08-25T13:24:00.000Z");
const clock = localClock(frozen);
assert.equal(clock.utc, frozen.toISOString());
assert.match(clock.date, /^\d{4}-\d{2}-\d{2}$/);
assert.match(clock.local, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/);

console.log("linear_cli label parsing ok");
