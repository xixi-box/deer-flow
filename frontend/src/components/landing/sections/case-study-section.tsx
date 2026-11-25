import { ArrowUpRightIcon } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { type LandingCopy } from "@/core/i18n/locales/landing";
import { pathOfPublicDemoThread } from "@/core/threads/static-demo";

import { Section } from "../section";

const caseStudyThreadIds = [
  "7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
  "4f3e55ee-f853-43db-bfb3-7d1a411f03cb",
  "21cfea46-34bd-4aa6-9e1f-3009452fbeb9",
  "ad76c455-5bf9-4335-8517-fc03834ab828",
  "d3e5adaf-084c-4dd5-9d29-94f1d6bccd98",
  "3823e443-4e2b-4679-b496-a9506eae462b",
] as const;

export function CaseStudySection({ copy }: { copy: LandingCopy }) {
  return (
    <Section
      id="case-studies"
      title={copy.caseStudies}
      subtitle={copy.caseStudiesIntro}
    >
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {caseStudyThreadIds.map((threadId, index) => {
          const [title, description] = copy.examples[index]!;
          return (
            <li key={threadId}>
              <Link
                href={pathOfPublicDemoThread(threadId)}
                target="_blank"
                rel="noopener noreferrer"
                prefetch={false}
                className="group bg-card border-border hover:border-landing-accent/70 flex h-full flex-col overflow-hidden rounded-lg border transition-colors"
              >
                <Image
                  src={`/images/${threadId}.jpg`}
                  alt={`${copy.casePreview} · ${title}`}
                  width={640}
                  height={360}
                  loading="lazy"
                  decoding="async"
                  sizes="(min-width: 1152px) 352px, (min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                  className="border-border aspect-video w-full border-b object-cover"
                />
                <div className="p-4">
                  <h3 className="flex items-start justify-between gap-3 font-medium">
                    {title}
                    <ArrowUpRightIcon
                      className="text-landing-accent mt-0.5 size-4 shrink-0"
                      aria-hidden="true"
                    />
                  </h3>
                  <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
                    {description}
                  </p>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </Section>
  );
}
