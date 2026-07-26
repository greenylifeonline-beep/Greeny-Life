/**
 * GREENY LIFE Migration Registry Builder
 * File: scripts/migration/cleanup-engine.js
 *
 * This engine reads report evidence, normalizes it, detects conflicts and
 * builds a registry and executable migration plan. It never moves, deletes
 * or edits any legacy source file.
 */

"use strict";

const path = require("path");

const config = require("./config");
const utils = require("./utils");

const DEFAULT_CATALOG = [
    { id: "components", file: null, type: "component_evidence", enabled: true },
    { id: "assets", file: null, type: "asset_evidence", enabled: true },
    { id: "refactor", file: null, type: "refactor_evidence", enabled: true },
    { id: "archive", file: null, type: "archive_evidence", enabled: true },
    { id: "remove", file: null, type: "remove_evidence", enabled: true }
];

class MigrationRegistryBuilder {
    constructor() {
        this.engine = {
            name: "GREENY LIFE Migration Registry Builder",
            version: "1.0.0"
        };
        this.errors = [];
        this.conflicts = [];
        this.registry = [];
        this.catalog = [];
        this.catalogResults = [];
    }

    run() {
        utils.title("GREENY LIFE Migration Registry Builder");

        this.catalog = this.loadCatalog();
        const evidence = this.loadEvidence(this.catalog);
        const records = this.mergeDuplicateSources(this.normalizeComponents(evidence.components));

        this.detectConflicts(records);
        this.registry = this.buildRegistry(records);
        this.writeReports(this.buildMigrationPlan(this.registry));

        utils.success(`Registry built: ${this.registry.length} records.`);
    }

    loadCatalog() {
        const catalogPath = path.join(config.paths.reports, "report-catalog.json");

        if (!utils.exists(catalogPath)) {
            return DEFAULT_CATALOG.map((entry) => ({
                ...entry,
                file: config.reports[entry.id] || null
            }));
        }

        const catalog = utils.readJSON(catalogPath);
        if (!catalog || !Array.isArray(catalog.reports)) {
            throw new Error(`Invalid report catalog: ${catalogPath}`);
        }

        return catalog.reports
            .filter((entry) => entry && entry.enabled !== false && entry.file && entry.type)
            .map((entry) => ({
                id: String(entry.id || entry.file),
                file: String(entry.file),
                type: String(entry.type),
                enabled: true
            }));
    }

    loadEvidence(catalog) {
        const evidence = { components: [] };

        for (const entry of catalog) {
            const reportPath = path.join(config.paths.reports, entry.file);
            const result = {
                id: entry.id,
                file: entry.file,
                type: entry.type,
                status: "ignored",
                records: 0
            };

            if (!utils.exists(reportPath)) {
                result.status = "missing";
                this.errors.push({ report: entry.file, message: "Report file does not exist." });
                this.catalogResults.push(result);
                continue;
            }

            const data = utils.readJSON(reportPath);
            if (data === null) {
                result.status = "invalid";
                this.catalogResults.push(result);
                continue;
            }

            if (entry.type === "component_evidence") {
                const records = Array.isArray(data) ? data : data.files;
                if (!Array.isArray(records)) {
                    result.status = "invalid";
                    this.errors.push({ report: entry.file, message: "Component evidence must be an array." });
                } else {
                    evidence.components.push(...records);
                    result.status = "loaded";
                    result.records = records.length;
                }
            } else {
                // Other reports are catalogued as evidence for future adapters.
                result.status = "catalogued";
                result.records = Array.isArray(data) ? data.length : (data.files || []).length;
            }

            this.catalogResults.push(result);
        }

        return evidence;
    }

    normalizeComponents(items) {
        return items.flatMap((item) => {
            if (!item?.component || !item?.source || !item?.target) {
                this.errors.push({ item, message: "Incomplete component record." });
                return [];
            }

            return [{
                component: String(item.component).trim(),
                source: this.normalizePath(item.source),
                target: this.normalizePath(item.target),
                fileType: item.fileType || "unknown",
                decision: item.decision || "REVIEW_REQUIRED",
                reasons: this.unique(item.reasons || [])
            }];
        });
    }

    mergeDuplicateSources(items) {
        const records = new Map();

        for (const item of items) {
            const key = `${item.component}|${item.target}`;
            const record = records.get(key) || {
                id: this.buildId(item.target),
                component: item.component,
                target: item.target,
                sources: [],
                decisions: [],
                reasons: [],
                fileTypes: []
            };

            this.add(record.sources, item.source);
            this.add(record.decisions, item.decision);
            this.add(record.fileTypes, item.fileType);
            for (const reason of item.reasons) this.add(record.reasons, reason);
            records.set(key, record);
        }

        return [...records.values()];
    }

