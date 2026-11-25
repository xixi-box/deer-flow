import { ArrowUpRightIcon, BoxIcon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { type LandingCopy } from "@/core/i18n/locales/landing";

import { Section } from "../section";

export function SandboxSection({
  copy,
  docsURL,
}: {
  copy: LandingCopy;
  docsURL: string;
}) {
  return (
    <Section
      id="sandbox"
      title={copy.sandboxTitle}
      subtitle={copy.sandboxIntro}
    >
      <div className="bg-card border-border flex flex-col items-start justify-between gap-5 rounded-lg border p-5 sm:flex-row sm:items-center">
        <div className="flex items-start gap-4">
          <BoxIcon
            className="text-landing-accent mt-0.5 size-6 shrink-0"
            aria-hidden="true"
          />
          <div>
            <h3 className="text-lg font-medium">
              <a
                href="https://github.com/agent-infra/sandbox"
                className="hover:underline"
              >
                {copy.aioSandbox}
              </a>
            </h3>
            <p className="text-muted-foreground mt-1 max-w-xl">
              {copy.aioDescription}
            </p>
          </div>
        </div>
        <Button className="h-11" variant="outline" asChild>
          <Link href={`${docsURL}/harness/sandbox`}>
            {copy.sandboxGuide}
            <ArrowUpRightIcon aria-hidden="true" />
          </Link>
        </Button>
      </div>
    </Section>
  );
}
