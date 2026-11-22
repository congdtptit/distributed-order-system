// Renders a route with the providers main.tsx sets up, without polling and without retries,
// so that each test sees exactly the responses it stubs.

import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { App } from "../App";
import { theme } from "../theme";

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
      <MantineProvider theme={theme} env="test">
        <Notifications />
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[path]}>
            <App />
          </MemoryRouter>
        </QueryClientProvider>
      </MantineProvider>,
    ),
  };
}
