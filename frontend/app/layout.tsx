import type { Metadata } from "next";
import "./globals.css";

import { Providers } from "@/providers/Providers";

export const metadata: Metadata = {
  title: {
    default: "Cartel",
    template: "%s | Cartel",
  },
  description:
    "The smartest way to buy your groceries. Compare, optimize, and save across multiple grocery platforms.",
  applicationName: "Cartel",
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({
  children,
}: Readonly<RootLayoutProps>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
