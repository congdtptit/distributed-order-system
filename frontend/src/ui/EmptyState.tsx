import type { ComponentType, ReactNode } from "react";
import { cn } from "./cn";

type IconComponent = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;

export function EmptyState({
  icon: Icon,
  children,
  className,
}: {
  icon: IconComponent;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 px-4 py-8 text-center",
        className,
      )}
    >
      <Icon className="h-5 w-5 text-ink-muted/80" aria-hidden />
      <p className="max-w-md text-sm leading-relaxed text-ink-secondary">{children}</p>
    </div>
  );
}
