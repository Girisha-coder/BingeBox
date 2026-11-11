import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
const evidence = path.resolve("../docs/evidence/stitch-regression");
fs.mkdirSync(evidence, { recursive: true });
const password = "BingeBox-Demo-2026!";
async function login(page, email, staff = false) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  if (staff) await page.getByLabel("Staff account").check();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(staff ? /\/admin$/ : /\/profiles$/);
}

test("an expired or invalid session still permits signing in", async ({
  page,
  context,
}) => {
  await context.addCookies([
    {
      name: "bingebox_session",
      value: "invalid.session",
      url: process.env.BASE_URL,
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);
  await page.goto("/login");
  await expect(page.getByLabel("Email address")).toBeVisible();
  await login(page, "dev.menon@bingebox.example");
  await expect(
    page.getByRole("button", { name: "Watch as Dev" }),
  ).toBeVisible();
});
test("guest discovery, preview, filters and responsive layout", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "The collection162" }),
  ).toBeVisible();
  await page.screenshot({ path: path.join(evidence, "desktop-home.png") });
  await page.getByLabel("Search the collection").fill("Monsoon");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await page.locator(".card").filter({ hasText: "Monsoon Letters" }).click();
  await expect(page).toHaveURL(/\/title\/2$/);
  await expect(
    page.getByRole("heading", {
      name: "Monsoon Letters",
      exact: true,
      level: 1,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Sign in to watch" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Play / resume" })).toHaveCount(
    0,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".card")).toHaveCount(20);
  await page.screenshot({
    path: path.join(evidence, "mobile-home.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("link", { name: "Plans", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Choose Family" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
test("W3 actual video, save, resume, completion and review", async ({
  page,
}) => {
  await login(page, "dev.menon@bingebox.example");
  await page.getByRole("button", { name: "Watch as Dev" }).click();
  await page.getByLabel("Search the collection").fill("A Minute of Rain");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await page
    .locator("#collection .card")
    .filter({ hasText: "A Minute of Rain" })
    .click();
  await page.getByRole("button", { name: "Play / resume" }).click();
  await expect(page).toHaveURL(/\/watch$/);
  const progressSaves = [];
  const observeProgress = (request) => {
    if (request.url().endsWith("/api/playback/progress")) {
      progressSaves.push({ time: Date.now(), position: request.postDataJSON().position });
    }
  };
  page.on("request", observeProgress);
  const video = page.locator("video");
  await expect
    .poll(() => video.evaluate((v) => v.readyState))
    .toBeGreaterThanOrEqual(2);
  expect(await video.evaluate((v) => v.duration)).toBe(60);
  await video.evaluate((v) => v.play());
  await expect.poll(() => progressSaves.length, { timeout: 26000 }).toBeGreaterThanOrEqual(2);
  expect(progressSaves[1].time - progressSaves[0].time).toBeGreaterThanOrEqual(10000);
  expect(progressSaves[1].time - progressSaves[0].time).toBeLessThanOrEqual(15000);
  expect(progressSaves[1].position).toBeGreaterThan(progressSaves[0].position);
  page.off("request", observeProgress);
  await video.evaluate((v) => {
    v.currentTime = 24;
    v.pause();
  });
  await page.screenshot({ path: path.join(evidence, "player.png") });
  await page.getByRole("button", { name: "Save & close" }).click();
  await page.getByRole("button", { name: "Play / resume" }).click();
  await expect
    .poll(() => video.evaluate((v) => v.currentTime))
    .toBeGreaterThanOrEqual(24);
  await video.evaluate((v) => {
    v.currentTime = 55;
    v.pause();
  });
  await page.getByRole("button", { name: "Save & close" }).click();
  await page
    .getByLabel("Your review")
    .fill("A short, quiet moment. Playback and resume worked.");
  await page.getByRole("button", { name: "Save review" }).click();
  await expect(
    page
      .locator(".review")
      .getByText("A short, quiet moment. Playback and resume worked."),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(evidence, "title-review.png"),
    fullPage: true,
  });
});
test("W1 profile cap, downgrade refusal, plan change and auto-renew", async ({
  page,
}) => {
  await login(page, "kabir.malhotra@bingebox.example");
  await page.getByLabel("Profile name").fill("Third viewer");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(page.getByRole("alert")).toContainText("no free profile slots");
  await page.getByRole("link", { name: "Plans", exact: true }).click();
  await page.getByRole("button", { name: "Choose Basic" }).click();
  await expect(page.getByRole("alert")).toContainText("Remove extra profiles");
  await page.getByRole("button", { name: "Choose Family" }).click();
  await expect(page).toHaveURL(/\/profiles$/);
  await page.getByLabel("Profile name").fill("Third viewer");
  await page.getByRole("button", { name: "Create profile" }).click();
  await expect(
    page.getByRole("button", { name: "Watch as Third viewer" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Account", exact: true }).click();
  await page.getByLabel("Automatically renew every month").uncheck();
  await expect(
    page.getByLabel("Automatically renew every month"),
  ).not.toBeChecked();
  await page.screenshot({
    path: path.join(evidence, "account.png"),
    fullPage: true,
  });
});
test("kids browsing and password-protected switching", async ({ page }) => {
  await login(page, "rohan.desai@bingebox.example");
  await page.getByRole("button", { name: "Watch as Tara" }).click();
  await page.getByLabel("Search the collection").fill("Midnight Signal");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByText("No stories match these filters. Try a broader search."),
  ).toBeVisible();
  await page.getByRole("link", { name: "Tara · Kids" }).click();
  await page.getByLabel("Account password").fill("wrong");
  await page.getByRole("button", { name: "Unlock account" }).click();
  await expect(page.getByRole("alert")).toContainText("incorrect");
  await page.getByLabel("Account password").fill(password);
  await page.getByRole("button", { name: "Unlock account" }).click();
  await expect(
    page.getByRole("heading", { name: "Who’s watching?" }),
  ).toBeVisible();
});
test("studio catalogue CRUD and billing role reports", async ({ page }) => {
  await login(page, "catalogue@staff.bingebox.example", true);
  await expect(
    page.getByRole("button", { name: "Accounts", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Genres", exact: true }).click();
  await page.getByLabel("Genre name").fill("Browser test genre");
  await page.getByRole("button", { name: "Save record" }).click();
  await expect(page.getByText("Record saved.", { exact: true })).toBeVisible();
  const row = page.getByRole("row").filter({ hasText: "Browser test genre" });
  await row.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Genre name").fill("Updated browser genre");
  await page.getByRole("button", { name: "Save record" }).click();
  page.once("dialog", (d) => d.accept());
  await page
    .getByRole("row")
    .filter({ hasText: "Updated browser genre" })
    .getByRole("button", { name: "Delete" })
    .click();
  await expect(
    page.getByRole("row").filter({ hasText: "Updated browser genre" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "billing@staff.bingebox.example", true);
  await expect(
    page.getByRole("button", { name: "Titles", exact: true }),
  ).toHaveCount(0);
  const dev = page
    .getByRole("row")
    .filter({ hasText: "dev.menon@bingebox.example" });
  await dev.getByRole("button", { name: "Suspend" }).click();
  await expect(dev.getByRole("button", { name: "Reinstate" })).toBeVisible();
  await dev.getByRole("button", { name: "Reinstate" }).click();
  await page.getByRole("button", { name: "Reports", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A closer look" }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Family", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: path.join(evidence, "studio-report.png") });
  await page
    .getByLabel("Report", { exact: true })
    .selectOption("rating-comparison");
  await expect(
    page.getByRole("columnheader", { name: "user rating" }),
  ).toBeVisible();
});

test("W1 staff renewal processing expires an opted-out subscription", async ({
  page,
}) => {
  await login(page, "billing@staff.bingebox.example", true);
  const day = new Date();
  day.setDate(day.getDate() + 2);
  await page
    .getByLabel("Process through")
    .fill(day.toLocaleDateString("en-CA"));
  await page.getByRole("button", { name: "Run renewals" }).click();
  await expect(page.getByRole("status")).toContainText(
    "1 subscriptions expired",
  );
  await expect(
    page.getByRole("row").filter({ hasText: "meera.iyer@bingebox.example" }),
  ).toContainText("expired");
});
