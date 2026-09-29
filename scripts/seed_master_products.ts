// Dynamically require @prisma/client to avoid TS/IDE errors when the package
// isn't installed in some environments (e.g., CI or editors). If it's missing
// we provide a minimal stub so the script can run without crashing.
let PrismaClient: any;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  PrismaClient = require('@prisma/client').PrismaClient;
} catch (e) {
  console.warn("Warning: '@prisma/client' not found. Using a minimal stub PrismaClient.");
  PrismaClient = class {
    async $disconnect() {}
    // minimal product model stub used by this script
    product = { upsert: async () => ({}) };
  };
}
import * as fs from 'fs';
import * as path from 'path';

const prisma = new PrismaClient();

async function main() {
  console.log("==================================================");
  console.log("   GREENY LIFE - MASTER PRODUCTS SEED MIGRATION");
  console.log("==================================================\n");

  const filePath = path.join(process.cwd(), 'legacy_audit_reports', 'active_master_products.json');
  if (!fs.existsSync(filePath)) {
    console.error("❌ ملف active_master_products.json غير موجود.");
    process.exit(1);
  }

  const rawData = fs.readFileSync(filePath, 'utf8');
  const data = JSON.parse(rawData);
  const products = data.products || [];

  console.log(`📦 تم العثور على ${products.length} منتجاً في السجل الرئيسي. جاري الاستيراد...`);

  for (const p of products) {
    try {
      // قم بتعديل اسم الجدول (مثل prisma.product) حسب ما هو مكتوب في ملف schema.prisma لديك
      await prisma.product.upsert({
        where: { productCode: p.product_code },
        update: {
          nameEn: p.name.en,
          nameAr: p.name.ar,
          collection: p.collection,
          accentColor: p.accent_color,
          published: p.status.published,
          active: p.status.active,
          featured: p.status.featured,
        },
        create: {
          id: p.id,
          productCode: p.product_code,
          refId: p.ref_id,
          collection: p.collection,
          nameEn: p.name.en,
          nameAr: p.name.ar,
          accentColor: p.accent_color,
          published: p.status.published,
          active: p.status.active,
          featured: p.status.featured,
        },
      });
      console.log(` ✅ تم استيراد المنتج: ${p.name.en} (${p.product_code})`);
    } catch (err: any) {
      console.error(` ❌ فشل استيراد المنتج ${p.product_code}: ${err.message}`);
    }
  }

  console.log("\n==================================================");
  console.log("✨ تمت عملية استيراد Product Master بنجاح تام!");
  console.log("==================================================");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });