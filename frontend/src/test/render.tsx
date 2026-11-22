// Renders a route with the providers main.tsx sets up, without polling and without retries,
// so that each test sees exactly the responses it stubs.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { App } from "../App";
import { ToastViewport, TooltipProvider } from "../ui";

export function renderRoute(path: string) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchInterval: false },
      mutations: { retry: false },
    },
  });
  return {
    client,
    ...render(
      <TooltipProvider>
        <ToastViewport />
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[path]}>
            <App />
          </MemoryRouter>
        </QueryClientProvider>
      </TooltipProvider>,
    ),
  };
}
