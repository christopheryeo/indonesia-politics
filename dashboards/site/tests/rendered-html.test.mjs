import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the media intelligence dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Sentient\.io Media Intelligence<\/title>/i);
  assert.match(html, /Media intelligence \/ Indonesia politics/);
  assert.match(html, /Articles monitored/);
  assert.match(html, /Coverage velocity/);
  assert.match(html, /Issue radar/);
  assert.match(html, /Knowledge graph/);
  assert.match(html, /Top(?:\s|<!-- -->)*countries/);
  assert.match(html, /Empty vault ready/);
  assert.match(html, /Awaiting first ingest/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("keeps the dashboard self-contained and vault-generated", async () => {
  const [data, client, page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/dashboard-data.json", import.meta.url), "utf8"),
    readFile(new URL("../app/dashboard-client.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  const parsed = JSON.parse(data);
  assert.equal(parsed.summary.articles, 0);
  assert.equal(parsed.summary.entities, 0);
  assert.equal(parsed.months.length, 0);
  assert.equal(parsed.top.countries.length, 0);

  assert.match(client, /"use client"/);
  assert.match(client, /function Dashboard/);
  assert.match(client, /selectedIssue/);
  assert.match(page, /import Dashboard from "\.\/dashboard-client"/);
  assert.match(page, /<Dashboard \/>/);
  assert.match(layout, /Sentient\.io Media Intelligence/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});
