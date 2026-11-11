import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import crypto from "node:crypto";
const evidence = path.resolve("../docs/evidence");

test("every catalogue title has distinct, locally served artwork", async ({
  page,
}) => {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(evidence, "catalogue-art-manifest.json"), "utf8"),
  );
  const titles = JSON.parse(
    fs.readFileSync(path.join(evidence, "catalogue-art-titles.json"), "utf8"),
  );
  expect(manifest.map((entry) => entry.title_id)).toEqual(
    titles.map((title) => title.title_id),
  );
  const hashes = manifest.map((entry) => {
    const bytes = fs.readFileSync(
      path.resolve("src/assets/catalogue", entry.file),
    );
    const hash = crypto.createHash("sha256").update(bytes).digest("hex");
    expect(hash).toBe(entry.sha256);
    return hash;
  });
  expect(new Set(hashes).size).toBe(titles.length);
  expect(manifest.some((entry) => entry.official_poster)).toBeTruthy();
  await page.goto("/");
  const covers = page.locator("#collection .card img");
  await expect(covers).toHaveCount(20);
  expect(
    new Set(await covers.evaluateAll((images) => images.map((im) => im.src)))
      .size,
  ).toBe(20);
  for (const cover of await covers.all()) {
    await cover.scrollIntoViewIfNeeded();
    await expect
      .poll(() => cover.evaluate((im) => im.complete && im.naturalWidth > 0))
      .toBeTruthy();
  }
  const official = manifest.find((entry) => entry.official_poster);
  await page.goto(`/title/${official.title_id}`);
  await expect(page.locator(".title-hero .official-poster")).toBeVisible();
  await expect
    .poll(() =>
      page.locator(".title-hero img").evaluate((im) => im.naturalWidth),
    )
    .toBeGreaterThan(0);
});

test("Stitch concept is live with real discovery, quick look and native scroll motion", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator("#collection .card")).toHaveCount(20);
  await expect(page.locator(".stitch-hero h1")).toHaveText("The Last Local");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: path.join(evidence, "stitch-desktop.png"),
    animations: "disabled",
  });
  const quick = page.getByRole("button", { name: "Quick look", exact: true });
  await quick.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  for (let i = 0; i < 5; i++) await page.keyboard.press("Tab");
  expect(
    await page
      .getByRole("dialog")
      .evaluate((el) => el.contains(document.activeElement)),
  ).toBeTruthy();
  await page.screenshot({
    path: path.join(evidence, "stitch-quick-look.png"),
    animations: "disabled",
  });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(quick).toBeFocused();
  await page.getByRole("button", { name: "Feature this" }).click();
  await expect(page.locator(".stitch-hero h1")).toHaveText("Monsoon Letters");
  await quick.click();
  await page
    .getByRole("dialog")
    .getByRole("link", { name: "Open title" })
    .click();
  await expect(page).toHaveURL(/\/title\/2$/);
  await page.reload();
  await expect(page.locator(".title-hero")).toBeVisible();
  await page.goto("/");
  await expect(page.locator("#collection .card")).toHaveCount(20);
  await page.mouse.wheel(0, 450);
  await expect
    .poll(() =>
      page
        .locator(".stitch-hero")
        .evaluate((el) =>
          parseFloat(el.style.getPropertyValue("--stitch-depth")),
        ),
    )
    .toBeGreaterThan(0);
  await page.getByLabel("Search the collection").fill("Monsoon");
  const response = page.waitForResponse(
    (r) => r.url().includes("/catalog?") && r.url().includes("q=Monsoon"),
  );
  await page.getByRole("button", { name: "Search", exact: true }).click();
  expect((await response).ok()).toBeTruthy();
  await page
    .locator("#collection .card")
    .filter({ hasText: "Monsoon Letters" })
    .click();
  await expect(page).toHaveURL(/\/title\/2$/);
  expect(errors).toEqual([]);
});

test("Stitch mobile, reduced motion and legacy URL normalization", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of [320, 390, 768]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/");
    await expect(page.locator("#collection .card")).toHaveCount(20);
    await expect(page.locator(".stitch-backdrop")).toHaveCSS(
      "transform",
      "none",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    if (width === 390) {
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({
        path: path.join(evidence, "stitch-mobile.png"),
        animations: "disabled",
      });
      await page.screenshot({
        path: path.join(evidence, "stitch-mobile-full.png"),
        animations: "disabled",
        fullPage: true,
      });
    }
    await page.getByRole("button", { name: "Quick look", exact: true }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    expect(
      await page
        .getByRole("dialog")
        .evaluate((el) => el.scrollWidth <= el.clientWidth),
    ).toBeTruthy();
    await page.getByRole("button", { name: "Close quick look" }).click();
    await page.getByRole("link", { name: "Plans", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Choose Family" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  for (const route of ["/", "/stitch/", "/black-white/", "/cinematic/"]) {
    await page.goto(route);
    await expect(page).toHaveURL(/\/$/);
    expect(new URL(page.url()).pathname).toBe("/");
    await expect(page.locator("#collection .card")).toHaveCount(20);
    expect(await page.locator("html").getAttribute("data-theme")).toBe(
      "stitch",
    );
    await expect(page.locator(".stitch-hero")).toHaveCount(1);
  }
  for (const prefix of ["stitch", "black-white", "cinematic"]) {
    await page.goto(`/${prefix}/title/17?from=saved#details`);
    await expect(page).toHaveURL(/\/title\/17\?from=saved#details$/);
    await expect(page.locator(".title-hero")).toBeVisible();
  }
});

test("Stitch account, profile and video playback integration", async ({
  page,
}) => {
  await page.goto("/login");
  await page
    .getByLabel("Email address")
    .fill("kabir.malhotra@bingebox.example");
  await page
    .getByLabel("Password", { exact: true })
    .fill("BingeBox-Demo-2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/profiles$/);
  await page
    .getByRole("button", { name: "Watch as Kabir", exact: true })
    .click();
  await expect(page.locator(".stitch-hero-bottom")).toContainText(
    "Watching as Kabir",
  );
  await page.getByRole("link", { name: "Account", exact: true }).click();
  const stop = page.getByRole("button", { name: "Stop stream", exact: true });
  await expect(
    page.getByRole("heading", { name: "Your account", exact: true }),
  ).toBeVisible();
  const slots = await stop.count();
  for (let remaining = slots; remaining > 0; remaining--) {
    const stopped = page.waitForResponse(
      (response) =>
        response.request().method() === "DELETE" &&
        response.url().includes("/account/sessions/"),
    );
    await stop.first().click();
    expect((await stopped).ok()).toBeTruthy();
    await expect(
      page.getByRole("heading", { name: "Your account", exact: true }),
    ).toBeVisible();
    await expect(stop).toHaveCount(remaining - 1);
  }
  await page.goto("/title/7");
  await page.getByRole("button", { name: "Play / resume" }).click();
  await expect(page).toHaveURL(/\/watch$/);
  await expect
    .poll(() => page.locator("video").evaluate((el) => el.readyState))
    .toBeGreaterThanOrEqual(2);
  expect(await page.locator("video").evaluate((el) => el.duration)).toBe(60);
  await page.getByRole("button", { name: "Save & close" }).click();
  await expect(page).toHaveURL(/\/title\/7$/);
});
