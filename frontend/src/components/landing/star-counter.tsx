"use client";

import { StarFilledIcon } from "@radix-ui/react-icons";
import { GitForkIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { NumberTicker } from "@/components/ui/number-ticker";

type RepositoryCounts = { stars: number; forks?: number };

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

/** Load public counts at runtime while keeping the page statically rendered. */
export function StarCounter({
  labels,
}: {
  labels?: { stars: string; forks: string };
}) {
  const [counts, setCounts] = useState<RepositoryCounts | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    // The root layout has no query provider; this one-shot decorative request
    // leaves homepage rendering static and GitHub caching on the server.
    void fetch("/github-stars", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok || response.status === 204) return;
        const data = (await response.json()) as {
          stars?: unknown;
          forks?: unknown;
        };
        if (!controller.signal.aborted && isCount(data.stars)) {
          setCounts({
            stars: data.stars,
            forks: isCount(data.forks) ? data.forks : undefined,
          });
        }
      })
      .catch(() => {
        // An unavailable optional counter must not break the GitHub link.
      });
    return () => controller.abort();
  }, []);

  if (!counts) return null;
  if (labels) {
    return (
      <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-2 font-mono tabular-nums">
        <span className="inline-flex items-center gap-1.5">
          <StarFilledIcon aria-hidden="true" className="size-4" />
          {counts.stars.toLocaleString()} {labels.stars}
        </span>
        {counts.forks !== undefined && (
          <span className="inline-flex items-center gap-1.5">
            <GitForkIcon aria-hidden="true" className="size-4" />
            {counts.forks.toLocaleString()} {labels.forks}
          </span>
        )}
      </div>
    );
  }

  return (
    <>
      <StarFilledIcon className="size-4 transition-colors duration-300 group-hover:text-yellow-500" />
      <NumberTicker className="font-mono tabular-nums" value={counts.stars} />
    </>
  );
}
