/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The screens call /api/<service>/...; the dev server forwards each prefix to its service
// (section 2 of docs/03-implementation-plan.md, "The screens decide nothing"). The service
// containers run in compose; a target can be overridden with API_<NAME>.
const services: Record<string, string> = {
  pos01: "http://pos01:8000",
  pos02: "http://pos02:8000",
  online: "http://online:8000",
  inventory: "http://inventory:8000",
  kitchen: "http://kitchen:8000",
  reports: "http://query:8000",
};

const proxy = Object.fromEntries(
  Object.entries(services).map(([name, target]) => [
    `/api/${name}`,
    {
      target: process.env[`API_${name.toUpperCase()}`] ?? target,
      changeOrigin: true,
      rewrite: (path: string) => path.slice(`/api/${name}`.length) || "/",
    },
  ]),
);

export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173, strictPort: true, proxy },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
