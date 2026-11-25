import { type Metadata } from "next";

import { Landing } from "@/components/landing/landing-page";
import { DEFAULT_LOCALE } from "@/core/i18n/locale";
import { landingCopy } from "@/core/i18n/locales/landing";

export const metadata: Metadata = {
  title: landingCopy[DEFAULT_LOCALE].headline,
  description: landingCopy[DEFAULT_LOCALE].intro,
  alternates: { languages: { en: "/", zh: "/zh" } },
};

export default function LandingPage() {
  return <Landing locale={DEFAULT_LOCALE} />;
}
