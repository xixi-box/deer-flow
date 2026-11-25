import { GitHubLogoIcon } from "@radix-ui/react-icons";

import { Button } from "@/components/ui/button";
import { type LandingCopy } from "@/core/i18n/locales/landing";

import { repositoryURL } from "../hero";
import { Section } from "../section";

export function CommunitySection({ copy }: { copy: LandingCopy }) {
  return (
    <Section
      id="community"
      title={copy.communityTitle}
      subtitle={copy.communityIntro}
    >
      <Button
        className="bg-landing-accent text-landing-accent-foreground hover:bg-landing-accent/90 h-11"
        asChild
      >
        <a href={repositoryURL}>
          <GitHubLogoIcon aria-hidden="true" />
          {copy.contribute}
        </a>
      </Button>
    </Section>
  );
}
