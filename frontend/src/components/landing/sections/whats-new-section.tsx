import { type LandingCopy } from "@/core/i18n/locales/landing";

import { Section } from "../section";

export function WhatsNewSection({ copy }: { copy: LandingCopy }) {
  return (
    <Section id="whats-new" title={copy.whatsNew} subtitle={copy.whatsNewIntro}>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {copy.improvements.map(([title, description]) => (
          <li
            key={title}
            className="bg-card border-border rounded-lg border p-5"
          >
            <h3 className="text-lg font-medium">{title}</h3>
            <p className="text-muted-foreground mt-2">{description}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
