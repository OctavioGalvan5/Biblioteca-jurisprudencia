import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "Biblioteca Jurisprudencia - Estudio Toyos & Espin",
  description: "Sistema de gestión de sentencias judiciales",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-[#f8f7fc]">
        <Navbar />
        {children}
      </body>
    </html>
  );
}
