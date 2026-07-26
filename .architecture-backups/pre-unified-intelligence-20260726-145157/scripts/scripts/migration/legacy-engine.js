"use strict";

const path = require("path");
const config = require("./config");
const utils = require("./utils");

const extensions = config.extensions || {};
const TEXT_EXTENSIONS = new Set([
    ...(extensions.html || [".html"]),
    ...(extensions.css || [".css"]),
    ...(extensions.javascript || [".js"]),
    ...(extensions.typescript || []),
    ...(extensions.json || [".json"])
].map((item) => String(item).toLowerCase()));

class LegacyMigrationEngine {
    constructor() {
        this.engine = { name: "Legacy Migration Engine", version: "1.1.0" };
        this.errors = [];
        this.files = [];
        this.components = [];
        this.assets = [];
        this.reuse = [];
        this.refactor = [];
        this.archive = [];
        this.remove = [];
        this.summary = {
            project: config.project.name,
            version: config.project.version,
            generated_at: utils.timestamp(),
            engine: this.engine,
            project_fingerprint: {
                root: config.paths.root,
                scanned_sources: this.getSourcePaths(),
                generated_by: "GREENY LIFE Enterprise Migration Engine"
            },
            statistics: {
                total_files: 0, html: 0, css: 0, javascript: 0,
                json: 0, images: 0, fonts: 0, others: 0
            },
            score: { reusable: 0, refactor: 0, archive: 0, remove: 0 },
            errors: this.errors
        };
    }

    run() {
        const started = Date.now();
        utils.title("GREENY LIFE Legacy Migration Engine");
        this.scanLegacyProject();
        this.analyzeFiles();
        this.classifyFiles();
        this.summary.execution_time_ms = Date.now() - started;
        this.generateReports();
        utils.success("Migration analysis completed.");
    }

    getSourcePaths() {
        const configured = Array.isArray(config.paths.sources)
            ? config.paths.sources
            : [config.paths.legacy];
        const sources = [...new Set(configured.filter(Boolean).map(path.normalize))];
        if (!sources.length) throw new Error("No legacy source directory is configured.");
        return sources;
    }

    scanLegacyProject() {
        utils.title("Scanning Legacy Project...");
        for (const source of this.getSourcePaths()) {
            utils.walk(source, (filePath) => {
                this.files.push(path.normalize(filePath));
                this.summary.statistics.total_files += 1;
            });
        }
        utils.success(`${this.files.length} files discovered.`);
    }

    analyzeFiles() {
        utils.title("Analyzing Legacy Files...");
        this.files = this.files.map((filePath) => this.analyzeFile(filePath));
        utils.success("Files analyzed successfully.");
    }

