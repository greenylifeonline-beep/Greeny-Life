import globalData from "@/data/01_global.json";

/**
 * Return all global configuration
 */
export function getGlobalData() {
  return globalData;
}

/**
 * Brand information
 */
export function getBrand() {
  return globalData.brand;
}

/**
 * Brand identity
 */
export function getIdentity() {
  return globalData.identity;
}

/**
 * Website configuration
 */
export function getWebsite() {
  return globalData.website;
}

/**
 * Manufacturer information
 */
export function getManufacturer() {
  return globalData.manufacturer;
}

/**
 * Contact information
 */
export function getContact() {
  return globalData.contact;
}