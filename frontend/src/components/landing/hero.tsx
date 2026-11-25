import { GitHubLogoIcon } from "@radix-ui/react-icons";
import {
  ArrowDownIcon,
  ArrowRightIcon,
  BoxIcon,
  BrainIcon,
  CpuIcon,
  LayersIcon,
  MessageSquareIcon,
  NetworkIcon,
  PlugIcon,
  WorkflowIcon,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { type LandingCopy } from "@/core/i18n/locales/landing";
import { env } from "@/env";
import { cn } from "@/lib/utils";

import { BytePlusIcon } from "./byteplus-icon";
import { StarCounter } from "./star-counter";

export const repositoryURL = "https://github.com/bytedance/deer-flow";

export function Hero({
  copy,
  docsURL,
}: {
  copy: LandingCopy;
  docsURL: string;
}) {
  const architecture = [
    {
      title: copy.inputs,
      nodes: [
        { label: copy.models, Icon: CpuIcon },
        { label: copy.channels, Icon: MessageSquareIcon },
      ],
    },
    {
      title: copy.core,
      nodes: [
        { label: copy.memory, Icon: BrainIcon },
        { label: copy.subagents, Icon: NetworkIcon },
      ],
    },
    {
      title: copy.execution,
      nodes: [
        { label: copy.sandbox, Icon: BoxIcon },
        { label: copy.skills, Icon: LayersIcon },
        { label: copy.mcp, Icon: PlugIcon },
      ],
    },
  ];

  return (
    <section
      aria-labelledby="landing-title"
      className="border-border border-b [background-image:linear-gradient(to_right,var(--landing-grid)_1px,transparent_1px),linear-gradient(to_bottom,var(--landing-grid)_1px,transparent_1px)] bg-size-[36px_36px]"
    >
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-14 sm:px-8 sm:py-20 lg:grid-cols-[1.2fr_1fr] lg:gap-14 lg:py-24">
        <div>
          <p className="text-muted-foreground font-mono text-sm tracking-wider uppercase">
            {copy.eyebrow}
          </p>
          <h1
            id="landing-title"
            className="mt-4 font-serif text-4xl leading-[1.06] tracking-tight text-balance sm:text-6xl"
          >
            {copy.headline}
          </h1>
          <p className="text-muted-foreground mt-5 max-w-xl text-lg leading-relaxed">
            {copy.intro}
          </p>
          <div className="mt-7 flex flex-wrap gap-2">
            <Button
              className="bg-landing-accent text-landing-accent-foreground hover:bg-landing-accent/90 h-11"
              asChild
            >
              <Link href="/workspace" prefetch={false}>
                {copy.getStarted}
                <ArrowRightIcon aria-hidden="true" />
              </Link>
            </Button>
            <Button className="h-11" variant="outline" asChild>
              <Link
                href={`${docsURL}/application/quick-start`}
                prefetch={false}
              >
                {copy.quickStart}
              </Link>
            </Button>
            <Button className="h-11" variant="ghost" asChild>
              <Link href={docsURL} prefetch={false}>
                {copy.docs}
              </Link>
            </Button>
          </div>
          <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-3 text-sm">
            <a
              href={repositoryURL}
              className="inline-flex items-center gap-2 rounded-sm font-medium underline-offset-4 hover:underline"
            >
              <GitHubLogoIcon aria-hidden="true" className="size-4" />
              {copy.openSource}
            </a>
            <StarCounter labels={{ stars: copy.stars, forks: copy.forks }} />
          </div>
          {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" && (
            <a
              href="https://byteplus.com"
              className="text-muted-foreground mt-5 inline-flex items-center gap-2 text-sm hover:underline"
            >
              {copy.partnership}
              <BytePlusIcon
                className="h-4 w-20"
                role="img"
                aria-label="BytePlus"
              />
            </a>
          )}
        </div>
        <figure
          aria-labelledby="landing-architecture"
          className="border-border bg-background rounded-xl border p-4 sm:p-6"
        >
          <figcaption
            id="landing-architecture"
            className="flex items-center gap-2 font-mono text-sm font-medium"
          >
            <WorkflowIcon
              className="text-landing-accent size-4"
              aria-hidden="true"
            />
            {copy.architecture}
          </figcaption>
          <ol className="mt-5">
            {architecture.map(({ title, nodes }, index) => (
              <li key={title}>
                {index > 0 && (
                  <ArrowDownIcon
                    className="text-landing-accent mx-auto my-1.5 size-4"
                    aria-hidden="true"
                  />
                )}
                <div
                  className={cn(
                    "rounded-lg border p-3",
                    index === 1
                      ? "border-landing-accent/40 bg-landing-accent/8"
                      : "bg-secondary/50 border-border",
                  )}
                >
                  <p className="mb-2 text-sm font-medium">
                    {index === 1 ? `DeerFlow · ${title}` : title}
                  </p>
                  <ul className="flex flex-wrap gap-2">
                    {nodes.map(({ label, Icon }) => (
                      <li
                        key={label}
                        className="border-border bg-background flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-sm"
                      >
                        <Icon
                          className="text-landing-accent size-4"
                          aria-hidden="true"
                        />
                        {label}
                      </li>
                    ))}
                  </ul>
                </div>
              </li>
            ))}
          </ol>
        </figure>
      </div>
    </section>
  );
}