    analyzeFile(filePath) {
        const extension = utils.extension(filePath);
        const type = this.getFileType(filePath, extension);
        const relative = utils.relative(filePath);
        let content = "";
        let size = 0;
        if (TEXT_EXTENSIONS.has(extension)) {
            try { content = utils.readFile(filePath); } catch (error) { this.recordError(relative, error.message); }
        }
        try { size = utils.size(filePath); } catch (error) { this.recordError(relative, `Cannot read file size: ${error.message}`); }

        const item = {
            file: filePath, relative, extension, size, type, content,
            analysis: {
                hasDOM: false, hasFetch: false, hasEvents: false, hasJSON: false,
                hasBusinessLogic: false, hasComponents: false, hasSections: false,
                hasCSSVariables: false, hasAssets: false
            }
        };
        const statisticKey = this.getStatisticKey(type);
        if (Object.hasOwn(this.summary.statistics, statisticKey)) this.summary.statistics[statisticKey] += 1;

        if (type === "html") {
            item.analysis.hasSections = /<section\b/i.test(content);
            item.analysis.hasComponents = /<(header|footer|nav|main)\b/i.test(content);
        } else if (type === "css") {
            item.analysis.hasCSSVariables = /--[\w-]+\s*:/.test(content);
        } else if (type === "javascript") {
            item.analysis.hasDOM = /querySelector|getElementById|createElement|appendChild|innerHTML|classList/.test(content);
            item.analysis.hasFetch = /\bfetch\s*\(/.test(content);
            item.analysis.hasEvents = /addEventListener|removeEventListener/.test(content);
            item.analysis.hasJSON = /JSON\.(parse|stringify)/.test(content);
            item.analysis.hasBusinessLogic = /\.(filter|map|reduce|sort|find|includes|some|every)\s*\(/.test(content);
        } else if (type === "image") {
            item.analysis.hasAssets = true;
            this.assets.push({ file: relative, extension });
        }
        return item;
    }

    recordError(file, message) {
        this.errors.push({ file, message });
        utils.warning(`${file}: ${message}`);
    }

    getFileType(filePath, extension) {
        if (utils.hasExtension(filePath, extensions.html || [".html"])) return "html";
        if (utils.hasExtension(filePath, extensions.css || [".css"])) return "css";
        if (utils.hasExtension(filePath, extensions.javascript || [".js"])) return "javascript";
        if (utils.hasExtension(filePath, extensions.typescript || [])) return "javascript";
        if (utils.hasExtension(filePath, extensions.json || [".json"])) return "json";
        if (utils.hasExtension(filePath, extensions.images || [])) return "image";
        if (utils.hasExtension(filePath, extensions.fonts || [])) return "font";
        return { ".html": "html", ".css": "css", ".js": "javascript", ".json": "json" }[extension] || "other";
    }

    getStatisticKey(type) {
        return { html: "html", css: "css", javascript: "javascript", json: "json", image: "images", font: "fonts", other: "others" }[type];
    }

    classifyFiles() {
        utils.title("Classifying Legacy Files...");
        for (const file of this.files) {
            const classification = this.scoreFile(file);
            file.classification = classification;
            this.storeClassification(classification);
            this.detectComponents(file, classification);
        }
        utils.success("Classification completed.");
    }

    scoreFile(file) {
        const result = { score: 0, reasons: [] };
        const { type, analysis } = file;
        if (type === "html") {
            result.score += 30; result.reasons.push("HTML page detected.");
            if (analysis.hasSections) { result.score += 20; result.reasons.push("Contains reusable sections."); }
            if (analysis.hasComponents) { result.score += 20; result.reasons.push("Contains reusable layout."); }
        } else if (type === "css") {
            result.score += 25; result.reasons.push("Stylesheet detected.");
            if (analysis.hasCSSVariables) { result.score += 25; result.reasons.push("Uses CSS variables."); }
        } else if (type === "javascript") {
            for (const [key, points, reason] of [
                ["hasBusinessLogic", 40, "Business logic detected."],
                ["hasFetch", 20, "Fetch API detected."],
                ["hasEvents", 10, "Events detected."],
                ["hasJSON", 10, "JSON processing detected."],
                ["hasDOM", -10, "DOM manipulation requires migration."]
            ]) if (analysis[key]) { result.score += points; result.reasons.push(reason); }
        } else if (type === "json") {
            result.score += 60; result.reasons.push("Business data detected.");
        } else if (type === "image" || type === "font") {
            result.score += 50; result.reasons.push(type === "image" ? "Reusable asset." : "Reusable font.");
        }
        const decision = result.score >= 70 ? "REUSE" : result.score >= 40 ? "REFACTOR" : result.score >= 10 ? "ARCHIVE" : "DELETE";
        return { file: file.relative, type, score: result.score, decision, reasons: result.reasons };
    }

    storeClassification(classification) {
        const buckets = {
            REUSE: [this.reuse, "reusable"], REFACTOR: [this.refactor, "refactor"],
            ARCHIVE: [this.archive, "archive"], DELETE: [this.remove, "remove"]
        };
        const bucket = buckets[classification.decision];
        if (!bucket) {
            this.recordError(classification.file, `Unknown classification: ${classification.decision}`);
            return;
        }
        const [files, summaryKey] = bucket;
        files.push(classification);
        this.summary.score[summaryKey] += 1;
    }

    detectComponents(file, classification) {
        const candidate = file.type === "html" || (file.type === "javascript" && (file.analysis.hasDOM || file.analysis.hasEvents || file.analysis.hasFetch));
        if (!candidate) return;
        const content = file.content || "";
        const definitions = [
            [/<header\b/i, "Header", "components/layout/Header.tsx"],
            [/<footer\b/i, "Footer", "components/layout/Footer.tsx"],
            [/<nav\b/i, "Navigation", "components/layout/Navigation.tsx"],
            [/<(?:section|div)\b[^>]*\bclass\s*=\s*["'][^"']*\bhero\b[^"']*["']/i, "Hero", "components/sections/Hero.tsx"],
            [/<(?:section|div)\b[^>]*\bclass\s*=\s*["'][^"']*\bcollections?\b[^"']*["']/i, "Collections", "components/sections/Collections.tsx"],
            [/<(?:section|div)\b[^>]*\bclass\s*=\s*["'][^"']*\bfeatures?\b[^"']*["']/i, "Features", "components/sections/Features.tsx"],
            [/<(?:section|div)\b[^>]*\bclass\s*=\s*["'][^"']*\bpackaging\b[^"']*["']/i, "Packaging", "components/sections/Packaging.tsx"],
            [/<(?:section|div)\b[^>]*\bclass\s*=\s*["'][^"']*\bmarkets?\b[^"']*["']/i, "Markets", "components/sections/Markets.tsx"],
            [/<(?:section|div)\b[^>]*\bclass\s*=\s*["'][^"']*\bcontact\b[^"']*["']/i, "Contact", "components/sections/Contact.tsx"],
            [/<(?:article|div|li)\b[^>]*\bclass\s*=\s*["'][^"']*\bproduct-card\b[^"']*["']/i, "ProductCard", "components/cards/ProductCard.tsx"],
            [/<(?:article|div|li)\b[^>]*\bclass\s*=\s*["'][^"']*\b(?:collection-card|category-card)\b[^"']*["']/i, "CollectionCard", "components/cards/CollectionCard.tsx"]
        ];
        let detected = false;
        for (const [pattern, component, target] of definitions) {
            if (!pattern.test(content)) continue;
            detected = true;
            this.addComponent(file, classification, component, target);
        }
        if (!detected) this.addComponent(file, classification, "Review Required", "Manual review required");
    }

    addComponent(file, classification, component, target) {
        if (this.components.some((item) => item.source === file.relative && item.component === component)) return;
        this.components.push({ component, source: file.relative, target, fileType: file.type, score: classification.score, decision: classification.decision, reasons: classification.reasons, status: "pending" });
    }

    generateReports() {
        const generatedAt = utils.timestamp();
        const reportsPath = config.paths.reports;
        const names = config.reports;
        const total = this.files.length;
        const reports = {
            summary: this.summary, components: this.components, assets: this.assets,
            refactor: this.createListReport(generatedAt, this.refactor),
            archive: this.createListReport(generatedAt, this.archive),
            remove: this.createListReport(generatedAt, this.remove),
            progress: { generated_at: generatedAt, total_files: total, reusable: this.reuse.length, refactor: this.refactor.length, archive: this.archive.length, remove: this.remove.length, completion: `${total ? Math.round((this.reuse.length / total) * 100) : 0}%` }
        };
        utils.ensureDirectory(reportsPath);
        for (const [name, report] of Object.entries(reports)) utils.writeJSON(path.join(reportsPath, names[name]), report);
        utils.writeJSON(path.join(reportsPath, names.migrationPlan || "legacy-migration-plan.json"), this.createMigrationPlan(generatedAt));
        utils.success("Reports saved successfully.");
    }

    createListReport(generatedAt, files) {
        return { generated_at: generatedAt, total: files.length, files, created_by: "GREENY LIFE Migration Engine" };
    }

    createMigrationPlan(generatedAt) {
        const tasks = new Map();
        for (const component of this.components) {
            if (component.component === "Review Required") continue;
            const key = `${component.component}:${component.target}`;
            const task = tasks.get(key) || { phase: this.getMigrationPhase(component.target), component: component.component, target: component.target, status: "pending", priority: this.getMigrationPriority(component), sources: [], decisions: [], reasons: [] };
            if (!task.sources.includes(component.source)) task.sources.push(component.source);
            if (!task.decisions.includes(component.decision)) task.decisions.push(component.decision);
            for (const reason of component.reasons) if (!task.reasons.includes(reason)) task.reasons.push(reason);
            if (this.getPriorityWeight(component) > this.getPriorityWeight(task)) task.priority = this.getMigrationPriority(component);
            tasks.set(key, task);
        }
        const compare = (left, right) => left.localeCompare(right);
        const plan = [...tasks.values()].map((task) => ({ ...task, sources: task.sources.sort(compare), decisions: task.decisions.sort(compare), reasons: task.reasons.sort(compare) })).sort((left, right) => left.phase - right.phase || left.component.localeCompare(right.component));
        return { generated_at: generatedAt, engine: this.engine, created_by: "GREENY LIFE Enterprise Migration Engine", total_tasks: plan.length, tasks: plan };
    }

    getMigrationPhase(target) {
        if (target.startsWith("components/layout/")) return 1;
        if (target.startsWith("components/sections/")) return 2;
        if (target.startsWith("components/cards/")) return 3;
        return 4;
    }

    getMigrationPriority(component) {
        if (component.target.startsWith("components/layout/")) return "critical";
        if (component.target.startsWith("components/sections/")) return "high";
        if (component.target.startsWith("components/cards/")) return "medium";
        return component.decision === "DELETE" ? "low" : "medium";
    }

    getPriorityWeight(component) {
        const priority = component.priority || this.getMigrationPriority(component);
        return { critical: 4, high: 3, medium: 2, low: 1 }[priority] || 0;
    }
}

if (require.main === module) new LegacyMigrationEngine().run();

module.exports = LegacyMigrationEngine;