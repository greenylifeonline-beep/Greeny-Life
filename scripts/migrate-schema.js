const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ROOT = path.join(__dirname, "..");

const DATA = path.join(ROOT, "data");

const REPORTS = path.join(ROOT, "reports");

const APPLY = process.argv.includes("--apply");

const REPORT = {
    date: new Date().toISOString(),
    success: true,
    files: [],
    warnings: [],
    errors: []
};

if (!fs.existsSync(REPORTS)) {
    fs.mkdirSync(REPORTS);
}

if (APPLY) {

    console.log("Creating backup...\n");

    execSync(
        "node scripts/backup-data.js",
        {
            stdio: "inherit"
        }
    );

}

console.log("GREENY LIFE Migration\n");

function save(file, json) {

    fs.writeFileSync(

        path.join(DATA, file),

        JSON.stringify(json, null, 2)

    );

}

function addSortOrder(items) {

    if (!Array.isArray(items))
        return;

    items.forEach((item, index) => {

        if (item.sort_order === undefined) {

            item.sort_order = (index + 1) * 10;

        }

    });

}

function addSortOrder(array) {

    array.forEach((item, index) => {

        if (!("sort_order" in item)) {

            item.sort_order =
                (index + 1) * 10;

        }

    });

}

function addFlags(items) {

    if (!Array.isArray(items))
        return;

    items.forEach(item => {

        if (!item.flags) {

            item.flags = {
                featured: false,
                new: false,
                bestseller: false
            };

        }

    });

}

function migrateCollections() {

    const file = "02_collections.json";

    const json = JSON.parse(

        fs.readFileSync(
            path.join(DATA, file),
            "utf8"
        )

    );

    addSortOrder(json.collections);

    addStatus(json.collections);

    if (APPLY)
        save(file, json);

    REPORT.files.push(file);

}

function addStatus(items) {

    if (!Array.isArray(items))
        return;

    items.forEach(item => {

        if (!item.status) {

            item.status = {
                published: true,
                active: true
            };

        }

    });

}

function migratePackaging() {

    const file = "03_packaging_system.json";

    const json = JSON.parse(
        fs.readFileSync(
            path.join(DATA, file),
            "utf8"
        )
    );

    addSortOrder(json.containers);

    addStatus(json.containers);

    if (APPLY)
        save(file, json);

    REPORT.files.push(file);

}
function migrateProfiles() {

    const file = "04_packaging_profiles.json";

    const json = JSON.parse(
        fs.readFileSync(
            path.join(DATA, file),
            "utf8"
        )
    );

    addSortOrder(json.profiles);

    addStatus(json.profiles);

    if (APPLY)
        save(file, json);

    REPORT.files.push(file);

}
function migrateProducts() {

    const file = "05_master_products.json";

    const json = JSON.parse(
        fs.readFileSync(
            path.join(DATA, file),
            "utf8"
        )
    );

    addSortOrder(json.products);

    addStatus(json.products);

    addFlags(json.products);

    if (APPLY)
        save(file, json);

    REPORT.files.push(file);

}
function migrateMarkets() {

    const file = "06_markets.json";

    const json = JSON.parse(
        fs.readFileSync(
            path.join(DATA, file),
            "utf8"
        )
    );

    addSortOrder(json.markets);

    addStatus(json.markets);

    if (APPLY)
        save(file, json);

    REPORT.files.push(file);

}
function migrateDocuments() {

    const file = "07_documents.json";

    const json = JSON.parse(
        fs.readFileSync(
            path.join(DATA, file),
            "utf8"
        )
    );

    addSortOrder(json.documents);

    addStatus(json.documents);

    if (APPLY)
        save(file, json);

    REPORT.files.push(file);

}

migrateCollections();

migratePackaging();

migrateProfiles();

migrateProducts();

migrateMarkets();

migrateDocuments();
fs.writeFileSync(

    path.join(
        REPORTS,
        "migration-report.json"
    ),

    JSON.stringify(
        REPORT,
        null,
        2
    )

);

console.log("");

console.log("Migration Finished.");

console.log("");

console.log("Files processed:");

REPORT.files.forEach(file => {

    console.log("✔", file);

});

console.log("");

console.log("Report saved to reports/migration-report.json");

console.log("");
