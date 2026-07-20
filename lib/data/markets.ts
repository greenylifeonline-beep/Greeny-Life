import { promises as fs } from 'fs';
import path from 'path';

// 1. تعريف واجهة البيانات (TypeScript Interface)
export interface Market {
  id: string;
  name: string;
  location: string;
  status: 'active' | 'inactive';
  description?: string;
}

// تحديد مسار ملف الـ JSON في المشروع
const marketsFilePath = path.join(process.cwd(), 'data', '06_markets.json');

// 2. دالة جلب كل الأسواق
export async function getAllMarkets(): Promise<Market[]> {
  try {
    const jsonData = await fs.readFile(marketsFilePath, 'utf8');
    const markets: Market[] = JSON.parse(jsonData);
    return markets;
  } catch (error) {
    console.error('Error reading markets data:', error);
    return [];
  }
}

// 3. دالة جلب سوق معين بواسطة المعرّف (ID)
export async function getMarketById(id: string): Promise<Market | null> {
  const markets = await getAllMarkets();
  return markets.find((market) => market.id === id) || null;
}