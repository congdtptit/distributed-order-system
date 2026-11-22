import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "./cn";
import { Spinner } from "./Spinner";

export type ButtonVariant = "primary" | "accent" | "secondary" | "ghost" | "danger" | "danger-soft";
export type ButtonSize = "xs" | "sm" | "md" | "lg" | "kds";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    "bg-primary text-primary-ink hover:bg-primary-hover shadow-xs disabled:bg-slate-200 disabled:text-slate-500 disabled:shadow-none",
  accent:
    "bg-accent text-white hover:bg-accent-hover shadow-xs disabled:bg-slate-200 disabled:text-slate-500 disabled:shadow-none",
  secondary:
    "bg-surface text-ink border border-line-strong hover:bg-subtle shadow-2xs disabled:text-ink-muted disabled:bg-subtle",
  ghost:
    "bg-transparent text-ink-secondary hover:bg-muted/80 hover:text-ink disabled:text-ink-muted",
  danger:
    "bg-rose-600 text-white hover:bg-rose-700 shadow-xs disabled:bg-rose-200 disabled:text-rose-500 disabled:shadow-none",
  "danger-soft":
    "bg-rose-100 text-rose-800 border border-rose-300 hover:bg-rose-200/85 disabled:opacity-50",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  xs: "h-7 px-2.5 text-xs gap-1.5 rounded-md",
  sm: "h-8 px-3 text-xs gap-1.5 rounded-lg",
  md: "h-9 px-3.5 text-sm gap-2 rounded-lg",
  lg: "h-10 px-4 text-sm gap-2 rounded-lg",
  kds: "min-h-[44px] px-4 text-sm gap-2 rounded-lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      loading = false,
      disabled,
      type = "button",
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        className={cn(
          "inline-flex cursor-pointer items-center justify-center whitespace-nowrap font-semibold transition-colors duration-150 disabled:cursor-not-allowed",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
        {...props}
      >
        {loading && <Spinner size="xs" label="Đang xử lý" className="text-current" />}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
