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

    let executed = new Set();
    let counter = 0;

    while (counter < this.autoLimit) {

        roadmap = this.readRoadmap();
        tasks = this.getTasks(roadmap);

        const next = this.findNextTask(tasks);

        if (!next) {
            utils.success("AUTO migration completed. No pending tasks.");
            return;
        }


        if (executed.has(next.id)) {
            utils.warning(
                `AUTO stopped: task repeated without progress: ${next.id}`
            );
            return;
        }


        executed.add(next.id);
        counter++;


        utils.success(
            `AUTO executing ${counter}: ${next.id}`
        );


        const beforeStatus = next.status;


        this.executeTask(
            next,
            roadmap,
            progress,
            tasks
        );


        const updatedRoadmap = this.readRoadmap();
        const updatedTasks = this.getTasks(updatedRoadmap);
        const updated = updatedTasks.find(
            t => t.id === next.id
        );


        if (!updated || updated.status === beforeStatus) {

            utils.warning(
                `AUTO stopped: ${next.id} was not marked completed.`
            );

            return;
        }

    }


    utils.warning(
        `AUTO stopped: safety limit ${this.autoLimit} reached.`
    );

    return;
}




        /*
         * SPECIFIC TASK MODE
         */

        if (!this.options.task) {
    utils.success("No task specified. Use --auto --apply or --task <id>.");
    return;
}

