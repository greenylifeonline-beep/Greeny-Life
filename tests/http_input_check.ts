import assert from "node:assert/strict";
import { finiteNumber, hasText, invalidRequest } from "../lib/http-input";

assert.equal(hasText("  valid  "), true);
assert.equal(hasText("  "), false);
assert.equal(finiteNumber(12.5), 12.5);
assert.equal(finiteNumber(" 12.5 "), 12.5);
assert.equal(finiteNumber(""), null);
assert.equal(finiteNumber("not-a-number"), null);
assert.equal(invalidRequest("Invalid input").status, 400);
console.log("http_input_check: PASS");