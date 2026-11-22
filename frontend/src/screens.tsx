import { Activity, BarChart3, ChefHat, Package, Store } from "lucide-react";
import type { ComponentType } from "react";

export interface Screen {
  /** Name used by the /screen skill (.claude/skills/screen/references/screens.md). */
  name: string;
  path: string;
  /** Link target in the navbar; differs from path when the route takes a parameter. */
  link: string;
  label: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  /** The step of section 4 of docs/03-implementation-plan.md that builds the screen. */
  builtIn: string;
  /** The navbar group the screen is listed under. */
  group: string;
}

export const SCREENS: Screen[] = [
  {
    name: "branch",
    path: "/branch/:branchId",
    link: "/branch/POS01",
    label: "Chi nhánh",
    icon: Store,
    builtIn: "6b",
    group: "Vận hành",
  },
  {
    name: "kitchen",
    path: "/kitchen",
    link: "/kitchen",
    label: "Bếp",
    icon: ChefHat,
    builtIn: "6b",
    group: "Vận hành",
  },
  {
    name: "inventory",
    path: "/inventory",
    link: "/inventory",
    label: "Kho",
    icon: Package,
    builtIn: "6b",
    group: "Vận hành",
  },
  {
    name: "monitor",
    path: "/monitor",
    link: "/monitor",
    label: "Giám sát",
    icon: Activity,
    builtIn: "6b",
    group: "Quản trị",
  },
  {
    name: "reports",
    path: "/reports",
    link: "/reports",
    label: "Quản lý",
    icon: BarChart3,
    builtIn: "7",
    group: "Quản trị",
  },
];
