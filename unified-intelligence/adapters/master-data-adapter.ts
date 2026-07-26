/**
 * Greeny-Life Unified Intelligence
 * Master Data Adapter
 *
 * Purpose:
 * - Read canonical Master Data
 * - Never mutate Master Data directly
 * - Expose authoritative data to Intelligence and Brain
 */

import fs from "fs";
import path from "path";

export interface MasterDataRecord {
    id?: string;
    [key: string]: unknown;
}

export interface MasterDataResult {
    source: string;
    authoritative: true;
    records: MasterDataRecord[];
    recordCount: number;
}

export class MasterDataAdapter {

    private readonly rootPath: string;

    constructor(rootPath: string) {
        this.rootPath = rootPath;
    }

    readJson(filePath: string): MasterDataResult {

        const absolutePath = path.isAbsolute(filePath)
            ? filePath
            : path.join(this.rootPath, filePath);

        if (!fs.existsSync(absolutePath)) {
            throw new Error(
                `MASTER_DATA_NOT_FOUND: ${absolutePath}`
            );
        }

        const raw = fs.readFileSync(
            absolutePath,
            "utf8"
        );

        const parsed = JSON.parse(raw);

        const records = Array.isArray(parsed)
            ? parsed
            : [parsed];

        return {
            source: absolutePath,
            authoritative: true,
            records,
            recordCount: records.length
        };
    }

    canWrite(): false {
        return false;
    }
}
