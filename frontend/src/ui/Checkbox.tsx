import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check } from "lucide-react";
import { useId } from "react";
import { cn } from "./cn";

export function Checkbox({
  label,
  checked,
  onCheckedChange,
  className,
}: {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  className?: string;
}) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex cursor-pointer items-center gap-2.5 rounded-lg border border-line bg-subtle/50 px-3 py-2 text-sm text-ink transition-colors hover:bg-subtle",
        checked && "border-accent/40 bg-accent-soft/50",
        className,
      )}
    >
      <CheckboxPrimitive.Root
        id={id}
        checked={checked}
        onCheckedChange={(state) => onCheckedChange(state === true)}
        className="flex h-4 w-4 shrink-0 items-center justify-center rounded border border-line-strong bg-surface transition-colors data-[state=checked]:border-accent data-[state=checked]:bg-accent data-[state=checked]:text-white"
      >
        <CheckboxPrimitive.Indicator>
          <Check className="h-3 w-3 stroke-[2.5]" aria-hidden="true" />
        </CheckboxPrimitive.Indicator>
      </CheckboxPrimitive.Root>
      <span className="select-none">{label}</span>
    </label>
  );
}