const task = tasks.find(
    (item) => item.id === this.options.task
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



        const completed = tasks.filter(
            item => item.status === "completed"
        ).length;


        Object.assign(progress, {

            current_phase: this.getCurrentPhase(tasks),

            current_task:
                this.findNextTask(tasks)?.id || null,

            completed,

            remaining:
                tasks.length - completed,


            percentage:
                tasks.length
                    ? Math.round(
                        (completed / tasks.length) * 100
                    )
                    : 100,


            started_at:
                progress.started_at || startedAt,


            updated_at:
                finishedAt
        });



        const history = this.readHistory();


        history.entries.push({

            task: task.id,

            status: "completed",

            executor: this.executor,

            started_at: startedAt,

            finished_at: finishedAt,

            duration_ms:
                task.duration_ms,


            created_files:
                createdFiles,


            source_files:
                task.sources || []

        });


        history.updated_at = finishedAt;


for (const phase of Object.values(roadmap.phases)) {

    const found = phase.tasks.find(
        t => t.id === task.id
    );

    if (found) {
        found.status = "completed";
        found.executor = this.executor;
        found.finished_at = finishedAt;
    }

}

        this.writeJSON(
            this.roadmapPath(),
            roadmap
        );


        this.writeJSON(
            this.progressPath(),
            progress
        );


        this.writeJSON(
            this.historyPath(),
            history
        );


        utils.success(
            `Completed ${task.id}`
        );
    }



    createTargets(task) {


        let target =
            task.target ||
            task.move_to;



        /*
         * Auto resolve file tasks
         *
         * Example:
         * file:data:06:markets:json
         *
         * becomes:
         * data/06_markets.json
         */

        if (!target && task.id.startsWith("file:")) {

            const parts = task.id
                .replace("file:", "")
                .split(":")
                .filter(Boolean);


            if (parts.length >= 2) {

                const ext = parts.pop();

                const rawName = parts.pop();


                let directory = parts.join("/");


                /*
                 * Convert numbered data files:
                 *
                 * data:06:markets:json
                 *
                 * to:
                 *
                 * data/06_markets.json
                 */

                if (
                    directory === "data" &&
                    /^\d+$/.test(rawName)
                ) {
                    // safety fallback
                    target =
                        `${directory}/${rawName}.${ext}`;
                }


                else if (
                    directory === "data" &&
                    /^\d+$/.test(parts[parts.length - 1])
                ) {

                    const number =
                        parts.pop();

                    const folder =
                        parts.join("/");

                    target =
                        `${folder}/${number}_${rawName}.${ext}`;
                }


                /*
                 * General files:
                 *
                 * app:assets:images:honey:jpg
                 *
                 * becomes:
                 *
                 * app/assets/images/honey.jpg
                 */

                else {

                    target =
                        `${directory}/${rawName}.${ext}`;
                }

            }
        }


        /*
         * Existing target protection
         */

        if (fs.existsSync(destination)) {

            utils.warning(
                `SKIP existing target: ${target}`
            );


            return [
                target.replace(/\\/g, "/")
            ];
        }



        fs.mkdirSync(
            path.dirname(destination),
            {
                recursive: true
            }
        );



        const componentName =
            String(
                task.component ||
                path.basename(
                    target,
                    path.extname(target)
                )
            )
            .replace(
                /[^a-zA-Z0-9_$]/g,
                ""
            )
            ||
            "MigratedComponent";



        let content;



        if (
            target.endsWith(".tsx")
        ) {


            content =
`/**
 * Migration task:
 * ${task.id}
 */

export function ${componentName}(){

    return (
        <section data-migration-id="${task.id}">
            ${componentName}
        </section>
    );
}


export default ${componentName};
`;

        }

        else if (
            target.endsWith(".json")
        ) {


            content =
JSON.stringify(
    {
        migration_task: task.id,
        created_at: utils.timestamp(),
        data: {}
    },
    null,
    2
);

        }

        else {


            content =
`Migration task:
${task.id}
`;

        }



        utils.writeFile(
            destination,
            content
        );



        return [
            target.replace(/\\/g, "/")
        ];

    }



    readRoadmap() {

        const roadmap = utils.readJSON(
            this.roadmapPath()
        );


        if (!roadmap || !roadmap.phases) {

            throw new Error(
                "Invalid or missing project roadmap."
            );
        }


        return roadmap;
    }



    readProgress(tasks) {

        const file =
            this.progressPath();


        if (utils.exists(file)) {

            return utils.readJSON(file);
        }


        return {

            current_phase:
                tasks[0]?.phase || null,

            current_task:
                tasks[0]?.id || null,

            completed: 0,

            remaining:
                tasks.length,

            percentage: 0,

            started_at: null,

            updated_at: null
        };
    }



    readHistory() {

        const file =
            this.historyPath();


        if (utils.exists(file)) {

            return utils.readJSON(file);
        }


        return {

            created_at:
                utils.timestamp(),

            updated_at: null,

            entries: []
        };
    }



    getTasks(roadmap) {

        return Object.entries(
            roadmap.phases
        )
        .flatMap(([key, phase]) => {

            return phase.tasks.map(task => ({

                ...task,

                phase:
                    task.phase ||
                    Number(
                        key.replace("phase", "")
                    )
            }));

        })
        .sort(
            (a,b) =>
                a.phase - b.phase ||
                a.id.localeCompare(b.id)
        );
    }



    findNextTask(tasks) {

        return tasks.find(task =>
            task.status === "pending" &&
            this.dependenciesComplete(
                task,
                tasks
            )
        );
    }



    dependenciesComplete(task,tasks) {

        const map =
            new Map(
                tasks.map(
                    item => [
                        item.id,
                        item
                    ]
                )
            );


        return (
            task.dependencies || []
        )
        .every(id =>
            map.get(id)?.status === "completed"
        );
    }



    getCurrentPhase(tasks) {

        return this.findNextTask(tasks)?.phase || null;
    }



    roadmapPath() {

        return path.join(
            config.paths.reports,
            config.reports.projectRoadmap
        );
    }



    progressPath() {

        return path.join(
            config.paths.reports,
            config.reports.migrationProgress
        );
    }



    historyPath() {

        return path.join(
            config.paths.reports,
            config.reports.migrationHistory
        );
    }



    writeJSON(file,value) {

        utils.writeJSON(
            file,
            value
        );
    }



    parseArgs(args) {

        const options = {

            task: null,

            apply:false,

            executor:null,

            auto:false
        };


        for (
            let i=0;
            i<args.length;
            i++
        ) {


            switch(args[i]) {


                case "--task":

                    options.task =
                        args[i+1] || null;

                    i++;

                    break;


                case "--apply":

                    options.apply = true;

                    break;


                case "--executor":

                    options.executor =
                        args[i+1] || null;

                    i++;

                    break;


                case "--auto":

                    options.auto = true;

                    break;
            }
        }


        return options;
    }

}



if (require.main === module) {

    new MigrationExecutor().run();

}



module.exports = MigrationExecutor;

