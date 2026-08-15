/**
 * Greeny-Life Traceable Report Adapter
 */

import fs from "fs";
import path from "path";

export interface TraceEvent {
    correlationId: string;
    phase: string;
    event: string;
    timestamp: string;
    payload?: unknown;
}

export class TraceableReportAdapter {

    private readonly reportRoot: string;

    constructor(reportRoot: string) {
        this.reportRoot = reportRoot;
    }

    writeTrace(
        event: TraceEvent
    ): string {

        const date =
            new Date()
                .toISOString()
                .slice(0, 10);

        const directory =
            path.join(
                this.reportRoot,
                "runtime",
                date
            );

        fs.mkdirSync(
            directory,
            {
                recursive: true
            }
        );

        const filename =
            `${event.correlationId}-${Date.now()}.json`;

        const outputPath =
            path.join(
                directory,
                filename
            );

        fs.writeFileSync(
            outputPath,
            JSON.stringify(
                event,
                null,
                2
            ),
            "utf8"
        );

        return outputPath;
    }
}
