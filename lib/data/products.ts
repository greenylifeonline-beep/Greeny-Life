import productsData from "@/data/05_master_products.json";

/**
 * ============================================
 * GREENY LIFE - PRODUCTS DATA ACCESS LAYER (DAL)
 * Professional & Scalable Architecture
 * ============================================
 */

// 1. تعريف الهيكل الصارم للمنتج (Strict Typing)
// يمكنك التعديل عليه حسب الخصائص الفعلية الموجودة في ملف الـ JSON لديك
export interface ProductStatus {
  active: boolean;
  published: boolean;
  featured: boolean;
}

export interface Product {
  id: string;
  product_code: string;
  ref_id: string;
  title: string;          // أضف الخصائص الفعليه هنا
  collection: string;
  packaging_profile: string;
  status: ProductStatus;
  // [Key: string]: any; // فك التجميد عن هذا السطر مؤقتاً إذا كانت هناك خصائص أخرى كثيرة لم تكتبها
}

export interface ProductsRegistry {
  products: Product[];
  // أضف أي خصائص أخرى موجودة في جذور ملف الـ JSON (مثل التعداد أو تاريخ التحديث)
}

// تحويل البيانات المستوردة لنوع المنتجات الصارم
const registry = productsData as unknown as ProductsRegistry;
const allProducts: Product[] = registry.products;


/**
 * Return complete products registry
 */
export async function getProductsData(): Promise<ProductsRegistry> {
  return registry;
}

/**
 * Return all products
 */
export async function getProducts(): Promise<Product[]> {
  return allProducts;
}

/**
 * Return active products
 */
export async function getActiveProducts(): Promise<Product[]> {
  return allProducts.filter((product) => product.status.active);
}

/**
 * Return published products
 */
export async function getPublishedProducts(): Promise<Product[]> {
  return allProducts.filter((product) => product.status.published);
}

/**
 * Return featured products
 */
export async function getFeaturedProducts(): Promise<Product[]> {
  return allProducts.filter((product) => product.status.featured === true);
}

/**
 * Find product by ID
 */
export async function getProduct(id: string): Promise<Product | undefined> {
  return allProducts.find((product) => product.id === id);
}

/**
 * Find product by Product Code
 */
export async function getProductByCode(productCode: string): Promise<Product | undefined> {
  return allProducts.find((product) => product.product_code === productCode);
}

/**
 * Find product by Reference ID
 */
export async function getProductByReference(refId: string): Promise<Product | undefined> {
  return allProducts.find((product) => product.ref_id === refId);
}

/**
 * Return products by collection
 */
export async function getProductsByCollection(collectionId: string): Promise<Product[]> {
  return allProducts.filter((product) => product.collection === collectionId);
}

/**
 * Return products by packaging profile
 */
export async function getProductsByPackagingProfile(profileId: string): Promise<Product[]> {
  return allProducts.filter((product) => product.packaging_profile === profileId);
}

/**
 * Check if product exists
 */
export async function productExists(id: string): Promise<boolean> {
  return allProducts.some((product) => product.id === id);
}

/**
 * Return total number of products
 */
export async function getProductsCount(): Promise<number> {
  return allProducts.length;
}