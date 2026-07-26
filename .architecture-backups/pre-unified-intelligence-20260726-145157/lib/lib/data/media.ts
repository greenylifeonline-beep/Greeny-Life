import mediaData from "@/data/08_media.json";

/**
 * ============================================
 * GREENY LIFE
 * Media Data Access Layer
 * Version: 1.0.0
 * ============================================
 */

/**
 * Return complete media library
 */
export function getMediaData() {
  return mediaData;
}

/**
 * ============================================
 * Brand Media
 * ============================================
 */

/**
 * Return all brand media
 */
export function getBrandMedia() {
  return mediaData.media.brand;
}

/**
 * Return primary logo
 */
export function getPrimaryLogo() {
  return mediaData.media.brand.logo_primary;
}

/**
 * Return light logo
 */
export function getLightLogo() {
  return mediaData.media.brand.logo_light;
}

/**
 * Return dark logo
 */
export function getDarkLogo() {
  return mediaData.media.brand.logo_dark;
}

/**
 * ============================================
 * Product Media
 * ============================================
 */

/**
 * Return all products media
 */
export function getProductsMedia() {
  return mediaData.media.products;
}

/**
 * Return media for one product
 */
export function getProductMedia(productId: string) {
  return mediaData.media.products[
    productId as keyof typeof mediaData.media.products
  ];
}

/**
 * Return hero image
 */
export function getProductHero(productId: string) {
  const product = getProductMedia(productId);

  return product?.hero ?? null;
}

/**
 * Return cover image
 */
export function getProductCover(productId: string) {
  const product = getProductMedia(productId);

  return product?.cover ?? null;
}

/**
 * Return gallery images
 */
export function getProductGallery(productId: string) {
  const product = getProductMedia(productId);

  return product?.gallery ?? [];
}

/**
 * ============================================
 * Documents
 * ============================================
 */

/**
 * Return all document media
 */
export function getDocumentMedia() {
  return mediaData.media.documents;
}

/**
 * Return company catalog
 */
export function getCatalog() {
  return mediaData.media.documents.catalog;
}

/**
 * Return company profile
 */
export function getCompanyProfile() {
  return mediaData.media.documents["company-profile"];
}