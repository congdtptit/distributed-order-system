// The page structure every screen uses (.claude/skills/screen/references/design.md, "Layout"):
// a page header, white panels on the grey page, and a row of figures. Screens compose these
// rather than spacing titles and tables themselves.

import {
  Box,
  Divider,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import type { ComponentType, ReactNode } from "react";

type Icon = ComponentType<{ size?: number; stroke?: number; "aria-hidden"?: boolean }>;

/** The page title (level 1, or 2 when the screen is embedded in the demo page), one line on
 * what the screen is for, and the screen's controls on the right. */
export function PageHeader({
  title,
  description,
  actions,
  level = 1,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  level?: 1 | 2;
}) {
  return (
    <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
      <Stack gap={2} style={{ minWidth: 0, flex: "1 1 280px" }}>
        <Title order={level} size={level === 1 ? "h1" : "h2"}>
          {title}
        </Title>
        {description && (
          <Text size="sm" c="dimmed" maw={720}>
            {description}
          </Text>
        )}
      </Stack>
      {actions && (
        <Group gap="sm" wrap="wrap" justify="flex-end">
          {actions}
        </Group>
      )}
    </Group>
  );
}

/** A white panel with a title bar. ``flush`` drops the body padding, for a table that runs to
 * the panel's edges. */
export function Panel({
  title,
  level = 2,
  count,
  actions,
  flush = false,
  label,
  children,
}: {
  title: string;
  level?: 2 | 3 | 4;
  /** A number shown in grey after the title, outside the heading's name. */
  count?: number | undefined;
  actions?: ReactNode;
  flush?: boolean;
  /** The accessible name of the panel's region; the title by default. */
  label?: string;
  children: ReactNode;
}) {
  return (
    <Paper component="section" aria-label={label ?? title} style={{ overflow: "hidden" }}>
      <Group justify="space-between" wrap="wrap" gap="xs" px="md" py="sm" mih={52}>
        <Group gap={8} wrap="nowrap">
          <Title order={level} size="h4">
            {title}
          </Title>
          {count !== undefined && (
            <Text size="sm" c="dimmed" fw={600} style={{ fontVariantNumeric: "tabular-nums" }}>
              {count}
            </Text>
          )}
        </Group>
        {actions}
      </Group>
      <Divider color="gray.2" />
      <Box p={flush ? 0 : "md"}>{children}</Box>
    </Paper>
  );
}

export interface Figure {
  label: string;
  value: ReactNode;
  icon: Icon;
  color: string;
  hint?: ReactNode;
}

/** A row of figures at the top of an office screen. Each figure comes from an API response. */
export function Figures({ figures }: { figures: Figure[] }) {
  return (
    <SimpleGrid cols={{ base: 1, xs: 2, md: figures.length > 3 ? 4 : figures.length }} spacing="md">
      {figures.map((f) => (
        <Paper key={f.label} p="md">
          <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
            <Stack gap={4} style={{ minWidth: 0 }}>
              <Text size="xs" c="dimmed" fw={600}>
                {f.label}
              </Text>
              <Text fz={26} fw={700} lh={1.1} style={{ fontVariantNumeric: "tabular-nums" }}>
                {f.value}
              </Text>
              {f.hint && (
                <Text size="xs" c="dimmed">
                  {f.hint}
                </Text>
              )}
            </Stack>
            <ThemeIcon variant="light" color={f.color} size={40} radius="md">
              <f.icon size={22} stroke={1.7} aria-hidden />
            </ThemeIcon>
          </Group>
        </Paper>
      ))}
    </SimpleGrid>
  );
}

/** What an empty list will show and why it is empty (design.md, "Behaviour"). */
export function Empty({ icon: IconC, children }: { icon: Icon; children: ReactNode }) {
  return (
    <Stack align="center" gap={6} py="xl" px="md">
      <ThemeIcon variant="light" color="gray" size={44} radius="xl">
        <IconC size={22} stroke={1.6} aria-hidden />
      </ThemeIcon>
      <Text size="sm" c="dimmed" ta="center" maw={420}>
        {children}
      </Text>
    </Stack>
  );
}
