import { cn } from "../ui";

export interface Segment {
  key: string;
  label: string;
  value: number;
  colorClass: string;
}

/** Pure HTML/CSS stacked distribution bar: gives immediate visual weight without heavy chart libs. */
export function StackedBar({ segments, className }: { segments: Segment[]; className?: string }) {
  const total = segments.reduce((sum, s) => sum + Math.max(0, s.value), 0);
  if (total <= 0) {
    return <div className={cn("h-2 w-full rounded-full bg-muted", className)} />;
  }
  return (
    <div
      className={cn("flex h-2 w-full overflow-hidden rounded-full bg-muted", className)}
      aria-hidden="true"
    >
      {segments.map((seg) => {
        if (seg.value <= 0) return null;
        const pct = (seg.value / total) * 100;
        return (
          <div
            key={seg.key}
            title={`${seg.label}: ${seg.value}`}
            style={{ width: `${pct}%` }}
            className={cn("h-full transition-[width] duration-300", seg.colorClass)}
          />
        );
      })}
    </div>
  );
}

/** Subtle horizontal proportion bar for breakdown rows. */
export function RatioBar({
  value,
  max,
  colorClass = "bg-slate-700",
}: {
  value: number;
  max: number;
  colorClass?: string;
}) {
  const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden="true">
      <div
        style={{ width: `${pct}%` }}
        className={cn("h-full rounded-full transition-[width] duration-300", colorClass)}
      />
    </div>
  );
}
