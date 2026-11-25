import Link from "next/link";

import { getLangByLocale, type Locale } from "@/core/i18n/locale";
import { landingCopy } from "@/core/i18n/locales/landing";

import { Hero, repositoryURL } from "./hero";
import { LandingHeader } from "./landing-header";
import { CaseStudySection } from "./sections/case-study-section";
import { CommunitySection } from "./sections/community-section";
import { SandboxSection } from "./sections/sandbox-section";
import { SkillsSection } from "./sections/skills-section";
import { WhatsNewSection } from "./sections/whats-new-section";

export function Landing({ locale }: { locale: Locale }) {
  const copy = landingCopy[locale];
  const docsURL = `/${getLangByLocale(locale)}/docs`;

  return (
    <div lang={locale} className="bg-background text-foreground min-h-screen">
      <LandingHeader copy={copy} locale={locale} docsURL={docsURL} />
      <main>
        <Hero copy={copy} docsURL={docsURL} />
        <CaseStudySection copy={copy} />
        <SkillsSection copy={copy} />
        <SandboxSection copy={copy} docsURL={docsURL} />
        <WhatsNewSection copy={copy} />
        <CommunitySection copy={copy} />
      </main>
      <footer className="border-border border-t">
        <div className="text-muted-foreground mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-6 text-sm sm:px-8">
          <span className="text-foreground font-serif text-xl">DeerFlow</span>
          <div className="flex flex-wrap gap-4">
            <Link href={docsURL} className="hover:underline">
              {copy.docs}
            </Link>
            <Link href="/blog/posts" className="hover:underline">
              {copy.blog}
            </Link>
            <a
              href={`${repositoryURL}/blob/main/LICENSE`}
              className="hover:underline"
            >
              {copy.license}
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
