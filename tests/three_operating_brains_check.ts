import assert from "node:assert/strict";

import { approvalNotification, escalationReasons, localBrainFor, mastermindAuthority, operatingBrains } from "../lib/intelligence/three-operating-brains";

assert.equal(mastermindAuthority.role, "Primary decision intelligence and command authority");
assert.equal(localBrainFor("GREENY_LIFE_EGYPT"), "GREENY_LIFE_EGYPT_BRAIN");
assert.equal(localBrainFor("GREENS_NATURE_UAE"), "GREENS_NATURE_UAE_BRAIN");
assert.equal(localBrainFor("GREEN_LINES_NORWAY_EU"), "GREEN_LINES_NORWAY_EU_BRAIN");
assert.equal(operatingBrains.GREENY_LIFE_EGYPT_BRAIN.company, "GREENY_LIFE_EGYPT");

const escalation = escalationReasons({ originCompany: "GREENY_LIFE_EGYPT", destinationCompany: "GREEN_LINES_NORWAY_EU", productId: "H001", destination: "Norway", eventType: "OPPORTUNITY" });
assert.ok(escalation.includes("CROSS_COMPANY_TRADE"));
assert.ok(escalation.includes("NEW_OPPORTUNITY"));
const notification = approvalNotification({ localBrain: "GREENY_LIFE_EGYPT_BRAIN", escalation, recommendation: "Hold", blockers: ["Missing evidence"], alternatives: ["Collect evidence"], proposedActions: ["Review"] });
assert.equal(notification.status, "PENDING_USER_APPROVAL");
assert.equal(notification.executionRule.includes("explicitly approves"), true);

console.log("Three operating brains: PASS");
