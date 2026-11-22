import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { useId } from "react";
import { cn } from "./cn";

export interface SelectOption {
  value: string;
  label: string;
}

export function Select({
  label,
  placeholder = "Chọn một mục",
  required = false,
  options,
  value,
  onValueChange,
  error,
}: {
  label: string;
  placeholder?: string;
  required?: boolean;
  options: SelectOption[];
  value: string | null;
  onValueChange: (value: string) => void;
  error?: string | null;
}) {
  const labelId = useId();
  const errorId = useId();

  return (
    <div className="space-y-1.5">
      <span id={labelId} className="block text-sm font-medium text-ink">
        {label}
        {required && (
          <span className="ml-0.5 text-rose-600" aria-hidden="true">
            *
          </span>
        )}
      </span>
      <SelectPrimitive.Root value={value ?? ""} onValueChange={onValueChange}>
        <SelectPrimitive.Trigger
          aria-labelledby={labelId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={cn(
            "flex h-10 w-full items-center justify-between rounded-lg border bg-surface px-3 text-sm text-ink transition-colors focus:outline-none focus:ring-2 focus:ring-accent/30",
            error ? "border-rose-500" : "border-line-strong hover:border-ink-muted",
            !value && "text-ink-muted",
          )}
        >
          <SelectPrimitive.Value placeholder={placeholder} />
          <SelectPrimitive.Icon>
            <ChevronDown className="h-4 w-4 text-ink-muted" aria-hidden="true" />
          </SelectPrimitive.Icon>
        </SelectPrimitive.Trigger>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={4}
          className="z-50 w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-line bg-surface p-1 shadow-lg"
        >
          <SelectPrimitive.Viewport>
            {options.map((opt) => (
              <SelectPrimitive.Item
                key={opt.value}
                value={opt.value}
                className="relative flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-sm text-ink outline-none select-none data-[highlighted]:bg-subtle data-[state=checked]:font-medium data-[state=checked]:text-accent-ink"
              >
                <SelectPrimitive.ItemText>{opt.label}</SelectPrimitive.ItemText>
                <SelectPrimitive.ItemIndicator>
                  <Check className="h-4 w-4 text-accent" aria-hidden="true" />
                </SelectPrimitive.ItemIndicator>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Root>
      {error && (
        <p id={errorId} className="text-xs font-medium text-rose-700">
          {error}
        </p>
      )}
    </div>
  );
}
