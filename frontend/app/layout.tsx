import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/layout/query-provider";

export const metadata: Metadata = {
  title: "Veekay Finserve — Renewal Dashboard",
  description: "Insurance renewal management system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
