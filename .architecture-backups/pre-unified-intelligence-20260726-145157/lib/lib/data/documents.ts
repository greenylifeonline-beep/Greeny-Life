import { promises as fs } from 'fs';
import path from 'path';

// 1. تعريف واجهة المستند (TypeScript Interface)
export interface Document {
  id: string;
  title: string;
  type: string; // مثل: 'pdf', 'docx', 'image'
  fileUrl: string;
  uploadedAt: string;
  category?: string;
}

// تحديد مسار ملف الـ JSON
const documentsFilePath = path.join(process.cwd(), 'data', '07_documents.json');

// 2. دالة جلب كل المستندات
export async function getAllDocuments(): Promise<Document[]> {
  try {
    const jsonData = await fs.readFile(documentsFilePath, 'utf8');
    const documents: Document[] = JSON.parse(jsonData);
    return documents;
  } catch (error) {
    console.error('Error reading documents data:', error);
    return [];
  }
}

// 3. دالة جلب المستندات التابعة لتصنيف معين
export async function getDocumentsByCategory(category: string): Promise<Document[]> {
  const documents = await getAllDocuments();
  return documents.filter((doc) => doc.category === category);
}