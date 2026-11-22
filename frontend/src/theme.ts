import {
  ActionIcon,
  Alert,
  AppShell,
  Badge,
  Button,
  Card,
  createTheme,
  Modal,
  NavLink,
  Paper,
  SegmentedControl,
  Table,
} from "@mantine/core";

// The one place for visual decisions (.claude/skills/screen/references/design.md).
// System fonts only: the demo must run without internet access.
export const theme = createTheme({
  primaryColor: "indigo",
  primaryShade: 7,
  defaultRadius: "md",
  // design.md, "Motion": Mantine's transitions only, and none when the user asks for less.
  respectReducedMotion: true,
  fontFamily:
    "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
  // design.md, "Type scale": one page title size, then section titles; never a 34px heading.
  headings: {
    fontWeight: "650",
    sizes: {
      h1: { fontSize: "1.5rem", lineHeight: "1.3" },
      h2: { fontSize: "1.125rem", lineHeight: "1.35" },
      h3: { fontSize: "1rem", lineHeight: "1.4" },
      h4: { fontSize: "0.9375rem", lineHeight: "1.4" },
      h5: { fontSize: "0.875rem", lineHeight: "1.4" },
    },
  },
  shadows: {
    xs: "0 1px 2px rgba(16, 24, 40, 0.05)",
    sm: "0 1px 3px rgba(16, 24, 40, 0.08), 0 1px 2px rgba(16, 24, 40, 0.04)",
  },
  components: {
    AppShell: AppShell.extend({
      styles: (t) => ({
        main: { backgroundColor: t.colors.gray[0] },
        header: { borderBottomColor: t.colors.gray[2] },
        navbar: { borderRightColor: t.colors.gray[2] },
      }),
    }),
    // Surfaces: white, a hairline border and the faintest shadow, on the grey page.
    Paper: Paper.extend({ defaultProps: { withBorder: true, shadow: "xs", radius: "md" } }),
    Card: Card.extend({ defaultProps: { withBorder: true, shadow: "xs", radius: "md" } }),
    Button: Button.extend({ defaultProps: { radius: "md" } }),
    ActionIcon: ActionIcon.extend({ defaultProps: { radius: "md" } }),
    Badge: Badge.extend({
      defaultProps: { radius: "sm", variant: "light", size: "md" },
      styles: { label: { textTransform: "none", fontWeight: 600, letterSpacing: 0 } },
    }),
    Alert: Alert.extend({ defaultProps: { radius: "md" } }),
    Modal: Modal.extend({ defaultProps: { radius: "md", centered: true } }),
    NavLink: NavLink.extend({
      styles: (t) => ({
        root: { borderRadius: t.radius.md, fontWeight: 500 },
        label: { fontSize: t.fontSizes.sm },
      }),
    }),
    SegmentedControl: SegmentedControl.extend({ defaultProps: { radius: "md" } }),
    // Tables: a quiet header band; numbers line up (tabular figures).
    Table: Table.extend({
      defaultProps: { verticalSpacing: "sm", horizontalSpacing: "md" },
      styles: (t) => ({
        thead: { backgroundColor: t.colors.gray[0] },
        th: {
          fontSize: t.fontSizes.xs,
          fontWeight: 600,
          color: t.colors.gray[7],
          whiteSpace: "nowrap",
        },
        td: { fontVariantNumeric: "tabular-nums" },
      }),
    }),
  },
});
