import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "GREENY LIFE | Operating System",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#f4f7f3", color: "#163020", fontFamily: "Arial, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}