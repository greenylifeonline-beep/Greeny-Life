import { NextResponse } from "next/server";

import { mastermindAuthority, operatingBrains } from "@/lib/intelligence/three-operating-brains";

export async function GET() {
  return NextResponse.json({
    success: true,
    data: {
      primaryAuthority: mastermindAuthority,
      operatingBrains,
      rule: "Local brains are semi-independent for daily operations. They escalate opportunities, errors, constraints, cross-company work, and material changes to MasterMind AI; all sensitive execution requires user approval.",
    },
  });
}
