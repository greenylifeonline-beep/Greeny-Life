import fs from "fs";
import path from "path";

const ROOT = process.cwd();

interface IntegrityFinding {
    type:
        | "MISSING_FILE"
        | "EMPTY_FILE"
        | "INVALID_JSON"
        | "MISSING_MIGRATION"
        | "MISSING_LEGACY"
        | "DATA_CONFLICT"
        | "DUPLICATE_ID"
        | "DUPLICATE_SLUG";

    severity:
        | "ERROR"
        | "WARNING";

    file?: string;

    product?: string;

    field?: string;

    message: string;
}

const FILES = {
    canonical:
        "data/product_master_extended.json",

    migrated:
        "data/migrated_products.json",

    legacy:
        "data/legacy/products.json"
};

function readJSON(
    file: string,
    findings: IntegrityFinding[]
) {
    const target = path.join(ROOT, file);

    if (!fs.existsSync(target)) {
        findings.push({
            type: "MISSING_FILE",
            severity: "ERROR",
            file,
            message: `${file} does not exist`
        });

        return null;
    }

    try {
        const content =
            fs.readFileSync(
                target,
                "utf8"
            ).trim();

        if (!content) {
            findings.push({
                type: "EMPTY_FILE",
                severity: "ERROR",
                file,
                message: `${file} is empty`
            });

            return null;
        }

        return JSON.parse(content);
    }

    catch {
        findings.push({
            type: "INVALID_JSON",
            severity: "ERROR",
            file,
            message: `${file} contains invalid JSON`
        });

        return null;
    }
}

function normalize(
    data: any
): any[] {

    if (Array.isArray(data)) {
        return data;
    }

    if (
        data &&
        Array.isArray(data.products)
    ) {
        return data.products;
    }

    if (
        data &&
        Array.isArray(data.data)
    ) {
        return data.data;
    }

    return [];
}

function normalizeValue(
    value: any
) {

    if (
        value === undefined ||
        value === null
    ) {
        return null;
    }

    if (
        typeof value === "object"
    ) {

        if (
            value.en
        ) {
            return String(
                value.en
            )
                .toLowerCase()
                .trim();
        }

        if (
            value.name
        ) {
            return String(
                value.name
            )
                .toLowerCase()
                .trim();
        }

        return JSON.stringify(
            value
        )
            .toLowerCase()
            .trim();
    }

    return String(value)
        .toLowerCase()
        .trim();
}

function getSlug(
    product: any
): string | null {

    if (
        typeof product.slug ===
        "string" &&
        product.slug.trim()
    ) {
        return product.slug
            .toLowerCase()
            .trim();
    }

    if (
        typeof product.id ===
        "string" &&
        product.id.trim()
    ) {
        return product.id
            .toLowerCase()
            .trim();
    }

    if (
        typeof product.name ===
        "string" &&
        product.name.trim()
    ) {
        return product.name
            .toLowerCase()
            .trim()
            .replace(/\s+/g, "-");
    }

    return null;
}

function detectDuplicates(
    products: any[],
    file: string,
    findings: IntegrityFinding[]
) {

    const ids =
        new Map<string, number>();

    const slugs =
        new Map<string, number>();

    for (
        const product
        of products
    ) {

        if (
            typeof product.id ===
            "string"
        ) {

            const id =
                product.id
                    .toLowerCase()
                    .trim();

            ids.set(
                id,
                (ids.get(id) ?? 0) + 1
            );
        }

        const slug =
            getSlug(product);

        if (slug) {

            slugs.set(
                slug,
                (slugs.get(slug) ?? 0) + 1
            );
        }
    }

    for (
        const [id, count]
        of ids
    ) {

        if (count > 1) {

            findings.push({
                type:
                    "DUPLICATE_ID",

                severity:
                    "ERROR",

                file,

                product:
                    id,

                message:
                    `${id} appears ${count} times in ${file}`
            });
        }
    }

    for (
        const [slug, count]
        of slugs
    ) {

        if (count > 1) {

            findings.push({
                type:
                    "DUPLICATE_SLUG",

                severity:
                    "ERROR",

                file,

                product:
                    slug,

                message:
                    `${slug} appears ${count} times in ${file}`
            });
        }
    }
}

