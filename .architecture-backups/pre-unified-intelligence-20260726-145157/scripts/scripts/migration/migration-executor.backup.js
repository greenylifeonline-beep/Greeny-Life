/**
 * GREENY LIFE Migration Executor
 *
 * Supports:
 *   npm run executor
 *   node scripts/migration/migration-executor.js --task <id> --apply
 *   node scripts/migration/migration-executor.js --auto --apply
 *
 * Safe execution:
 * - Never overwrites existing files
 * - Supports interrupted migrations
 * - Updates roadmap/progress/history
 * - Prevents duplicate execution loops
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
        this.autoLimit = 500;
    }


    run() {

        let roadmap = this.readRoadmap();
        let tasks = this.getTasks(roadmap);
        let progress = this.readProgress(tasks);


        /*
         * AUTO MODE
         */
        if (this.options.auto && this.options.apply) {

            let counter = 0;

            while (counter < this.autoLimit) {

                roadmap = this.readRoadmap();
                tasks = this.getTasks(roadmap);

                const next = this.findNextTask(tasks);

                if (!next) {
                    utils.success("AUTO migration completed. No pending tasks.");
                    return;
                }


                counter++;

                utils.success(
                    `AUTO executing ${counter}/${this.autoLimit}: ${next.id}`
                );


                try {

                    this.executeTask(
                        next,
                        roadmap,
                        progress,
                        tasks
                    );


                } catch (error) {

                    utils.warning(
                        `AUTO stopped at ${next.id}`
                    );

                    throw error;
                }


                progress = this.readProgress(tasks);
            }


            utils.warning(
                "AUTO stopped because safety limit was reached."
            );

            return;
        }



        /*
         * NORMAL MODE - SHOW NEXT TASK
         */
        if (!this.options.task) {

            const next = this.findNextTask(tasks);

            utils.title(
                "GREENY LIFE Migration Executor"
            );


            if (next) {

                utils.success(
                    `Next task: ${next.id} (${next.component || next.file || next.target || "unknown"})`
                );

            } else {

                utils.success(
                    "No executable pending task found."
                );
            }


            return;
        }



        /*
         * SPECIFIC TASK MODE
         */

        const task = tasks.find(
            item => item.id === this.options.task
        );


        if (!task) {

            throw new Error(
                `Task not found: ${this.options.task}`
            );
        }


        if (task.status === "completed") {

            utils.warning(
                `Task already completed: ${task.id}`
            );

            return;
        }


        if (!this.dependenciesComplete(task, tasks)) {

            throw new Error(
                `Dependencies are not complete for: ${task.id}`
            );
        }


        if (!this.options.apply) {

            utils.warning(
                `Preview only. Use --apply for ${task.id}`
            );

            return;
        }


        this.executeTask(
            task,
            roadmap,
            progress,
            tasks
        );

    }
