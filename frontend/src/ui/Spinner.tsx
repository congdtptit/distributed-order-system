import { Loader2 } from "lucide-react";
import { cn } from "./cn";

export function Spinner({
  size = "md",
  label = "Đang tải",
  className,
}: {
  size?: "xs" | "sm" | "md" | "lg";
  label?: string;
  className?: string;
}) {
  const sizes = {
    xs: "h-3.5 w-3.5",
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  }[size];

  return (
    <span
      role="status"
      aria-label={label}
      className={cn("inline-flex items-center justify-center", className)}
    >
      <Loader2 className={cn("animate-spin text-ink-muted", sizes)} aria-hidden="true" />
    </span>
  );
}
