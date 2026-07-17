import productsData from "@/data/05_master_products.json";

/**
 * ============================================
 * GREENY LIFE
 * Products Data Access Layer
 * ============================================
 */

/**
 * Return complete products registry
 */
export function getProductsData() {
  return productsData;
}

/**
 * Return all products
 */
export function getProducts() {
  return productsData.products;
}

/**
 * Return active products
 */
export function getActiveProducts() {
  return productsData.products.filter(
    (product) => product.status.active
  );
}

/**
 * Return published products
 */
export function getPublishedProducts() {
  return productsData.products.filter(
    (product) => product.status.published
  );
}

/**
 * Return featured products
 */
export function getFeaturedProducts() {
  return productsData.products.filter(
    (product) => product.status.featured === true
  );
}

/**
 * Find product by ID
 */
export function getProduct(id: string) {
  return productsData.products.find(
    (product) => product.id === id
  );
}

/**
 * Find product by Product Code
 */
export function getProductByCode(productCode: string) {
  return productsData.products.find(
    (product) => product.product_code === productCode
  );
}

/**
 * Find product by Reference ID
 */
export function getProductByReference(refId: string) {
  return productsData.products.find(
    (product) => product.ref_id === refId
  );
}

/**
 * Return products by collection
 */
export function getProductsByCollection(collectionId: string) {
  return productsData.products.filter(
    (product) => product.collection === collectionId
  );
}

/**
 * Return products by packaging profile
 */
export function getProductsByPackagingProfile(profileId: string) {
  return productsData.products.filter(
    (product) => product.packaging_profile === profileId
  );
}

/**
 * Check if product exists
 */
export function productExists(id: string) {
  return productsData.products.some(
    (product) => product.id === id
  );
}

/**
 * Return total number of products
 */
export function getProductsCount() {
  return productsData.products.length;
}