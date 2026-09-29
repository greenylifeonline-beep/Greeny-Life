const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const DATA_DIR = path.join(ROOT, "data");

const FILES = [
    "02_collections.json",
    "03_packaging_system.json",
    "04_packaging_profiles.json",
    "05_master_products.json",
    "06_markets.json",
    "07_documents.json"
];

console.clear();

console.log("");
console.log("==========================================");
console.log(" GREENY LIFE Schema Validator");
console.log("==========================================");
console.log("");

let totalErrors = 0;

function validateEntity(entity, fileName) {

    if (!entity.id) {

        console.log(`❌ ${fileName}: Missing id`);
        totalErrors++;

    }

    if (!("sort_order" in entity)) {

        console.log(`❌ ${fileName}: ${entity.id} -> Missing sort_order`);
        totalErrors++;

    }

    if (!("status" in entity)) {

        console.log(`❌ ${fileName}: ${entity.id} -> Missing status`);
        totalErrors++;

    }

}

for (const file of FILES) {

    const filePath = path.join(DATA_DIR, file);

    if (!fs.existsSync(filePath)) {

        console.log(`❌ File not found: ${file}`);
        totalErrors++;
        continue;

    }

    const json = JSON.parse(
        fs.readFileSync(filePath, "utf8")
    );

    switch (file) {

        case "02_collections.json":

            json.collections.forEach(validate =>
                validateEntity(validate, file)
            );

            break;

        case "03_packaging_system.json":

            json.containers.forEach(validate =>
                validateEntity(validate, file)
            );

            break;

        case "04_packaging_profiles.json":

            json.profiles.forEach(validate =>
                validateEntity(validate, file)
            );

            break;

        case "05_master_products.json":

            json.products.forEach(product => {

                validateEntity(product, file);

                if (!("flags" in product)) {

                    console.log(`❌ ${file}: ${product.id} -> Missing flags`);

                    totalErrors++;

                }

            });

            break;

        case "06_markets.json":

            json.markets.forEach(validate =>
                validateEntity(validate, file)
            );

            break;

        case "07_documents.json":

            json.documents.forEach(validate =>
                validateEntity(validate, file)
            );

            break;

    }

}

console.log("");

if (totalErrors === 0) {

    console.log("✅ Schema Validation Passed");

} else {

    console.log(`❌ ${totalErrors} issue(s) found`);

}

console.log("");
console.log("==========================================");
console.log("");