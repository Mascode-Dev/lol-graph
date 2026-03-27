import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer"; // 1. IMPORT FOOTER

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LoL Knowledge Graph",
  description: "An AI-powered semantic search engine for League of Legends.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/* 2. ADD FLEXBOX AND MIN-HEIGHT TO BODY */}
      <body className={`${inter.className} bg-slate-50 text-slate-900 antialiased pt-16 flex flex-col min-h-screen`}>
        <Navbar />
        
        {/* 3. WRAP CHILDREN IN FLEX-GROW */}
        <main className="flex-grow">
          {children}
        </main>

        {/* 4. ADD FOOTER AT THE VERY BOTTOM */}
        <Footer />
      </body>
    </html>
  );
}