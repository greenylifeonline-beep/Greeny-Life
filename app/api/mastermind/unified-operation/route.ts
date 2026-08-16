import { NextRequest, NextResponse } from "next/server";

import { authorizeRequest } from "@/lib/authz";

import {
  buildUnifiedOperationalResult,
} from "@/lib/intelligence/unified-operational-orchestrator";

import {
  type MasterMindRequest,
} from "@/lib/intelligence/mastermind-agents";

import {
  companies,
} from "@/lib/intelligence/trade-corridors";

const isCompany = (
  value: unknown,
): value is MasterMindRequest["originCompany"] =>
  typeof value === "string" && value in companies;

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(
    request,
    ["ADMIN", "EXPORT"],
    "/api/mastermind/unified-operation",
    "BUILD_UNIFIED_OPERATIONAL_RESULT",
  );

  if (authorization.response) {
    return authorization.response;
  }

  if (!authorization.session) {
    return NextResponse.json(
      {
        success: false,
        error: "Authenticated session is required.",
      },
      {
        status: 401,
      },
    );
  }

  try {
    const body =
      (await request.json()) as Record<string, unknown>;

    if (
      typeof body.productId !== "string" ||
      typeof body.destination !== "string" ||
      !isCompany(body.originCompany) ||
      !isCompany(body.destinationCompany)
    ) {
      return NextResponse.json(
        {
          success: false,
          error:
            "productId, destination, originCompany and destinationCompany are required.",
        },
        {
          status: 400,
        },
      );
    }

    const data =
      await buildUnifiedOperationalResult({
        productId: body.productId.trim(),
        destination: body.destination.trim(),

        actor:
          authorization.session.email,

        originCompany:
          body.originCompany,

        destinationCompany:
          body.destinationCompany,

        traceCode:
          typeof body.traceCode === "string"
            ? body.traceCode.trim()
            : undefined,

        eventType:
          typeof body.eventType === "string"
            ? body.eventType.trim()
            : undefined,

        customerId:
          typeof body.customerId === "string"
            ? body.customerId.trim()
            : undefined,
      });

    return NextResponse.json(
      {
        success: true,
        data,
      },
      {
        status: 201,
      },
    );
  }
  catch (error) {
    return NextResponse.json(
      {
        success: false,
        error:
          "Unable to build unified operational result",
        details:
          (error as Error).message,
      },
      {
        status: 400,
      },
    );
  }
}