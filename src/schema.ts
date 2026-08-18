import { z } from "zod";
export const EvidenceSchema = z.object({
  label: z.string(),
  url: z.string().url(),
});
export const AppResearchSchema = z.object({
  id: z.number().int().min(1).max(100),
  name: z.string(),
  category: z.string(),
  site: z.string().url(),
  what: z.string(),
  primaryAuth: z.enum([
    "OAuth2",
    "API key",
    "Basic",
    "Token",
    "Other",
    "None",
    "Mixed",
  ]),
  authMethods: z.array(z.string()).min(1),
  access: z.enum([
    "Self-serve",
    "Admin/paid",
    "Review/approval",
    "Partner/sales",
    "Open-source/local",
  ]),
  accessDetail: z.string(),
  apiStyle: z.array(z.string()).min(1),
  breadth: z.enum(["Broad", "Moderate", "Local", "Unknown"]),
  mcp: z.enum(["Official", "Community", "None", "Local skill"]),
  mcpScope: z.string(),
  verdict: z.enum(["Ready", "Ready with constraints", "Blocked"]),
  blocker: z.string(),
  confidence: z.enum(["High", "Medium", "Low"]),
  evidence: z.array(EvidenceSchema).min(1),
  notes: z.string(),
  verifiedAt: z.string(),
});
export type AppResearch = z.infer<typeof AppResearchSchema>;
