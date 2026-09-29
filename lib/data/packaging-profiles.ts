import profilesData from "@/data/04_packaging_profiles.json";

/**
 * Return complete packaging profiles data
 */
export function getPackagingProfilesData() {
  return profilesData;
}

/**
 * Return all packaging profiles
 */
export function getPackagingProfiles() {
  return profilesData.profiles;
}

/**
 * Find packaging profile by ID
 */
export function getPackagingProfile(id: string) {
  return profilesData.profiles.find(
    (profile) => profile.id === id
  );
}

/**
 * Return packaging profiles for a specific product
 */
export function getPackagingProfileByProduct(productId: string) {
  return profilesData.profiles.find((profile) =>
    profile.supported_products.includes(productId)
  );
}