function buildIdentityMap(
    products: any[]
) {

    const map =
        new Map<string, any>();

    for (
        const product
        of products
    ) {

        const slug =
            getSlug(product);

        if (!slug) {
            continue;
        }

        if (
            !map.has(slug)
        ) {
            map.set(
                slug,
                product
            );
        }
    }

    return map;
}

function compareProvenance(
    canonical: any[],
    source: any[],
    sourceType:
        "MIGRATION" |
        "LEGACY",
    findings:
        IntegrityFinding[]
) {

    const sourceMap =
        buildIdentityMap(
            source
        );

    for (
        const product
        of canonical
    ) {

        const slug =
            getSlug(product);

        if (!slug) {
            continue;
        }

        const found =
            sourceMap.get(slug);

        if (!found) {

            findings.push({

                type:
                    sourceType ===
                    "MIGRATION"
                        ? "MISSING_MIGRATION"
                        : "MISSING_LEGACY",

                severity:
                    "ERROR",

                product:
                    slug,

                message:
                    `${slug} missing from ${sourceType.toLowerCase()} source`
            });

            continue;
        }

        const fields = [
            "name",
            "category",
            "image",
            "status"
        ];

        for (
            const field
            of fields
        ) {

            const canonicalValue =
                normalizeValue(
                    product[field]
                );

            const sourceValue =
                normalizeValue(
                    found[field]
                );

            if (
                canonicalValue !==
                sourceValue
            ) {

                findings.push({

                    type:
                        "DATA_CONFLICT",

                    severity:
                        "WARNING",

                    product:
                        slug,

                    field,

                    message:
                        `${field} mismatch between canonical and ${sourceType.toLowerCase()} source`
                });
            }
        }
    }
}

export function runIntegrityEngine() {

    const findings:
        IntegrityFinding[] = [];

    /*
     * =====================================================
     * 1. CANONICAL SOURCE
     * =====================================================
     */

    const canonicalRaw =
        readJSON(
            FILES.canonical,
            findings
        );

    const canonical =
        normalize(
            canonicalRaw
        );

    /*
     * =====================================================
     * 2. PROVENANCE SOURCES
     * =====================================================
     */

    const migratedRaw =
        readJSON(
            FILES.migrated,
            findings
        );

    const legacyRaw =
        readJSON(
            FILES.legacy,
            findings
        );

    const migrated =
        normalize(
            migratedRaw
        );

    const legacy =
        normalize(
            legacyRaw
        );

    /*
     * =====================================================
     * 3. DUPLICATE DETECTION
     * =====================================================
     */

    detectDuplicates(
        canonical,
        FILES.canonical,
        findings
    );

    detectDuplicates(
        migrated,
        FILES.migrated,
        findings
    );

    detectDuplicates(
        legacy,
        FILES.legacy,
        findings
    );

    /*
     * =====================================================
     * 4. PROVENANCE VALIDATION
     * =====================================================
     */

    compareProvenance(
        canonical,
        migrated,
        "MIGRATION",
        findings
    );

    compareProvenance(
        canonical,
        legacy,
        "LEGACY",
        findings
    );

    /*
     * =====================================================
     * 5. FINAL HEALTH
     * =====================================================
     */

    const errors =
        findings.filter(
            item =>
                item.severity ===
                "ERROR"
        ).length;

    const warnings =
        findings.filter(
            item =>
                item.severity ===
                "WARNING"
        ).length;

    let health:
        "HEALTHY" |
        "REVIEW_REQUIRED" |
        "FAILED";

    if (errors > 0) {

        health =
            "FAILED";

    }

    else if (
        warnings > 0
    ) {

        health =
            "REVIEW_REQUIRED";

    }

    else {

        health =
            "HEALTHY";
    }

    return {

        system:
            "GL-DOS",

        engine:
            "Data Integrity Engine",

        version:
            "3.0",

        architecture:
            "CANONICAL_SOURCE_WITH_PROVENANCE",

        canonical_source:
            FILES.canonical,

        generated:
            new Date()
                .toISOString(),

        summary: {

            canonical_products:
                canonical.length,

            migrated_products:
                migrated.length,

            legacy_products:
                legacy.length,

            unique_products:
                new Set(
                    canonical
                        .map(
                            getSlug
                        )
                        .filter(
                            Boolean
                        )
                ).size,

            errors,

            warnings,

            health
        },

        findings
    };
}