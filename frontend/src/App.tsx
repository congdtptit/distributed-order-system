import { AppShell, Burger, Group, NavLink, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconToolsKitchen2 } from "@tabler/icons-react";
import { Navigate, Route, NavLink as RouterLink, Routes, useLocation } from "react-router";
import { SCREENS, type Screen } from "./screens";
import { BranchScreen } from "./screens/branch/BranchScreen";
import { DemoScreen } from "./screens/demo/DemoScreen";
import { InventoryScreen } from "./screens/inventory/InventoryScreen";
import { KitchenScreen } from "./screens/kitchen/KitchenScreen";
import { MonitorScreen } from "./screens/monitor/MonitorScreen";
import { ReportsScreen } from "./screens/reports/ReportsScreen";

/** The screens built so far; the others show a placeholder naming their step. */
const BUILT: Record<string, () => React.JSX.Element> = {
  branch: BranchScreen,
  kitchen: KitchenScreen,
  inventory: InventoryScreen,
  monitor: MonitorScreen,
  reports: ReportsScreen,
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

/** The navbar groups, in the order SCREENS first names them. */
const GROUPS = [...new Set(SCREENS.map((s) => s.group))];

export function App() {
  const [opened, { toggle, close }] = useDisclosure();
  const { pathname } = useLocation();

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 240, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="lg"
    >
      <AppShell.Header>
        <Group h="100%" px="md" gap="sm" wrap="nowrap">
          <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Mở menu" />
          <ThemeIcon size={34} radius="md" variant="filled" aria-hidden>
            <IconToolsKitchen2 size={20} stroke={1.8} />
          </ThemeIcon>
          <Stack gap={0}>
            <Text fw={700} size="sm" lh={1.25}>
              Hệ thống đặt món
            </Text>
            <Text size="xs" c="dimmed" lh={1.25}>
              Chuỗi nhà hàng · chi nhánh, Kho và Bếp
            </Text>
          </Stack>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="sm" aria-label="Các màn hình">
        <Stack gap="md">
          {GROUPS.map((group) => (
            <Stack key={group} gap={2}>
              <Text size="xs" fw={600} c="dimmed" px="sm" pb={4} tt="uppercase" lts={0.4}>
                {group}
              </Text>
              {SCREENS.filter((s) => s.group === group).map((screen) => {
                const Icon = screen.icon;
                const section = screen.link.split("/")[1] ?? "";
                return (
                  <NavLink
                    key={screen.name}
                    component={RouterLink}
                    to={screen.link}
                    label={screen.label}
                    leftSection={<Icon size={18} stroke={1.7} aria-hidden="true" />}
                    active={pathname.startsWith(`/${section}`)}
                    onClick={close}
                  />
                );
              })}
            </Stack>
          ))}
        </Stack>
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
