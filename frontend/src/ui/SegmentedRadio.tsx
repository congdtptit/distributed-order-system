import { useId } from "react";
import { cn } from "./cn";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

/** Accessible radio group styled as a crisp segmented pill bar (uses native inputs so
 * screens with zero buttons in <main> keep zero buttons). */
export function SegmentedRadio<T extends string>({
  name,
  "aria-label": ariaLabel,
  value,
  onChange,
  options,
  size = "md",
  className,
}: {
  name?: string;
  "aria-label": string;
  value: T;
  onChange: (value: T) => void;
  options: readonly SegmentedOption<T>[];
  size?: "sm" | "md";
  className?: string;
}) {
  const generatedId = useId();
  const groupName = name ?? `seg-${generatedId}`;

  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex items-center rounded-lg border border-line-strong bg-muted/90 p-0.5",
        className,
      )}
    >
      {options.map((opt) => {
        const id = `${groupName}-${opt.value}`;
        const checked = value === opt.value;
        return (
          <label
            key={opt.value}
            htmlFor={id}
            className={cn(
              "relative cursor-pointer rounded-md font-semibold whitespace-nowrap transition-all duration-150 select-none",
              size === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-xs",
              checked
                ? "bg-surface text-ink shadow-xs ring-1 ring-inset ring-line-strong"
                : "text-ink-secondary hover:text-ink",
            )}
          >
            <input
              id={id}
              type="radio"
              name={groupName}
              value={opt.value}
              checked={checked}
              onChange={() => onChange(opt.value)}
              className="sr-only"
            />
            {opt.label}
          </label>
        );
      })}
    </div>
  );
}
