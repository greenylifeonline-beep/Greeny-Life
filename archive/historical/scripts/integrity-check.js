/**
 * GL-EOS Integrity Scanner v1.0
 * يقوم بفحص شجرة الملفات والتأكد من وجود المكونات الأساسية
 */
const fs = require('fs');
const path = require('path');

const requiredFiles = [
    'GL-EOS-v1.0.md',
    'GL-EOS-v1.0.json',
    'master_products.json',
    'generator.js',
    'src/db/neo4j-schema.cypher',
    'src/api/sync-engine.js',
    'src/portal/supplier-intake.js',
    'src/dashboard/qa-dashboard.js'
];

function checkIntegrity() {
    console.log("🔍 Starting GL-EOS System Scan...");
    let missing = [];

    requiredFiles.forEach(file => {
        if (!fs.existsSync(path.join(__dirname, file))) {
            missing.push(file);
        }
    });

    if (missing.length > 0) {
        console.error("❌ System Incomplete! Missing files:", missing);
    } else {
        console.log("✅ System Integrity Verified. All components present.");
    }
}

checkIntegrity();