/**
 * ============================================================
 * GREENY LIFE - Legacy Migration Engine Utilities
 * File: scripts/migration/utils.js
 * ============================================================
 */

"use strict";

const fs = require("fs");
const path = require("path");

const config = require("./config");

const IGNORE_FOLDERS = new Set(config.ignoreFolders || []);
const IGNORE_FILES = new Set(config.ignoreFiles || []);

/** Returns an ISO-8601 timestamp for report metadata and logs. */
function timestamp() {
    return new Date().toISOString();
}

/** Returns true when a path exists. */
function exists(target) {
    return fs.existsSync(target);
}

/** Creates a directory and every missing parent directory. */
function ensureDirectory(target) {
    if (!target) {
        throw new TypeError("A directory path is required.");
    }

    fs.mkdirSync(target, { recursive: true });
}

/** Reads a UTF-8 text file. Errors are intentionally propagated to the caller. */
function readFile(file) {
    return fs.readFileSync(file, "utf8");
}

/** Writes UTF-8 text, creating the destination directory when necessary. */
function writeFile(file, content) {
    if (!file) {
        throw new TypeError("A file path is required.");
    }

    ensureDirectory(path.dirname(file));
    fs.writeFileSync(file, String(content), "utf8");
}

/** Reads and parses a JSON file. Returns null when the JSON is invalid. */
function readJSON(file) {
    try {
        return JSON.parse(readFile(file));
    } catch (cause) {
        warning(`Cannot read valid JSON: ${relative(file)} (${cause.message})`);
        return null;
    }
}

/** Serializes an object as consistently formatted JSON without mutating it. */
function writeJSON(file, value) {
    if (value === undefined) {
        throw new TypeError("Cannot write an undefined JSON value.");
    }

    const output = JSON.stringify(value, null, 2);

    writeFile(file, `${output}\n`);
}

/** Returns a lowercase extension, including the leading dot. */
function extension(file) {
    return path.extname(file).toLowerCase();
}

/** Returns true when a file has one of the supplied extensions. */
function hasExtension(file, extensions) {
    if (!Array.isArray(extensions)) {
        return false;
    }

    return extensions.map((item) => String(item).toLowerCase()).includes(extension(file));
}

/** Returns true when a file or directory name is configured to be ignored. */
function ignored(name, isDirectory = false) {
    return isDirectory ? IGNORE_FOLDERS.has(name) : IGNORE_FILES.has(name);
}

/**
 * Recursively visits each non-ignored file beneath a directory.
 * Symbolic links are ignored to prevent traversal cycles.
 */
function walk(directory, callback) {
    if (typeof callback !== "function") {
        throw new TypeError("walk requires a callback function.");
    }

    let entries;
    try {
        entries = fs.readdirSync(directory, { withFileTypes: true });
    } catch (cause) {
        warning(`Cannot read directory: ${directory} (${cause.message})`);
        return;
    }

    entries.sort((left, right) => left.name.localeCompare(right.name));

    for (const entry of entries) {
        if (entry.isSymbolicLink() || ignored(entry.name, entry.isDirectory())) {
            continue;
        }

        const fullPath = path.join(directory, entry.name);
        if (entry.isDirectory()) {
            walk(fullPath, callback);
        } else if (entry.isFile()) {
            callback(fullPath);
        }
    }
}

/** Returns a normalized path relative to the configured project root. */
function relative(file) {
    const relativePath = path.relative(config.paths.root, file);

    return path.normalize(relativePath);
}

/** Returns a file size in bytes. */
function size(file) {
    return fs.statSync(file).size;
}

/** Returns true when a file has no bytes. */
function empty(file) {
    return size(file) === 0;
}

/** Creates the standard base structure used by report files. */
function report(name) {
    return {
        project: config.project.name,
        report: name,
        generated_at: timestamp(),
        items: []
    };
}

/** Adds an item to a report, validating its expected shape. */
function add(reportObject, item) {
    if (!reportObject || !Array.isArray(reportObject.items)) {
        throw new TypeError("Report object must contain an items array.");
    }

    reportObject.items.push(item);
}

/** Writes a report to the configured reports directory. */
function saveReport(name, reportObject) {
    if (!name) {
        throw new TypeError("A report name is required.");
    }

    writeJSON(path.join(config.paths.reports, name), reportObject);
}

function title(text) {
    console.log(`\n========================================\n${text}\n========================================`);
}

function success(text) {
    console.log(`[SUCCESS] ${text}`);
}

function warning(text) {
    console.warn(`[WARNING] ${text}`);
}

function error(text) {
    console.error(`[ERROR] ${text}`);
}

module.exports = {
    exists,
    ensureDirectory,
    readFile,
    writeFile,
    readJSON,
    writeJSON,
    extension,
    hasExtension,
    ignored,
    walk,
    relative,
    size,
    empty,
    report,
    add,
    saveReport,
    title,
    success,
    warning,
    error,
    timestamp
};
