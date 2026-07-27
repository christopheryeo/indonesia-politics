import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;
  const description = "A deterministic dashboard for the Indonesia-politics knowledge vault.";

  return {
    title: "Sentient.io Media Intelligence",
    description,
    openGraph: {
      title: "Sentient.io Media Intelligence",
      description,
      url: origin,
      images: [{ url: `${origin}/og.png`, width: 1200, height: 630, alt: "Sentient.io Media Intelligence" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Sentient.io Media Intelligence",
      description,
      images: [`${origin}/og.png`],
    },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
