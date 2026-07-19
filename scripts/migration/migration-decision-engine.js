/** GREENY LIFE Migration Decision Engine */
"use strict";

const path = require("path");
const config = require("./config");
const utils = require("./utils");

class MigrationDecisionEngine {
    constructor() {
        this.engine = { name: "GREENY LIFE Migration Decision Engine", version: "1.0.0" };
        this.entities = new Map();
        this.files = new Map();
        this.errors = [];
    }

    run() {
        utils.title("GREENY LIFE Migration Decision Engine");
        const reports = this.loadReports();
        const planByTarget = new Map((reports.plan?.tasks || []).map((task) => [task.target, task]));

        this.applyRegistry(reports.registry, planByTarget);
        this.applyComponents(reports.components, planByTarget);
        this.applyClassifications(reports.refactor, "MOVE", "legacy_refactor");
        this.applyClassifications(reports.archive, "ARCHIVE", "legacy_archive");
        this.applyClassifications(reports.remove, "ARCHIVE", "legacy_remove");
        this.applyAssets(reports.assets);

        const result = this.buildResult();
        this.writeReports(result);
        this.writeRoadmap(this.buildProjectRoadmap(result));
        utils.success(`Decision report created: ${result.summary.files.total} files, ${result.summary.entities.total} entities.`);
    }

    loadReports() {
        const names = config.reports;
        return {
            registry: this.readReport(names.migrationRegistry),
            plan: this.readReport(names.migrationPlan),
            components: this.readReport(names.components),
            assets: this.readReport(names.assets),
            refactor: this.readReport(names.refactor),
            archive: this.readReport(names.archive),
            remove: this.readReport(names.remove)
        };
    }

    readReport(name) {
        const file = path.join(config.paths.reports, name);
        if (!utils.exists(file)) {
            this.errors.push({ report: name, message: "Report is missing." });
            return null;
        }
        return utils.readJSON(file);
    }

    applyRegistry(report, planByTarget) {
        for (const record of report?.records || []) {
            const task = planByTarget.get(record.target);
            const action = record.review_required ? "REVIEW_REQUIRED"
                : record.decisions?.includes("REFACTOR") ? "MOVE" : "KEEP";
            const entity = this.proposeEntity({
                id: record.id,
                entity: record.component,
                action,
                confidence: record.review_required ? 100 : 90,
                decisionSource: "migration_registry",
                moveTo: action === "MOVE" ? record.target : null,
                target: record.target,
                phase: task?.phase ?? null,
                reasons: record.reasons || []
            });

            for (const source of record.sources || []) {
                const fileAction = action === "REVIEW_REQUIRED"
                    ? "REVIEW_REQUIRED"
                    : this.isHtmlSource(source) ? "MIGRATE" : action;
                this.proposeFile({
                    file: source,
                    entity: entity.entity,
                    action: fileAction,
                    confidence: entity.confidence,
                    decisionSource: "migration_registry",
                    moveTo: fileAction === "MOVE" ? record.target : null,
                    phase: task?.phase ?? null,
                    reasons: record.reasons || []
                });
            }
        }
    }

    applyComponents(components, planByTarget) {
        for (const item of Array.isArray(components) ? components : []) {
            if (!item.source) continue;
            const task = planByTarget.get(item.target);
            const action = item.decision === "REFACTOR"
                ? "MOVE"
                : this.isHtmlSource(item.source) ? "MIGRATE" : "KEEP";
            this.proposeFile({
                file: item.source,
                entity: item.component || null,
                action,
                confidence: item.decision === "REFACTOR" ? 80 : 70,
                decisionSource: "legacy_components",
                moveTo: action === "MOVE" ? item.target || null : null,
                phase: task?.phase ?? null,
                reasons: item.reasons || []
            });
        }
    }

    applyClassifications(report, action, decisionSource) {
        for (const item of report?.files || []) {
            if (!item.file) continue;
            this.proposeFile({
                file: item.file,
                entity: null,
                action,
                confidence: action === "DELETE" ? 60 : 75,
                decisionSource,
                moveTo: null,
                phase: null,
                reasons: item.reasons || [`Classification decision: ${item.decision || action}.`]
            });
        }
    }

    applyAssets(assets) {
        for (const asset of Array.isArray(assets) ? assets : []) {
            if (!asset.file) continue;
            this.proposeFile({
                file: asset.file,
                entity: null,
                action: "KEEP",
                confidence: 85,
                decisionSource: "legacy_assets",
                moveTo: null,
                phase: null,
                reasons: ["Reusable legacy asset."]
            });
        }
    }

    proposeEntity(candidate) {
        return this.merge(this.entities, candidate, "entity");
    }

    proposeFile(candidate) {
        return this.merge(this.files, candidate, "file");
    }

    merge(store, candidate, keyName) {
        const key = keyName === "entity" ? candidate.id : this.normalizePath(candidate.file);
        const normalized = {
            ...candidate,
            file: candidate.file ? this.normalizePath(candidate.file) : undefined,
            moveTo: candidate.moveTo ? this.normalizePath(candidate.moveTo) : null,
            target: candidate.target ? this.normalizePath(candidate.target) : null,
            reasons: this.unique(candidate.reasons),
            fingerprint: null,
            approved: false,
            executor_status: "pending"
        };
        const current = store.get(key);
        if (!current) {
            store.set(key, normalized);
            return normalized;
        }

        current.action = this.resolveAction(current.action, normalized.action);
        current.confidence = Math.max(current.confidence, normalized.confidence);
        current.decisionsource = this.sourceFor(current.action, current.decisionSource, normalized.decisionSource);
        current.decisionSource = current.decisionsource;
        if (current.action === "MOVE" && !current.moveTo) current.moveTo = normalized.moveTo;
        if (!current.target) current.target = normalized.target;
        if (current.phase === null) current.phase = normalized.phase;
        if (!current.entity) current.entity = normalized.entity;
        for (const reason of normalized.reasons) this.addUnique(current.reasons, reason);
        return current;
    }

