const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const readJson = (...parts) => JSON.parse(fs.readFileSync(path.join(root, ...parts), "utf8"));

function orderTotalRemediationCandidates(orders) {
  return orders
    .filter((order) => !Number.isFinite(order.quantity) || !Number.isFinite(order.unit_price) || !Number.isFinite(order.total_price) || Math.abs(order.quantity * order.unit_price - order.total_price) > 0.01)
    .map((order) => ({
      remediationId: `ORDER_TOTAL_${order.order_id}`,
      status: "REVIEW_REQUIRED",
      orderId: order.order_id,
      customerId: order.customer_id,
      productId: order.product_id,
      original: { quantity: order.quantity, unitPrice: order.unit_price, totalPrice: order.total_price },
      calculatedTotal: order.quantity * order.unit_price,
      difference: order.total_price - (order.quantity * order.unit_price),
      requiredEvidence: ["Approved commercial record, invoice, or source order document."],
      action: "No automatic correction. A named commercial-data owner must approve the correction basis and final value.",
    }));
}

function evaluateImportData({ suppliers, links, products, customers, orders }) {
  const productIds = new Set(products.map((product) => product.id));
  const supplierIds = new Set(suppliers.map((supplier) => supplier.supplier_id));
  const customerIds = new Set(customers.map((customer) => customer.customer_id));
  const supplierByProduct = new Map(links.map((link) => [link.product_id, link.supplier_id]));
  const missingSupplierLinks = products.filter((product) => !supplierByProduct.has(product.id)).map((product) => product.id);
  const invalidLinks = links.filter((link) => !productIds.has(link.product_id) || !supplierIds.has(link.supplier_id));
  const invalidOrders = orders.filter((order) => !productIds.has(order.product_id) || !customerIds.has(order.customer_id));
  const remediationCandidates = orderTotalRemediationCandidates(orders);
  const invalidOrderTotals = remediationCandidates.map((item) => ({ orderId: item.orderId, productId: item.productId, expectedTotal: item.calculatedTotal, actualTotal: item.original.totalPrice }));

  const pricesByProduct = new Map();
  for (const order of orders) {
    const prices = pricesByProduct.get(order.product_id) ?? new Set();
    prices.add(order.unit_price);
    pricesByProduct.set(order.product_id, prices);
  }
  const historicalPriceVariations = [...pricesByProduct.entries()]
    .filter(([, prices]) => prices.size > 1)
    .map(([productId, prices]) => ({ productId, prices: [...prices].sort((a, b) => a - b) }));
  const blocked = Boolean(missingSupplierLinks.length || invalidLinks.length || invalidOrders.length || invalidOrderTotals.length);

  return {
    counts: { suppliers: suppliers.length, products: products.length, links: links.length, customers: customers.length, historicalOrders: orders.length },
    integrity: { missingSupplierLinks, invalidLinks: invalidLinks.length, invalidOrders: invalidOrders.length, invalidOrderTotals },
    remediation: { owner: "COMMERCIAL_DATA_OWNER_UNASSIGNED", candidateCount: remediationCandidates.length, candidates: remediationCandidates },
    warnings: { historicalPriceVariations, rule: "Historical unit-price variation is not a current price catalogue and does not by itself invalidate an order." },
    decision: blocked ? "IMPORT_BLOCKED_INVALID_REFERENCES_OR_TOTALS" : "IMPORT_REVIEW_REQUIRED_APPROVED_COMMERCIAL_CATALOGUE",
    blocked,
  };
}

if (require.main === module) {
  const report = evaluateImportData({
    suppliers: readJson("canonical", "data", "suppliers.json").suppliers,
    links: readJson("canonical", "data", "supplier-product-links.json").links,
    products: readJson("canonical", "data", "master_products.json").products,
    customers: readJson("canonical", "data", "customer-domain", "customers.json").customers,
    orders: readJson("canonical", "data", "customer-domain", "orders.json").orders,
  });
  console.log(JSON.stringify({ generatedAt: new Date().toISOString(), ...report }, null, 2));
  process.exitCode = report.blocked ? 2 : 0;
}

module.exports = { evaluateImportData, orderTotalRemediationCandidates };
