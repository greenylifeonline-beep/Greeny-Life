const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");

const DATA_DIR = path.join(ROOT, "data");

const BACKUP_ROOT = path.join(ROOT, "backup");

/**
 * Create timestamp
 */
function getTimestamp() {
    const now = new Date();

    const yyyy = now.getFullYear();

    const mm = String(now.getMonth() + 1).padStart(2, "0");

    const dd = String(now.getDate()).padStart(2, "0");

    const hh = String(now.getHours()).padStart(2, "0");

    const min = String(now.getMinutes()).padStart(2, "0");

    const ss = String(now.getSeconds()).padStart(2, "0");

    return `${yyyy}-${mm}-${dd}_${hh}-${min}-${ss}`;
}

/**
 * Copy folder recursively
 */
function copyFolder(source, destination) {

    if (!fs.existsSync(destination)) {

        fs.mkdirSync(destination, {
            recursive: true
        });

    }

    const entries = fs.readdirSync(source, {
        withFileTypes: true
    });

    for (const entry of entries) {

        const sourcePath = path.join(source, entry.name);

        const destinationPath = path.join(destination, entry.name);

        if (entry.isDirectory()) {

            copyFolder(sourcePath, destinationPath);

        } else {

            fs.copyFileSync(sourcePath, destinationPath);

        }

    }

}

console.clear();

console.log("");

console.log("==========================================");
console.log(" GREENY LIFE Backup Tool");
console.log("==========================================");

if (!fs.existsSync(DATA_DIR)) {

    console.log("");

    console.log("ERROR:");

    console.log("Data folder not found.");

    process.exit(1);

}

if (!fs.existsSync(BACKUP_ROOT)) {

    fs.mkdirSync(BACKUP_ROOT);

}

const backupFolder = path.join(
    BACKUP_ROOT,
    getTimestamp()
);

copyFolder(DATA_DIR, backupFolder);

console.log("");

console.log("Backup created successfully.");

console.log("");

console.log("Location:");

console.log(backupFolder);

console.log("");

console.log("==========================================");

console.log("");