    resolveAction(left, right) {
        if (left === right) return left;
        if (left === "REVIEW_REQUIRED" || right === "REVIEW_REQUIRED") return "REVIEW_REQUIRED";
        if (left === "DELETE" || right === "DELETE") return "REVIEW_REQUIRED";
        if (left === "MIGRATE" || right === "MIGRATE") return "MIGRATE";
        if (left === "KEEP" || right === "KEEP") return "KEEP";
        return "REVIEW_REQUIRED";
    }

    sourceFor(action, current, candidate) {
        return action === "REVIEW_REQUIRED" ? "decision_conflict" : current || candidate;
    }

    buildResult() {
        const entityDecisions = this.serialize(this.entities, "entity");
        const fileDecisions = this.serialize(this.files, "file");
        return {
            generated_at: utils.timestamp(),
            engine: this.engine,
            project: config.project.name,
            version: config.project.version,
            root: config.paths.root,
            summary: {
                entities: this.summarize(entityDecisions),
                files: this.summarize(fileDecisions)
            },
            entities: entityDecisions,
            files: fileDecisions,
            errors: this.errors
        };
    }

    serialize(store, type) {
        return [...store.values()].map((item) => ({
            ...(type === "entity" ? { id: item.id, entity: item.entity, target: item.target } : { file: item.file, entity: item.entity }),
            action: item.action,
            confidence: item.confidence,
            decisionsource: item.decisionSource,
            move_to: item.moveTo,
            phase: item.phase,
            fingerprint: item.fingerprint,
            approved: item.approved,
            executor_status: item.executor_status,
            reasons: this.sort(item.reasons)
        })).sort((left, right) => (left.file || left.id).localeCompare(right.file || right.id));
    }

    summarize(records) {
        const count = (action) => records.filter((item) => item.action === action).length;
        return { total: records.length, keep: count("KEEP"), migrate: count("MIGRATE"), move: count("MOVE"), archive: count("ARCHIVE"), review_required: count("REVIEW_REQUIRED") };
    }

    writeReports(result) {
        const names = config.reports;
        utils.ensureDirectory(config.paths.reports);
        utils.writeJSON(path.join(config.paths.reports, names.projectDecisions), result);
        utils.writeJSON(path.join(config.paths.reports, names.cleanupActions), {
            generated_at: result.generated_at,
            engine: this.engine,
            project: config.project.name,
            keep: result.files.filter((item) => item.action === "KEEP"),
            migrate: result.files.filter((item) => item.action === "MIGRATE"),
            move: result.files.filter((item) => item.action === "MOVE"),
            archive: result.files.filter((item) => item.action === "ARCHIVE"),
            review_required: result.files.filter((item) => item.action === "REVIEW_REQUIRED")
        });
    }

    buildProjectRoadmap(result) {
        const phases = {
            phase1: { title: "Layout", tasks: [] },
            phase2: { title: "Sections", tasks: [] },
            phase3: { title: "Cards", tasks: [] },
            phase4: { title: "Data", tasks: [] },
            phase5: { title: "Assets", tasks: [] }
        };

        for (const entity of result.entities) {
            if (!["KEEP", "MIGRATE", "MOVE"].includes(entity.action)) continue;
            if (entity.phase >= 1 && entity.phase <= 3) {
                phases[`phase${entity.phase}`].tasks.push(this.toRoadmapTask(entity));
            }
        }

        phases.phase4.tasks = result.files.filter((item) =>
            item.action === "MOVE" && (item.file.startsWith("data/") || item.file.startsWith("lib/data/"))
        ).map((item) => this.toRoadmapTask(item));
        phases.phase5.tasks = result.files.filter((item) =>
            ["KEEP", "MIGRATE"].includes(item.action) &&
            (item.file.startsWith("app/assets/") || item.file.startsWith("public/"))
        ).map((item) => this.toRoadmapTask(item));

        return {
            generated_at: utils.timestamp(),
            engine: this.engine,
            project: config.project.name,
            phases
        };
    }

    writeRoadmap(roadmap) {
        utils.writeJSON(
            path.join(config.paths.reports, config.reports.projectRoadmap || "project-roadmap.json"),
            roadmap
        );
    }

    toRoadmapTask(item) {
        return {
            ...item,
            id: item.id || `file:${this.normalizePath(item.file).replace(/[^a-zA-Z0-9]+/g, ":")}`,
            target: item.target || item.move_to || null,
            status: "pending",
            executor: null,
            started_at: null,
            finished_at: null,
            duration_ms: 0
        };
    }

    isHtmlSource(file) {
        return /\.html?$/i.test(file);
    }

    normalizePath(value) { return String(value).trim().replace(/\\/g, "/"); }
    unique(values) { return [...new Set((values || []).map(String).map((item) => item.trim()).filter(Boolean))]; }
    addUnique(values, value) { if (value && !values.includes(value)) values.push(value); }
    sort(values) { return [...values].sort((left, right) => left.localeCompare(right)); }
}

if (require.main === module) new MigrationDecisionEngine().run();

module.exports = MigrationDecisionEngine;
