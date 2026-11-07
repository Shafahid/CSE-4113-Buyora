import type { Metadata } from "next";
import Script from "next/script";
import { Providers } from "@/components/ui";
import "./globals.css";
import "@/components/layout-adjustments.css";
import "@/components/landing-refinements.css";

export const metadata: Metadata = {
  title: {
    default: "Buyora — A second perspective before you publish",
    template: "%s | Buyora",
  },
  description:
    "Explore buyer perspectives, improve your product posts, and make more informed social commerce decisions with Buyora.",
  icons: { icon: "/logo.png" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script
          id="buyora-theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('buyora-theme');document.documentElement.dataset.theme=t==='dark'||t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}catch(e){document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}})();`,
          }}
        />
      </head>
      <body>
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
