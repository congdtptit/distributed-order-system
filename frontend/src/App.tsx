import { AppShell, Burger, Group, NavLink, Stack, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Navigate, Route, NavLink as RouterLink, Routes, useLocation } from "react-router";
import { SCREENS, type Screen } from "./screens";
import { BranchScreen } from "./screens/branch/BranchScreen";
import { DemoScreen } from "./screens/demo/DemoScreen";
import { InventoryScreen } from "./screens/inventory/InventoryScreen";
import { KitchenScreen } from "./screens/kitchen/KitchenScreen";
import { MonitorScreen } from "./screens/monitor/MonitorScreen";

/** The screens built so far; the others show a placeholder naming their step. */
const BUILT: Record<string, () => React.JSX.Element> = {
  branch: BranchScreen,
  kitchen: KitchenScreen,
  inventory: InventoryScreen,
  monitor: MonitorScreen,
  demo: DemoScreen,
};

function Placeholder({ screen }: { screen: Screen }) {
  return (
    <Stack gap="xs">
      <Title order={1}>{screen.label}</Title>
      <Text c="dimmed">Màn hình này được làm ở bước {screen.builtIn}.</Text>
    </Stack>
  );
}

export function App() {
  const [opened, { toggle, close }] = useDisclosure();
  const { pathname } = useLocation();

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md">
          <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Mở menu" />
          <Text fw={600}>Hệ thống đặt món</Text>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs" aria-label="Các màn hình">
        {SCREENS.map((screen) => {
          const Icon = screen.icon;
          const section = screen.link.split("/")[1] ?? "";
          return (
            <NavLink
              key={screen.name}
              component={RouterLink}
              to={screen.link}
              label={screen.label}
              leftSection={<Icon size={18} stroke={1.6} aria-hidden="true" />}
              active={pathname.startsWith(`/${section}`)}
              onClick={close}
            />
          );
        })}
      </AppShell.Navbar>

      <AppShell.Main>
        <Routes>
          <Route path="/" element={<Navigate to="/branch/POS01" replace />} />
          {SCREENS.map((screen) => {
            const Built = BUILT[screen.name];
            return (
              <Route
                key={screen.name}
                path={screen.path}
                element={Built ? <Built /> : <Placeholder screen={screen} />}
              />
            );
          })}
          <Route path="*" element={<Text>Không có màn hình này.</Text>} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}
