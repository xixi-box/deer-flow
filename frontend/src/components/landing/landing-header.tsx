import { LanguagesIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { type Locale } from "@/core/i18n/locale";
import { type LandingCopy } from "@/core/i18n/locales/landing";

import {
  LandingBanner,
  LandingMenus,
  LandingThemeToggle,
} from "./landing-controls";
import { MobileNav } from "./mobile-nav";

export function LandingHeader({
  copy,
  locale,
  docsURL,
}: {
  copy: LandingCopy;
  locale: Locale;
  docsURL: string;
}) {
  const chinese = locale === "zh-CN";
  const menus = [
    {
      name: copy.product,
      links: [
        { label: copy.caseStudies, href: "#case-studies" },
        { label: copy.skillsTitle, href: "#skills" },
        { label: copy.whatsNew, href: "#whats-new" },
      ],
    },
    {
      name: copy.integrations,
      links: [
        { label: copy.models, href: `${docsURL}/harness/configuration` },
        { label: copy.sandbox, href: "#sandbox" },
        { label: copy.mcp, href: `${docsURL}/harness/mcp` },
        { label: copy.channels, href: `${docsURL}/application/configuration` },
      ],
    },
    {
      name: copy.developers,
      links: [
        { label: copy.quickStart, href: `${docsURL}/application/quick-start` },
        { label: copy.docs, href: docsURL },
        { label: copy.blog, href: "/blog/posts" },
        { label: copy.community, href: "#community" },
      ],
    },
  ];

  return (
    <header className="border-border bg-background border-b">
      <LandingBanner
        invite={copy.communityInvite}
        dismiss={copy.dismissBanner}
      />
      <div className="mx-auto flex min-h-16 max-w-6xl items-center justify-between gap-2 px-4 sm:px-8">
        <Link
          href={chinese ? "/zh" : "/"}
          className="rounded-sm font-serif text-2xl leading-none tracking-tight"
        >
          DeerFlow
        </Link>
        <LandingMenus label={copy.navigation} menus={menus} />
        <div className="flex items-center gap-1">
          <Button className="h-11" variant="ghost" asChild>
            <Link
              href={chinese ? "/" : "/zh"}
              prefetch={false}
              hrefLang={chinese ? "en-US" : "zh-CN"}
              lang={chinese ? "en-US" : "zh-CN"}
            >
              <LanguagesIcon aria-hidden="true" />
              {chinese ? "English" : "中文"}
            </Link>
          </Button>
          <LandingThemeToggle label={copy.darkMode} />
          <MobileNav
            links={menus.flatMap(({ links }) => links)}
            menuLabel={copy.openMenu}
          />
        </div>
      </div>
    </header>
  );
}
