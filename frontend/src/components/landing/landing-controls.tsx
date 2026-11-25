"use client";

import {
  ArrowUpRightIcon,
  ChevronDownIcon,
  MoonIcon,
  SunIcon,
  XIcon,
} from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { type MobileNavLink } from "./mobile-nav";

export function LandingMenus({
  label,
  menus,
}: {
  label: string;
  menus: { name: string; links: MobileNavLink[] }[];
}) {
  return (
    <nav aria-label={label} className="hidden items-center sm:flex">
      {menus.map(({ name, links }) => (
        <DropdownMenu key={name}>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="px-2.5">
              {name}
              <ChevronDownIcon aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="bg-background">
            {links.map(({ label, href }) => (
              <DropdownMenuItem key={href} asChild>
                <Link href={href}>{label}</Link>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      ))}
    </nav>
  );
}

export function LandingThemeToggle({ label }: { label: string }) {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <Button
      aria-label={label}
      aria-pressed={resolvedTheme === "dark"}
      className="size-11"
      size="icon"
      variant="ghost"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      <MoonIcon aria-hidden="true" className="dark:hidden" />
      <SunIcon aria-hidden="true" className="hidden dark:block" />
    </Button>
  );
}

export function LandingBanner({
  invite,
  dismiss,
}: {
  invite: string;
  dismiss: string;
}) {
  const [open, setOpen] = useState(true);

  if (!open) return null;

  return (
    <div className="border-border bg-landing-accent/8 border-b">
      <div className="mx-auto flex min-h-11 max-w-6xl items-center justify-between gap-2 px-4 sm:px-8">
        <a
          href="https://github.com/bytedance/deer-flow/discussions"
          className="text-landing-accent inline-flex min-h-11 items-center gap-1.5 rounded-sm py-2 text-sm font-medium underline-offset-4 hover:underline"
        >
          {invite}
          <ArrowUpRightIcon aria-hidden="true" className="size-4 shrink-0" />
        </a>
        <Button
          type="button"
          aria-label={dismiss}
          className="size-11"
          variant="ghost"
          size="icon"
          onClick={() => setOpen(false)}
        >
          <XIcon aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
