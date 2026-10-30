import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DukaanSaathi — Voice-First Kirana Commerce",
  description: "Voice-first commerce infrastructure for neighbourhood kirana stores across Bharat.",
  applicationName: "DukaanSaathi",
  appleWebApp: {
    capable: true,
    title: "DukaanSaathi",
    statusBarStyle: "default",
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
    <html lang="hi" className="h-full">
      <body className="h-full bg-dukaan-canvas text-dukaan-text antialiased">
        {children}
      </body>
    </html>
  );
}
