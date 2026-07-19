/**
 * GREENY LIFE Migration Executor
 *
 * Usage:
 *   npm run executor                         # show next executable task
 *   node scripts/migration/migration-executor.js --task <id> --apply
 *
 * The executor never overwrites existing files. It creates a small, valid
 * component scaffold, records its source evidence, and updates roadmap,
 * progress and history atomically through JSON reports.
 */

"use strict";

const fs = require("fs");
const path = require("path");

const config = require("./config");
const utils = require("./utils");

class MigrationExecutor {
    constructor(args = process.argv.slice(2)) {
        this.options = this.parseArgs(args);
        this.executor = this.options.executor || "migration-executor";
    }

    run() {
        const roadmap = this.readRoadmap();
        const tasks = this.getTasks(roadmap);
        const progress = this.readProgress(tasks);

        if (!this.options.task) {
            const next = this.findNextTask(tasks);
            utils.title("GREENY LIFE Migration Executor");
            if (next) {
                utils.success(`Next task: ${next.id} (${next.component || next.file || next.target})`);
            } else {
                utils.success("No executable pending task found.");
            }
            return;
        }

        const task = tasks.find((item) => item.id === this.options.task);
        if (!task) throw new Error(`Task not found: ${this.options.task}`);
        if (task.status === "completed") throw new Error(`Task is already completed: ${task.id}`);
        if (!this.dependenciesComplete(task, tasks)) throw new Error(`Dependencies are not complete for: ${task.id}`);

        if (!this.options.apply) {
            utils.warning(`Preview only. Run again with --apply to execute ${task.id}.`);
            return;
        }

        this.executeTask(task, roadmap, progress, tasks);
    }

    executeTask(task, roadmap, progress, tasks) {
        const started = Date.now();
        const startedAt = utils.timestamp();
        const createdFiles = this.createTargets(task);
        const finishedAt = utils.timestamp();

        task.status = "completed";
        task.executor = this.executor;
        task.started_at = startedAt;
        task.finished_at = finishedAt;
        task.duration_ms = Date.now() - started;

        const completed = tasks.filter((item) => item.status === "completed").length;
        Object.assign(progress, {
            current_phase: this.getCurrentPhase(tasks),
            current_task: this.findNextTask(tasks)?.id || null,
            completed,
            remaining: tasks.length - completed,
            percentage: tasks.length ? Math.round((completed / tasks.length) * 100) : 100,
            started_at: progress.started_at || startedAt,
            updated_at: finishedAt
        });

        const history = this.readHistory();
        history.entries.push({
            task: task.id,
            status: "completed",
            executor: this.executor,
            started_at: startedAt,
            finished_at: finishedAt,
            duration_ms: task.duration_ms,
            created_files: createdFiles,
            source_files: task.sources || []
        });
        history.updated_at = finishedAt;

        this.writeJSON(this.roadmapPath(), roadmap);
        this.writeJSON(this.progressPath(), progress);
        this.writeJSON(this.historyPath(), history);
        utils.success(`Completed ${task.id}.`);
    }

    createTargets(task) {
        const target = task.target || task.move_to;
        if (!target) throw new Error(`Task has no implementation target: ${task.id}`);

        const destination = path.resolve(config.paths.root, target);
        const root = path.resolve(config.paths.root);
        if (!destination.startsWith(`${root}${path.sep}`)) throw new Error("Target escapes the project root.");
        if (fs.existsSync(destination)) throw new Error(`Target already exists: ${target}`);

        const sourceComment = (task.sources || []).map((source) => ` * - ${source}`).join("\n");
        const componentName = String(task.component || path.basename(target, path.extname(target)))
            .replace(/[^a-zA-Z0-9_$]/g, "") || "MigratedComponent";
        const content = [
            "/**",
            ` * Migration task: ${task.id}`,
            " * Legacy sources:",
            sourceComment || " * - None recorded",
            " */",
            "",
            `export function ${componentName}() {`,
            `    return <section data-migration-id=${JSON.stringify(task.id)} />;`,
            "}",
            "",
            `export default ${componentName};`,
            ""
        ].join("\n");

        utils.writeFile(destination, content);
        return [target.replace(/\\/g, "/")];
    }

    readRoadmap() {
        const roadmap = utils.readJSON(this.roadmapPath());
        if (!roadmap?.phases) throw new Error("Invalid or missing project roadmap.");
        return roadmap;
    }

    readProgress(tasks) {
        const existing = utils.exists(this.progressPath()) ? utils.readJSON(this.progressPath()) : null;
        return existing || {
            current_phase: tasks[0]?.phase || null,
            current_task: tasks[0]?.id || null,
            completed: 0,
            remaining: tasks.length,
            percentage: 0,
            started_at: null,
            updated_at: null
        };
    }

    readHistory() {
        const existing = utils.exists(this.historyPath()) ? utils.readJSON(this.historyPath()) : null;
        return existing || { created_at: utils.timestamp(), updated_at: null, entries: [] };
    }

    getTasks(roadmap) {
        return Object.entries(roadmap.phases)
            .flatMap(([key, phase]) => phase.tasks.map((task) => ({
                ...task,
                phase: task.phase || Number(key.replace("phase", ""))
            })))
            .sort((left, right) => left.phase - right.phase || left.id.localeCompare(right.id));
    }

    findNextTask(tasks) {
        return tasks.find((task) => task.status === "pending" && this.dependenciesComplete(task, tasks));
    }

    dependenciesComplete(task, tasks) {
        const byId = new Map(tasks.map((item) => [item.id, item]));
        return (task.dependencies || []).every((id) => byId.get(id)?.status === "completed");
    }

    getCurrentPhase(tasks) {
        return this.findNextTask(tasks)?.phase || null;
    }

    roadmapPath() { return path.join(config.paths.reports, config.reports.projectRoadmap); }
    progressPath() { return path.join(config.paths.reports, config.reports.migrationProgress); }
    historyPath() { return path.join(config.paths.reports, config.reports.migrationHistory); }
    writeJSON(file, value) { utils.writeJSON(file, value); }

    parseArgs(args) {
        const options = { task: null, apply: false, executor: null };
        for (let index = 0; index < args.length; index += 1) {
            if (args[index] === "--task") options.task = args[index + 1] || null;
            if (args[index] === "--apply") options.apply = true;
            if (args[index] === "--executor") options.executor = args[index + 1] || null;
        }
        return options;
    }
}

if (require.main === module) new MigrationExecutor().run();

module.exports = MigrationExecutor;
