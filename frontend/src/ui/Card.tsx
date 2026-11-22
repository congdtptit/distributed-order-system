import type { ReactNode } from "react";
import { cn } from "./cn";

export function Card({
  children,
  className,
  as: Component = "div",
  ...props
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
  "aria-label"?: string;
  "data-ticket"?: string;
}) {
  return (
    <Component
      className={cn(
        "rounded-xl border border-line bg-surface shadow-[var(--shadow-card)]",
        className,
      )}
      {...props}
    >
      {children}
    </Component>
  );
}

export function Panel({
  title,
  count,
  actions,
  flush = false,
  label,
  level = 2,
  children,
  className,
}: {
  title: string;
  count?: number | undefined;
  actions?: ReactNode | undefined;
  flush?: boolean;
  label?: string | undefined;
  level?: 2 | 3 | 4;
  children: ReactNode;
  className?: string | undefined;
}) {
  const Heading = level === 2 ? "h2" : level === 3 ? "h3" : "h4";
  return (
    <section
      aria-label={label ?? title}
      className={cn(
        "overflow-hidden rounded-xl border border-line bg-surface shadow-[var(--shadow-card)]",
        className,
      )}
    >
      <div className="flex min-h-12 flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Heading className="text-sm font-semibold tracking-[-0.01em] text-ink">{title}</Heading>
          {count !== undefined && (
            <span className="rounded-md bg-subtle px-1.5 py-0.5 font-mono text-xs font-medium text-ink-secondary tabular-nums">
              {count}
            </span>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      <div className={flush ? "" : "p-4"}>{children}</div>
    </section>
  );
}
