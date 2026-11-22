import type { ReactNode } from "react";
import { cn } from "./cn";

export type Tone = "gray" | "blue" | "orange" | "yellow" | "green" | "dark" | "red" | "teal";

const SOFT_TONES: Record<Tone, string> = {
  gray: "bg-slate-200/85 text-slate-800 ring-1 ring-inset ring-slate-300",
  blue: "bg-sky-100 text-sky-900 ring-1 ring-inset ring-sky-300",
  orange: "bg-orange-100 text-orange-900 ring-1 ring-inset ring-orange-300",
  yellow: "bg-amber-100 text-amber-950 ring-1 ring-inset ring-amber-300",
  green: "bg-emerald-100 text-emerald-900 ring-1 ring-inset ring-emerald-300",
  dark: "bg-slate-800 text-white ring-1 ring-inset ring-slate-900",
  red: "bg-rose-100 text-rose-900 ring-1 ring-inset ring-rose-300",
  teal: "bg-teal-100 text-teal-900 ring-1 ring-inset ring-teal-300",
};

const OUTLINE_TONES: Record<Tone, string> = {
  gray: "bg-white text-slate-800 ring-1 ring-inset ring-slate-400",
  blue: "bg-white text-sky-900 ring-1 ring-inset ring-sky-400",
  orange: "bg-orange-50 text-orange-900 ring-1 ring-inset ring-orange-400",
  yellow: "bg-amber-50 text-amber-950 ring-1 ring-inset ring-amber-400",
  green: "bg-emerald-50 text-emerald-900 ring-1 ring-inset ring-emerald-400",
  dark: "bg-white text-slate-900 ring-1 ring-inset ring-slate-500",
  red: "bg-rose-50 text-rose-900 ring-1 ring-inset ring-rose-400",
  teal: "bg-teal-50 text-teal-900 ring-1 ring-inset ring-teal-400",
};

export function Badge({
  tone = "gray",
  variant = "soft",
  icon,
  children,
  className,
}: {
  tone?: Tone;
  variant?: "soft" | "outline";
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const palette = variant === "outline" ? OUTLINE_TONES[tone] : SOFT_TONES[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold leading-5 whitespace-nowrap",
        palette,
        className,
      )}
    >
      {icon && <span className="inline-flex shrink-0 items-center">{icon}</span>}
      <span>{children}</span>
    </span>
  );
}
