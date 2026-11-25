import { type ReactNode } from "react";

export function Section({
  id,
  title,
  subtitle,
  children,
}: {
  id: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="border-border border-b last:border-b-0"
    >
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-8 sm:py-18">
        <h2
          id={`${id}-title`}
          className="font-serif text-3xl leading-tight tracking-tight sm:text-4xl"
        >
          {title}
        </h2>
        <p className="text-muted-foreground mt-2 max-w-2xl text-base leading-relaxed">
          {subtitle}
        </p>
        <div className="mt-7">{children}</div>
      </div>
    </section>
  );
}
