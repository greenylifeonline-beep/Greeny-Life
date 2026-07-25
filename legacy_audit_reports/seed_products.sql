-- Greeny Life EOS - Master Products Direct Seed
BEGIN;


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('wildflower-honey', 'HON001', 'GL-HON-001', 'honey', 'Wildflower Honey', 'عسل الزهور البرية', '#C9A227', TRUE, TRUE, TRUE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('citrus-honey', 'HON002', 'GL-HON-002', 'honey', 'Citrus Honey', 'عسل الحمضيات', '#E8913A', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('clover-honey', 'HON003', 'GL-HON-003', 'honey', 'Clover Honey', 'عسل البرسيم', '#E8D5A3', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('royal-jelly', 'BEE001', 'GL-BEE-001', 'bee_products', 'Royal Jelly', 'غذاء ملكات النحل', '#F4E7C6', TRUE, TRUE, TRUE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('raw-propolis', 'BEE002', 'GL-BEE-002', 'bee_products', 'Raw Propolis', 'صمغ النحل الخام', '#7A4A24', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('bee-pollen', 'BEE003', 'GL-BEE-003', 'bee_products', 'Bee Pollen', 'حبوب لقاح النحل', '#E2B400', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('pure-beeswax', 'BEE004', 'GL-BEE-004', 'bee_products', 'Pure Beeswax', 'شمع النحل النقي', '#D4A017', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('garlic-powder', 'SPC001', 'GL-SPC-001', 'spices', 'Garlic Powder', 'بودرة الثوم', '#E8DDC6', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('onion-powder', 'SPC002', 'GL-SPC-002', 'spices', 'Onion Powder', 'بودرة البصل', '#A47149', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('turmeric-powder', 'SPC003', 'GL-SPC-003', 'spices', 'Turmeric Powder', 'بودرة الكركم', '#E5B800', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('sweet-paprika', 'SPC004', 'GL-SPC-004', 'spices', 'Sweet Paprika', 'البابريكا الحلوة', '#C6452D', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('roasted-cumin', 'SPC005', 'GL-SPC-005', 'spices', 'Roasted Cumin', 'الكمون المحمص', '#8B5A2B', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('seven-spices-blend', 'SPC006', 'GL-SPC-006', 'spices', 'Seven Spices Blend', 'خلطة السبع بهارات', '#6E8B3D', TRUE, TRUE, TRUE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('hibiscus-flowers', 'HRB001', 'GL-HRB-001', 'herbs', 'Hibiscus Flowers', 'زهور الكركديه', '#B22222', TRUE, TRUE, FALSE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();


INSERT INTO "Product" (id, "productCode", "refId", collection, "nameEn", "nameAr", "accentColor", published, active, featured, "createdAt", "updatedAt")
VALUES ('black-seed-oil', 'OIL001', 'GL-OIL-001', 'oils', 'Black Seed Oil', 'زيت حبة البركة', '#1F1F1F', TRUE, TRUE, TRUE, NOW(), NOW())
ON CONFLICT ("productCode") DO UPDATE SET
    "refId" = EXCLUDED."refId",
    collection = EXCLUDED.collection,
    "nameEn" = EXCLUDED."nameEn",
    "nameAr" = EXCLUDED."nameAr",
    "accentColor" = EXCLUDED."accentColor",
    published = EXCLUDED.published,
    active = EXCLUDED.active,
    featured = EXCLUDED.featured,
    "updatedAt" = NOW();

COMMIT;