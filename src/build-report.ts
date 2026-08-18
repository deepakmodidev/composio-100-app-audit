import fs from "node:fs/promises";
const apps = JSON.parse(
  await fs.readFile(
    new URL("../data/apps.final.json", import.meta.url),
    "utf8",
  ),
);
const counts = (key: string) =>
  Object.fromEntries(
    [...new Set(apps.map((x: any) => x[key]))].map((v) => [
      v,
      apps.filter((x: any) => x[key] === v).length,
    ]),
  );
console.log(
  JSON.stringify(
    {
      apps: apps.length,
      verdict: counts("verdict"),
      access: counts("access"),
      mcp: counts("mcp"),
      priority: counts("priority"),
    },
    null,
    2,
  ),
);
