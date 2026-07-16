import { getBrand } from "@/lib/data/global";

export default function HomePage() {
  const brand = getBrand();

  return (
    <main
      style={{
        maxWidth: "1200px",
        margin: "0 auto",
        padding: "40px",
      }}
    >
      <h1>{brand.name}</h1>

      <p>{brand.tagline}</p>

      <hr />

      <h2>GREENY LIFE</h2>

      <p>Next.js Architecture is Ready.</p>
    </main>
  );
}