    detectConflicts(records) {
        const targetsByComponent = new Map();

        for (const record of records) {
            const targets = targetsByComponent.get(record.component) || [];
            this.add(targets, record.target);
            targetsByComponent.set(record.component, targets);
        }

        for (const [component, targets] of targetsByComponent) {
            if (targets.length < 2) continue;

            this.conflicts.push({
                id: `conflict:component:${component}`,
                component,
                type: "multiple_targets",
                targets: this.sort(targets),
                sources: this.sort(this.unique(
                    records
                        .filter((record) => record.component === component)
                        .flatMap((record) => record.sources)
                )),
                review_required: true
            });
        }
    }

    buildRegistry(records) {
        const conflictedComponents = new Set(this.conflicts.map((conflict) => conflict.component));

        return records.map((record) => {
            const reviewRequired = conflictedComponents.has(record.component) || record.component === "Review Required";

            return {
                id: record.id,
                component: record.component,
                target: record.target,
                fingerprint: null,
                sources: this.sort(record.sources),
                decisions: this.sort(record.decisions),
                reasons: this.sort(record.reasons),
                file_types: this.sort(record.fileTypes),
                status: reviewRequired ? "review_required" : "pending",
                review_required: reviewRequired,
                conflicts: reviewRequired
                    ? this.conflicts.filter((conflict) => conflict.component === record.component)
                    : []
            };
        }).sort((left, right) => left.id.localeCompare(right.id));
    }

    buildMigrationPlan(registry) {
        const idByComponent = new Map(
            registry
                .filter((record) => !record.review_required)
                .map((record) => [record.component, record.id])
        );

        const tasks = registry
            .filter((record) => !record.review_required)
            .map((record) => ({
                id: record.id,
                phase: this.getPhase(record.target),
                component: record.component,
                target: record.target,
                status: "pending",
                priority: this.getPriority(record.target),
                sources: record.sources,
                decisions: record.decisions,
                reasons: record.reasons,
                dependencies: this.getDependencies(record.component, idByComponent)
            }))
            .sort((left, right) => left.phase - right.phase || left.component.localeCompare(right.component));

        return {
            generated_at: utils.timestamp(),
            engine: this.engine,
            created_by: "GREENY LIFE Migration Registry Builder",
            total_tasks: tasks.length,
            review_required: this.conflicts.length,
            tasks
        };
    }

    getDependencies(component, idByComponent) {
        const graph = {
            Navigation: ["Header"],
            Hero: ["Header"],
            Collections: ["Hero"],
            Features: ["Collections"],
            Packaging: ["Features"],
            Markets: ["Packaging"],
            Contact: ["Markets"],
            ProductCard: ["Collections"],
            CollectionCard: ["Collections"]
        };

        return (graph[component] || [])
            .map((dependency) => idByComponent.get(dependency))
            .filter(Boolean);
    }

    getPhase(target) {
        if (target.startsWith("components/layout/")) return 1;
        if (target.startsWith("components/sections/")) return 2;
        if (target.startsWith("components/cards/")) return 3;
        return 4;
    }

    getPriority(target) {
        if (target.startsWith("components/layout/")) return "critical";
        if (target.startsWith("components/sections/")) return "high";
        if (target.startsWith("components/cards/")) return "medium";
        return "low";
    }

    writeReports(plan) {
        const generatedAt = utils.timestamp();
        const reports = config.reports;
        const metadata = {
            generated_at: generatedAt,
            engine: this.engine,
            project: config.project.name,
            version: config.project.version,
            root: config.paths.root
        };

        utils.ensureDirectory(config.paths.reports);
        utils.writeJSON(
            path.join(config.paths.reports, reports.migrationRegistry || "migration-registry.json"),
            {
                ...metadata,
                total_records: this.registry.length,
                review_required: this.conflicts.length,
                records: this.registry
            }
        );
        utils.writeJSON(
            path.join(config.paths.reports, reports.migrationPlan || "legacy-migration-plan.json"),
            plan
        );
        utils.writeJSON(
            path.join(config.paths.reports, reports.migrationConflicts || "migration-conflicts.json"),
            {
                ...metadata,
                total_conflicts: this.conflicts.length,
                conflicts: this.conflicts,
                errors: this.errors
            }
        );
        utils.writeJSON(
            path.join(config.paths.reports, "report-catalog-results.json"),
            { ...metadata, reports: this.catalogResults }
        );
    }

    buildId(target) {
        const cleanTarget = this.normalizePath(target)
            .replace(/\.[^.]+$/, "")
            .replace(/[^a-zA-Z0-9]+/g, ":")
            .replace(/^:|:$/g, "");

        return `component:${cleanTarget}`;
    }

    normalizePath(value) {
        return String(value).trim().replace(/\\/g, "/");
    }

    unique(values) {
        return [...new Set(values.map((value) => String(value).trim()).filter(Boolean))];
    }

    add(values, value) {
        if (value && !values.includes(value)) values.push(value);
    }

    sort(values) {
        return [...values].sort((left, right) => left.localeCompare(right));
    }
}

if (require.main === module) {
    new MigrationRegistryBuilder().run();
}

module.exports = MigrationRegistryBuilder;
