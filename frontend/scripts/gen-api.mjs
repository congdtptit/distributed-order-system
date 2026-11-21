// Generate the TypeScript API types from the services' OpenAPI documents.
//   1. docker compose exec tools python scripts/dump_openapi.py   writes src/api/openapi/<service>.json
//   2. docker compose exec frontend npm run gen:api                       writes src/api/generated/<service>.ts
// The generated files are committed and never edited by hand (.claude/rules/frontend.md).

import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";

const input = "src/api/openapi";
const output = "src/api/generated";

for (const file of readdirSync(input).filter((f) => f.endsWith(".json"))) {
  const name = file.replace(/\.json$/, "");
  execFileSync(
    "npx",
    ["--no-install", "openapi-typescript", `${input}/${file}`, "-o", `${output}/${name}.ts`],
    {
      stdio: "inherit",
    },
  );
}
