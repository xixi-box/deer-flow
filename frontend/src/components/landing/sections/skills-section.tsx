import { type LandingCopy } from "@/core/i18n/locales/landing";

import { Section } from "../section";

export function SkillsSection({ copy }: { copy: LandingCopy }) {
  return (
    <Section id="skills" title={copy.skillsTitle} subtitle={copy.skillsIntro}>
      <ol className="grid gap-3 md:grid-cols-3">
        {copy.skillSteps.map(([title, description], index) => (
          <li
            className="bg-card border-border rounded-lg border p-5"
            key={title}
          >
            <h3 className="flex items-center gap-3 text-lg font-medium">
              <span
                className="text-landing-accent font-mono text-sm"
                aria-hidden="true"
              >
                {index + 1}.
              </span>
              {title}
            </h3>
            <p className="text-muted-foreground mt-2 text-base">
              {description}
            </p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
