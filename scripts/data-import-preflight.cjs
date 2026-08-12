const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const readJson = (...parts) => JSON.parse(fs.readFileSync(path.join(root, ...parts), "utf8"));

const suppliers = readJson("canonical", "data", "suppliers.json").suppliers;
const links = readJson("canonical", "data", "supplier-product-links.json").links;
const products = readJson("canonical", "data", "master_products.json").products;
const customers = readJson("canonical", "data", "customer-domain", "customers.json").customers;
const orders = readJson("canonical", "data", "customer-domain", "orders.json").orders;

const productIds = new Set(products.map((product) => product.id));
const supplierIds = new Set(suppliers.map((supplier) => supplier.supplier_id));
const customerIds = new Set(customers.map((customer) => customer.customer_id));
const supplierByProduct = new Map(links.map((link) => [link.product_id, link.supplier_id]));
const missingSupplierLinks = products.filter((product) => !supplierByProduct.has(product.id)).map((product) => product.id);
const invalidLinks = links.filter((link) => !productIds.has(link.product_id) || !supplierIds.has(link.supplier_id));
const invalidOrders = orders.filter((order) => !productIds.has(order.product_id) || !customerIds.has(order.customer_id));

const pricesByProduct = new Map();
for (const order of orders) {
  const prices = pricesByProduct.get(order.product_id) ?? new Set();
  prices.add(order.unit_price);
  pricesByProduct.set(order.product_id, prices);
}
const conflictingHistoricalPrices = [...pricesByProduct.entries()]
  .filter(([, prices]) => prices.size > 1)
  .map(([productId, prices]) => ({ productId, prices: [...prices].sort((a, b) => a - b) }));

console.log(JSON.stringify({
  generatedAt: new Date().toISOString(),
  counts: { suppliers: suppliers.length, products: products.length, links: links.length, customers: customers.length, historicalOrders: orders.length },
  integrity: { missingSupplierLinks, invalidLinks: invalidLinks.length, invalidOrders: invalidOrders.length, conflictingHistoricalPrices },
  decision: "IMPORT_BLOCKED_PENDING_APPROVED_COMMERCIAL_CATALOGUE",
}, null, 2));

process.exitCode = missingSupplierLinks.length || invalidLinks.length || invalidOrders.length || conflictingHistoricalPrices.length ? 2 : 0;
