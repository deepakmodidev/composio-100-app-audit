import "dotenv/config";
import fs from "node:fs/promises";
import OpenAI from "openai";
import { Composio } from "@composio/core";
import { OpenAIResponsesProvider } from "@composio/openai";
import { z } from "zod";
import { AppResearchSchema, type AppResearch } from "./schema.js";

const SeedSchema = z.array(
  z.object({
    id: z.number(),
    name: z.string(),
    category: z.string(),
    website: z.string().url(),
  }),
);
const outputPath = new URL("../data/agent-output.json", import.meta.url);
const seedPath = new URL("../data/seed.json", import.meta.url);
const USER_ID = "composio-audit-agent";
const MODEL = process.env.OPENAI_MODEL || "gpt-5.6";
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const composio = new Composio({ provider: new OpenAIResponsesProvider() });

const system = `You research app integration buildability for AI agents. Use official vendor documentation first.
Return only strict JSON matching the supplied schema. Distinguish vendor-native MCP, third-party MCP, docs-only MCP, and API buildability.
Never infer self-serve access from public docs alone. Mark uncertainty and preserve source URLs.`;

async function researchOne(
  app: { id: number; name: string; category: string; website: string },
  session: any,
): Promise<AppResearch> {
  const tools = await session.tools();
  let response = await client.responses.create({
    model: MODEL,
    tools,
    input: `${system}\nResearch: ${JSON.stringify(app)}\nReturn one JSON object with exactly these fields:\nid, name, category, site, what, primaryAuth, authMethods, access, accessDetail, apiStyle, breadth, mcp, mcpScope, verdict, blocker, confidence, evidence, notes, verifiedAt.\nUse the supplied app identity exactly. Set verifiedAt to 2026-08-18.`,
  });
  for (let i = 0; i < 8; i++) {
    const calls = response.output.filter(
      (x: any) => x.type === "function_call",
    );
    if (!calls.length) break;
    const results = await composio.provider.handleToolCalls(
      USER_ID,
      calls,
    );
    response = await client.responses.create({
      model: MODEL,
      tools,
      previous_response_id: response.id,
      input: results,
    });
  }
  const text = response.output_text.trim().replace(/^```json\s*|```$/g, "");
  const parsed = AppResearchSchema.parse(JSON.parse(text));
  if (
    parsed.id !== app.id ||
    parsed.name !== app.name ||
    parsed.category !== app.category ||
    parsed.site !== app.website
  ) {
    throw new Error(`Identity mismatch for ${app.id} ${app.name}`);
  }
  return parsed;
}

async function loadCheckpoint(): Promise<AppResearch[]> {
  try {
    return AppResearchSchema.array().parse(
      JSON.parse(await fs.readFile(outputPath, "utf8")),
    );
  } catch {
    return [];
  }
}

async function main() {
  if (!process.env.COMPOSIO_API_KEY || !process.env.OPENAI_API_KEY)
    throw new Error(
      "Set COMPOSIO_API_KEY and OPENAI_API_KEY. Use npm run demo for the keyless proof.",
    );
  const seed = SeedSchema.parse(
    JSON.parse(await fs.readFile(seedPath, "utf8")),
  );
  const session = await composio.create(USER_ID);
  const rows = await loadCheckpoint();
  const completed = new Set(rows.map((row) => row.id));
  for (const app of seed) {
    if (completed.has(app.id)) continue;
    try {
      const row = await researchOne(app, session);
      rows.push(row);
      rows.sort((a, b) => a.id - b.id);
      completed.add(app.id);
    } catch (error) {
      console.error(`FAILED ${app.id} ${app.name}`, error);
    }
    await fs.writeFile(outputPath, JSON.stringify(rows, null, 2));
  }
  console.log(`Wrote ${rows.length} rows to ${outputPath.pathname}`);
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
