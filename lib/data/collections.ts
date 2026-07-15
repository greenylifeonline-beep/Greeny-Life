import collections from "@/data/02_collections.json";

export function getCollections() {
  return collections;
}

export function getCollection(id: string) {
  return collections.find(
    collection => collection.id === id
  );
}