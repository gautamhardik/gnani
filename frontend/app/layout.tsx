import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ShopAmbientBackground } from "@/components/ShopAmbientBackground";

export const metadata: Metadata = {
  title: "DukaanSaathi — Voice-First Kirana Commerce",
  description: "Voice-first commerce infrastructure for neighbourhood kirana stores across Bharat.",
  applicationName: "DukaanSaathi",
  appleWebApp: {
    capable: true,
    title: "DukaanSaathi",
    statusBarStyle: "default",
  },
  other: {
    google: "notranslate",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#C2410C",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="hi" className="h-full notranslate" translate="no" suppressHydrationWarning>
      <head>
        <meta name="google" content="notranslate" />
      </head>
      <body className="h-full bg-dukaan-canvas text-dukaan-text antialiased relative" suppressHydrationWarning>
        <ShopAmbientBackground />
        {children}
      </body>
    </html>
  );
}
