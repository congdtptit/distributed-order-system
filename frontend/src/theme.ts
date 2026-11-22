import { createTheme } from "@mantine/core";

// The one place for visual decisions (.claude/skills/screen/references/design.md).
// System fonts only: the demo must run without internet access.
export const theme = createTheme({
  primaryColor: "blue",
  defaultRadius: "sm",
  // design.md, "Motion": Mantine's transitions only, and none when the user asks for less.
  respectReducedMotion: true,
  fontFamily:
    "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
});
