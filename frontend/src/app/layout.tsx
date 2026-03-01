import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "LLM Influence Dashboard",
  description:
    "Fine-tune LLMs and explore per-partition influence scores with TracIn and DataInf.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Sidebar />
        <main className="ml-[68px] min-h-screen">{children}</main>
      </body>
    </html>
  );
}
