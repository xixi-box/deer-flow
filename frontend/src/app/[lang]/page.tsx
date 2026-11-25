import { type Metadata } from "next";
import { notFound } from "next/navigation";

import { Landing } from "@/components/landing/landing-page";
import { landingCopy } from "@/core/i18n/locales/landing";

export function generateStaticParams() {
  return [{ lang: "zh" }];
}

export const dynamicParams = false;

export const metadata: Metadata = {
  title: landingCopy["zh-CN"].headline,
  description: landingCopy["zh-CN"].intro,
  alternates: { languages: { en: "/", zh: "/zh" } },
};

export default async function LocalizedLandingPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (lang !== "zh") notFound();

  return <Landing locale="zh-CN" />;
}
