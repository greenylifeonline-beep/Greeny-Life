import collectionsData from "@/data/02_collections.json";

export function getCollections() {
  return collectionsData.collections;
}

export function getCollectionById(id: string) {
  return collectionsData.collections.find(
    (collection) => collection.id === id
  );
}