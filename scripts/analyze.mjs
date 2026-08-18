import fs from "node:fs";
const rows = JSON.parse(
  fs.readFileSync(new URL("../data/apps.final.json", import.meta.url)),
);
const count = (k) =>
  Object.fromEntries(
    [...new Set(rows.map((x) => x[k]))].map((v) => [
      v,
      rows.filter((x) => x[k] === v).length,
    ]),
  );
console.log("Composio 100-app audit proof");
console.log({
  apps: rows.length,
  verdict: count("verdict"),
  access: count("access"),
  mcp: count("mcp"),
  priority: count("priority"),
});
console.log(
  "Sample easy wins:",
  rows
    .filter((x) => x.priority === "Easy win")
    .slice(0, 12)
    .map((x) => x.name)
    .join(", "),
);
