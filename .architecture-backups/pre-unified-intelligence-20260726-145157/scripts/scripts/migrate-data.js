// scripts/migrate-data.js
const fs = require('fs');
const path = require('path');

const legacyPath = path.join(__dirname, '../data/legacy');
const targetPath = path.join(__dirname, '../data');

// الملفات التي سنقوم بترحيلها بتركيز
const filesToMigrate = ['products.json', 'categories.json', 'brand.json'];

filesToMigrate.forEach(file => {
    if (fs.existsSync(path.join(legacyPath, file))) {
        const data = fs.readFileSync(path.join(legacyPath, file), 'utf8');
        fs.writeFileSync(path.join(targetPath, 'migrated_' + file), data);
        console.log(`تم ترحيل بيانات ${file} بنجاح.`);
    }
});