/**
 * ============================================================
 * GREENY LIFE
 * Legacy Migration Engine
 * ------------------------------------------------------------
 * File:
 * scripts/migration/config.js
 * ============================================================
 */

const path = require("path");

const ROOT = process.cwd();

module.exports = {

    project: {

        name: "GREENY LIFE",

        version: "1.0.0"

    },

    paths: {

    root: ROOT,

    reports: path.join(ROOT, "reports"),

    sources: [

        path.join(ROOT, "app"),

        path.join(ROOT, "data"),

        path.join(ROOT, "components"),

        path.join(ROOT, "lib"),

        path.join(ROOT, "public")

    ]

},

    
ignoreFolders: [

    ".git",

    ".next",

    "node_modules",

    "backup",

    "reports"

],
ignoreFiles: [

    ".DS_Store",

    "Thumbs.db"

],

    extensions: {

        html: [".html"],

        css: [".css"],

        javascript: [

            ".js"

        ],

        typescript: [

            ".ts",

            ".tsx"

        ],

        json: [

            ".json"

        ],

        images: [

            ".png",

            ".jpg",

            ".jpeg",

            ".svg",

            ".webp",

            ".gif",

            ".avif"

        ],

        fonts: [

            ".woff",

            ".woff2",

            ".ttf",

            ".otf"

        ]

    },

    analysis: {

        detectDOM: true,

        detectFetch: true,

        detectEvents: true,

        detectBusinessLogic: true,

        detectAssets: true,

        detectSections: true,

        detectComponents: true,

        detectCSSVariables: true

    },

    reports: {

    summary: "legacy-summary.json",

    components: "legacy-components.json",

    assets: "legacy-assets.json",

    progress: "legacy-progress.json",

    refactor: "legacy-refactor.json",

    archive: "legacy-archive.json",

    remove: "legacy-remove.json",

    reportCatalog: "report-catalog.json",

    migrationRegistry: "migration-registry.json",

    migrationPlan: "legacy-migration-plan.json",

    migrationConflicts: "migration-conflicts.json",

    projectDecisions: "project-decisions.json",

    cleanupActions: "cleanup-actions.json",

    projectRoadmap: "project-roadmap.json",

    migrationProgress: "migration-progress.json",

    migrationHistory: "migration-history.json"

},
    score: {

        businessLogic: 40,

        reusableFunction: 20,

        reusableAssets: 15,

        designSystem: 15,

        legacyOnly: -20,

        domManipulation: -15,

        htmlRendering: -20

    }


};
