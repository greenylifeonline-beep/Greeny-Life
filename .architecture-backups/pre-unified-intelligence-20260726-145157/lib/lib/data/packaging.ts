import packagingData from "@/data/03_packaging_system.json";

/**
 * Return all packaging system data
 */
export function getPackagingData() {
  return packagingData;
}

/**
 * Return all containers
 */
export function getContainers() {
  return packagingData.containers;
}

/**
 * Find container by ID
 */
export function getContainer(id: string) {
  return packagingData.containers.find(
    (container) => container.id === id
  );
}

/**
 * Return all usage profiles
 */
export function getUsageProfiles() {
  return packagingData.usage_profiles;
}

/**
 * Return one usage profile
 */
export function getUsageProfile(id: string) {
  return packagingData.usage_profiles[
    id as keyof typeof packagingData.usage_profiles
  ];
}

/**
 * Return all business channels
 */
export function getBusinessChannels() {
  return packagingData.business_channels;
}

/**
 * Return one business channel
 */
export function getBusinessChannel(id: string) {
  return packagingData.business_channels[
    id as keyof typeof packagingData.business_channels
  ];
}

/**
 * Return customization settings
 */
export function getCustomization() {
  return packagingData.customization;
}