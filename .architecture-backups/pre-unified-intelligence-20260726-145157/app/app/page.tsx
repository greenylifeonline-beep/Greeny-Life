import { getBrand, getWebsite } from "@/lib/data/global";

///Greeny Life
import {
  getActiveProducts,
  getFeaturedProducts
} from "@/lib/data/products";

interface ProductStatus {
  active: boolean;
  published: boolean;
  featured: boolean;
}
interface ProductType {
  id: string;
  product_code: string;
  ref_id: string;
  collection: string;
  packaging_profile: string;
  status: ProductStatus;
  title?: string;
}

interface ProductCardProps {
  id: string;
  product_code: string;
  title: string;
  collection: string;
  language: "en" | "ar";
}

/**
 * ProductCard component transformed from traditional structural patterns
 */
function ProductCard({ id, product_code, title, collection, language }: ProductCardProps) {
  return (
    <div 
      style={{
        border: "1px solid #eaeaea",
        borderRadius: "8px",
        padding: "20px",
        backgroundColor: "#fff",
        boxShadow: "0 2px 4px rgba(0,0,0,0.02)",
        transition: "transform 0.2s, box-shadow 0.2s",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between"
      }}
    >
      <div>
        <span style={{ fontSize: "12px", color: "#888", textTransform: "uppercase" }}>
          {collection}
        </span>
        <h3 style={{ margin: "8px 0", fontSize: "18px", color: "#333" }}>{title}</h3>
        <p style={{ fontSize: "13px", color: "#666" }}>
          {language === "ar" ? "كود المنتج:" : "Code:"} <strong>{product_code}</strong>
        </p>
      </div>
      <button 
        style={{
          marginTop: "16px",
          padding: "10px",
          backgroundColor: "#00b207",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          fontWeight: "bold"
        }}
      >
        {language === "ar" ? "عرض التفاصيل" : "View Details"}
      </button>
    </div>
  );
}

/**
 * Main HomePage Server Component
 */
export default async function HomePage() {
  const brand = getBrand();
  const website = getWebsite();
  const language = website.default_language as "en" | "ar";

  // Fetch data safely from the local products file asynchronously
  const [activeProducts, featuredProducts] = await Promise.all([
    getActiveProducts(),
    getFeaturedProducts()
  ]);

  const isRtl = language === "ar";

  return (
    <main
      dir={isRtl ? "rtl" : "ltr"}
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "40px",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Brand Header Section */}
      <header style={{ marginBottom: "40px", textAlign: isRtl ? "right" : "left" }}>
        <h1 style={{ fontSize: "36px", margin: "0 0 10px 0", color: "#111" }}>{brand.name}</h1>
        <p style={{ fontSize: "18px", color: "#666", margin: "0" }}>{brand.tagline[language]}</p>
      </header>

      <hr style={{ border: "0", borderTop: "1px solid #eee", margin: "30px 0" }} />

      {/* Featured Products Layout */}
      <section style={{ marginBottom: "50px" }}>
        <h2 style={{ fontSize: "24px", marginBottom: "20px", color: "#222" }}>
          {language === "ar" ? "المنتجات المميزة" : "Featured Products"}
        </h2>
        
        {featuredProducts.length === 0 ? (
          <p style={{ color: "#888" }}>
            {language === "ar" ? "لا توجد منتجات مميزة حالياً." : "No featured products found."}
          </p>
        ) : (
          <div 
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "24px"
            }}
          >
            {featuredProducts.map((product: ProductType) => (
              <ProductCard 
                key={product.id}
                id={product.id}
                product_code={product.product_code}
                title={product.title || "Greeny Life Product"}
                collection={product.collection}
                language={language}
              />
            ))}
          </div>
        )}
      </section>

      {/* Persistent System Architecture Footer */}
      <footer style={{ marginTop: "60px", paddingTop: "20px", borderTop: "1px solid #eee", textAlign: "center" }}>
        <h4 style={{ color: "#00b207", margin: "0 0 5px 0" }}>GREENY LIFE</h4>
        <p style={{ color: "#777", fontSize: "14px", margin: "0" }}>
          Next.js Architecture is Production-Ready with Advanced Async DAL.
        </p>
      </footer>
    </main>
  );
}