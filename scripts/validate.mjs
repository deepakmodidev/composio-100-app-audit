import fs from "node:fs";
const root = new URL("../", import.meta.url);
const rows = JSON.parse(
  fs.readFileSync(new URL("data/apps.final.json", root), "utf8"),
);
const flags = [];
const flag = (row, severity, rule, detail) =>
  flags.push({ appId: row.id, app: row.name, severity, rule, detail });
for (const row of rows) {
  if (!row.evidence?.length)
    flag(row, "error", "missing-evidence", "At least one source is required.");
  if (row.mcp === "Official" && row.mcpScope === "None")
    flag(row, "error", "mcp-scope", "Official MCP requires an explicit scope.");
  if (
    row.mcp !== "Official" &&
    [
      "Action",
      "Read-only",
      "Docs-only",
      "Storefront",
      "Inbound agent",
      "Platform bridge",
    ].includes(row.mcpScope)
  )
    flag(
      row,
      "review",
      "mcp-provenance",
      "Scope implies a vendor surface but provenance is not Official.",
    );
  if (
    row.verdict === "Blocked" &&
    ["Self-serve", "Open-source/local"].includes(row.access)
  )
    flag(
      row,
      "review",
      "verdict-access",
      "Blocked conflicts with a direct credential path.",
    );
  if (
    row.access === "Self-serve" &&
    /(?:requires?|needs?|must|contact).{0,40}(?:partner|sales|contract)|(?:partner|sales)[ -]?gated|contract required/i.test(
      row.accessDetail,
    )
  )
    flag(
      row,
      "review",
      "self-serve-claim",
      "Access detail contains a likely gate.",
    );
  if (
    row.verdict === "Ready" &&
    /(partnership|partner path|admin approval|app review|sales-gated)/i.test(
      row.blocker,
    )
  )
    flag(
      row,
      "review",
      "ready-gate",
      "Ready verdict may understate a production gate.",
    );
  if (row.confidence === "High" && row.evidence.length === 1)
    flag(
      row,
      "review",
      "high-confidence-single-source",
      "High confidence rests on one source.",
    );
}
fs.writeFileSync(
  new URL("data/validator-flags.json", root),
  JSON.stringify(flags, null, 2),
);
const errors = flags.filter((x) => x.severity === "error").length;
const reviews = flags.filter((x) => x.severity === "review").length;
console.log(`${errors} errors, ${reviews} review flags`);
if (errors) process.exitCode = 1;
