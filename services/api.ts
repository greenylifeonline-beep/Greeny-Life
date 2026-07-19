// services/api.ts
import fs from 'fs';
import path from 'path';

const dataPath = path.join(process.cwd(), 'data');

export async function getProducts() {
  const filePath = path.join(dataPath, 'migrated_products.json');
  const fileContent = fs.readFileSync(filePath, 'utf8');
  return JSON.parse(fileContent);
}

export async function getCategories() {
  const filePath = path.join(dataPath, 'migrated_categories.json');
  const fileContent = fs.readFileSync(filePath, 'utf8');
  return JSON.parse(fileContent);
}