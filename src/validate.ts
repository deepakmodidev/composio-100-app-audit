import fs from "node:fs/promises";
import { AppResearchSchema } from "./schema.js";

const rows = AppResearchSchema.array().parse(
  JSON.parse(
    await fs.readFile(
      new URL("../data/apps.final.json", import.meta.url),
      "utf8",
    ),
  ),
);
const flags: {
  appId: number;
  app: string;
  severity: "error" | "review";
  rule: string;
  detail: string;
}[] = [];
const flag = (
  row: any,
  severity: "error" | "review",
  rule: string,
  detail: string,
) => flags.push({ appId: row.id, app: row.name, severity, rule, detail });
for (const row of rows) {
  if (row.evidence.length < 1)
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
await fs.writeFile(
  new URL("../data/validator-flags.json", import.meta.url),
  JSON.stringify(flags, null, 2),
);
console.log(
  `${flags.filter((x) => x.severity === "error").length} errors, ${flags.filter((x) => x.severity === "review").length} review flags`,
);
if (flags.some((x) => x.severity === "error")) process.exitCode = 1;
