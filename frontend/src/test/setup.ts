import "@testing-library/jest-dom/vitest";
import { notifications } from "@mantine/notifications";
import { cleanup } from "@testing-library/react";
import { server } from "./server";

// jsdom lacks the browser APIs Mantine reads on start.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverStub;
window.HTMLElement.prototype.scrollIntoView = () => {};

// MSW: every request a test makes must have a handler (src/test/server.ts).
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  cleanup();
  notifications.clean(); // the store is module-wide: a notice must not leak into the next test
  server.resetHandlers();
});
afterAll(() => server.close());
