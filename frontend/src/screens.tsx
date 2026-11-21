import {
  IconActivityHeartbeat,
  IconBox,
  IconBuildingStore,
  IconChefHat,
  IconLayoutColumns,
  IconReportAnalytics,
} from "@tabler/icons-react";
import type { ComponentType } from "react";

export interface Screen {
  /** Name used by the /screen skill (.claude/skills/screen/references/screens.md). */
  name: string;
  path: string;
  /** Link target in the navbar; differs from path when the route takes a parameter. */
  link: string;
  label: string;
  icon: ComponentType<{ size?: number; stroke?: number }>;
  /** The step of section 4 of docs/03-implementation-plan.md that builds the screen. */
  builtIn: string;
}

export const SCREENS: Screen[] = [
  {
    name: "branch",
    path: "/branch/:branchId",
    link: "/branch/POS01",
    label: "Chi nhánh",
    icon: IconBuildingStore,
    builtIn: "6b",
  },
  {
    name: "kitchen",
    path: "/kitchen",
    link: "/kitchen",
    label: "Bếp",
    icon: IconChefHat,
    builtIn: "6b",
  },
  {
    name: "inventory",
    path: "/inventory",
    link: "/inventory",
    label: "Kho",
    icon: IconBox,
    builtIn: "6b",
  },
  {
    name: "monitor",
    path: "/monitor",
    link: "/monitor",
    label: "Giám sát",
    icon: IconActivityHeartbeat,
    builtIn: "6b",
  },
  {
    name: "reports",
    path: "/reports",
    link: "/reports",
    label: "Quản lý",
    icon: IconReportAnalytics,
    builtIn: "7",
  },
  {
    name: "demo",
    path: "/demo/:branchId",
    link: "/demo/POS01",
    label: "Demo",
    icon: IconLayoutColumns,
    builtIn: "6b",
  },
];
