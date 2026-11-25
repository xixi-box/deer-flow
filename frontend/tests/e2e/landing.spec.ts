import { expect, test } from "@playwright/test";

import { mockLangGraphAPI } from "./utils/mock-api";

test.describe("Landing page", () => {
  test("explains the agent harness and its integrations", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light", reducedMotion: "reduce" });
    await page.goto("/");

    const hero = page.getByRole("region", { name: /DeerFlow.*agent harness/i });
    await expect(hero.getByRole("heading", { level: 1 })).toBeVisible();
    const diagram = hero.getByRole("figure", { name: "DeerFlow architecture" });
    for (const label of [
      "Models",
      "IM channels",
      "Sandboxes",
      "Skills",
      "MCP tools",
    ]) {
      await expect(diagram.getByText(label, { exact: true })).toBeVisible();
    }
    await expect(
      hero.getByRole("link", { name: "Quick Start" }),
    ).toHaveAttribute("href", "/en/docs/application/quick-start");
    await expect(hero.locator("canvas")).toHaveCount(0);
  });

  test("renders the header and hero section", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.locator("header").first().getByText("DeerFlow", { exact: true }),
    ).toBeVisible();
    await expect(page.locator("h1")).toHaveCount(1);
    await expect(page.locator("h1")).toContainText("DeerFlow");

    // "Get Started" call-to-action button in hero
    await expect(
      page.getByRole("link", { name: /get started/i }),
    ).toBeVisible();
  });

  test("shows repository counts and supports keyboard navigation", async ({
    page,
  }) => {
    await page.route("**/github-stars", (route) =>
      route.fulfill({ json: { stars: 42, forks: 7 } }),
    );
    await page.goto("/");

    await expect(page.getByText("42 stars")).toBeVisible();
    await expect(page.getByText("7 forks")).toBeVisible();

    const developers = page.getByRole("button", { name: "Developers" });
    await developers.focus();
    await developers.press("Enter");
    await expect(page.getByRole("menuitem", { name: "Blog" })).toHaveAttribute(
      "href",
      "/blog/posts",
    );
    await page.keyboard.press("Escape");
    await expect(developers).toBeFocused();

    const showcase = page.getByRole("link", {
      name: "Forecast 2026 Agent Trends and Opportunities",
    });
    await expect(showcase).toHaveAttribute(
      "href",
      "/showcase/7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
    );
  });

  test("supports theme, language, banner, and section controls on mobile", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/");

    const theme = page.getByRole("button", { name: "Dark mode" });
    await expect(page.locator("html")).toHaveClass(/\blight\b/);
    await theme.click();
    await expect(page.locator("html")).toHaveClass(/\bdark\b/);

    await page
      .getByRole("button", { name: "Dismiss community banner" })
      .click();
    await expect(
      page.getByRole("link", { name: "Join the DeerFlow community on GitHub" }),
    ).toHaveCount(0);

    await page.getByRole("button", { name: "Open menu" }).click();
    const menu = page.getByRole("dialog");
    await menu.getByRole("link", { name: "Case Studies" }).click();
    await expect(menu).toBeHidden();
    await expect(page).toHaveURL(/#case-studies$/);

    await page.getByRole("link", { name: "中文" }).click();
    await expect(page).toHaveURL(/\/zh$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "DeerFlow，开源智能体框架",
    );
    await expect(page.getByRole("link", { name: "快速开始" })).toHaveAttribute(
      "href",
      "/zh/docs/application/quick-start",
    );
    await expect(page.locator("html")).toHaveClass(/\bdark\b/);
    await page.getByRole("link", { name: "English" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "agent harness",
    );
  });

  for (const width of [320, 375, 390]) {
    test(`does not overflow at ${width}px width`, async ({ page }) => {
      await page.setViewportSize({ width, height: 812 });
      await page.goto("/");

      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
        .toBeLessThanOrEqual(width);
      await expect(page.locator("main").first()).toBeInViewport();
    });
  }

  test("Get Started link navigates to workspace", async ({ page }) => {
    mockLangGraphAPI(page);

    await page.goto("/");

    const getStarted = page.getByRole("link", { name: /get started/i });
    await getStarted.click();

    // Should redirect to /workspace/chats/new
    await page.waitForURL("**/workspace/chats/new");
    await expect(page).toHaveURL(/\/workspace\/chats\/new/);
  });
});
