import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RL Decision Brain",
  description: "RL Decision Brain dashboard UI"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
