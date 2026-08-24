"use strict";

const assert = require("assert");
const { normalizeLabelIds, parseInvocation } = require("./linear_cli.js");

const uuid = "353fdde3-4428-46a7-a145-b88193b1e961";

assert.deepStrictEqual(normalizeLabelIds([uuid]), [uuid]);
assert.deepStrictEqual(normalizeLabelIds(`["${uuid}"]`), [uuid]);
assert.deepStrictEqual(normalizeLabelIds(`[${uuid}]`), [uuid]);
assert.deepStrictEqual(normalizeLabelIds(uuid), [uuid]);

const parsed = parseInvocation(["node", "linear_cli.js", "save_issue", "--labelIds", uuid]);
assert.deepStrictEqual(normalizeLabelIds(parsed.payload.labelIds), [uuid]);

console.log("linear_cli label parsing ok");
