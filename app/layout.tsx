import "./globals.css";

export const metadata = {
  title: "GREENY LIFE",
  description: "Natural Products",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
