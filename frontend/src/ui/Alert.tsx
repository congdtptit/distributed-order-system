import type { ReactNode } from "react";
import { cn } from "./cn";

export type AlertTone = "info" | "warning" | "danger" | "orange";

const TONES: Record<AlertTone, { box: string; title: string; icon: string }> = {
  info: {
    box: "border-sky-200 bg-sky-50/90 text-sky-950",
    title: "text-sky-900",
    icon: "text-sky-700",
  },
  warning: {
    box: "border-amber-200 bg-amber-50/95 text-amber-950",
    title: "text-amber-950",
    icon: "text-amber-700",
  },
  orange: {
    box: "border-orange-200 bg-orange-50/95 text-orange-950",
    title: "text-orange-950",
    icon: "text-orange-700",
  },
  danger: {
    box: "border-rose-200 bg-rose-50/95 text-rose-950",
    title: "text-rose-900",
    icon: "text-rose-700",
  },
};

export function Alert({
  tone = "warning",
  title,
  icon,
  role,
  "aria-label": ariaLabel,
  children,
  className,
}: {
  tone?: AlertTone;
  title?: ReactNode;
  icon?: ReactNode;
  role?: "alert" | "status";
  "aria-label"?: string;
  children: ReactNode;
  className?: string;
}) {
  const styles = TONES[tone];
  const boxClass = cn("rounded-xl border px-4 py-3 text-sm", styles.box, className);
  const inner = (
    <div className="flex items-start gap-2.5">
      {icon && (
        <span className={cn("mt-0.5 shrink-0", styles.icon)} aria-hidden="true">
          {icon}
        </span>
      )}
      <div className="min-w-0 flex-1 space-y-1">
        {title && <p className={cn("font-semibold leading-5", styles.title)}>{title}</p>}
        <div className="text-sm leading-relaxed">{children}</div>
      </div>
    </div>
  );

  if (role === "alert") {
    return (
      <div role="alert" aria-label={ariaLabel} className={boxClass}>
        {inner}
      </div>
    );
  }
  if (role === "status") {
    return (
      <output aria-label={ariaLabel} className={cn("block", boxClass)}>
        {inner}
      </output>
    );
  }
  return (
    <section aria-label={ariaLabel} className={boxClass}>
      {inner}
    </section>
  );
}
