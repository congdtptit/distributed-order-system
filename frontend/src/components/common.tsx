// Shared domain display primitives: status badges (icon + label), short order ids,
// unreachable-service banners, and Vietnamese time/duration formatters.

import {
  AlertTriangle,
  Ban,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Flame,
  Hand,
  Package,
  PlugZap,
  Utensils,
} from "lucide-react";
import { type ComponentType, useState } from "react";
import type { StatusLabel } from "../labels";
import { Alert, Badge, Tooltip } from "../ui";

const ICONS: Record<string, ComponentType<{ className?: string; "aria-hidden"?: boolean }>> = {
  CHO_KHO: Clock,
  DA_GIU: Package,
  DANG_GIU: Package,
  CHO_NAU: Utensils,
  HUY_CHO_DON: Hand,
  DANG_NAU: Flame,
  HOAN_TAT: CheckCircle2,
  DA_DUNG: CheckCircle2,
  DA_HUY: Ban,
  DA_TRA: Ban,
  THAT_BAI: AlertTriangle,
  CHO_KIEM_KHO: AlertTriangle,
  DANG_YEU_CAU: Hand,
  BEP_KHONG_NAU: Hand,
};

/** A status or flag as a badge: colour, icon and label, never colour alone. */
export function StatusBadge({
  code,
  table,
  variant = "soft",
  suffix,
}: {
  code: string;
  table: Record<string, StatusLabel>;
  variant?: "soft" | "outline";
  suffix?: string;
}) {
  const entry = table[code];
  const Icon = ICONS[code];
  return (
    <Badge
      tone={entry?.color ?? "gray"}
      variant={variant}
      icon={Icon ? <Icon className="h-3 w-3" aria-hidden /> : undefined}
    >
      {entry?.label ?? code}
      {suffix ? ` · ${suffix}` : ""}
    </Badge>
  );
}

/** The first 8 characters of an order id; full id in tooltip and copyable. */
export function OrderId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    void navigator.clipboard?.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <Tooltip label={id}>
        <span className="font-mono text-xs font-medium text-ink">{id.slice(0, 8)}</span>
      </Tooltip>
      <button
        type="button"
        onClick={copy}
        aria-label={copied ? "Đã chép mã đơn" : `Chép mã đơn ${id.slice(0, 8)}`}
        className="inline-flex h-6 w-6 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-subtle hover:text-ink"
      >
        {copied ? (
          <Check className="h-3 w-3 text-blue-600" aria-hidden="true" />
        ) : (
          <Copy className="h-3 w-3" aria-hidden="true" />
        )}
      </button>
    </span>
  );
}

/** The banner of a service that does not answer; the screen keeps its last data. */
export function ServiceBanner({ service, lastAnswer }: { service: string; lastAnswer: number }) {
  return (
    <Alert
      tone="danger"
      role="alert"
      icon={<PlugZap className="h-4 w-4" aria-hidden="true" />}
      title={`Không kết nối được tới ${service}`}
    >
      {lastAnswer
        ? `Lần trả lời cuối lúc ${clock(new Date(lastAnswer))}. Dữ liệu dưới đây có thể đã cũ.`
        : "Chưa nhận được dữ liệu nào."}
    </Alert>
  );
}

/** HH:mm:ss in the local time zone. */
export function clock(at: Date | string): string {
  const d = typeof at === "string" ? new Date(at) : at;
  return d.toLocaleTimeString("vi-VN", { hour12: false });
}

/** "45 giây", "3 phút", "2 giờ 5 phút". */
export function duration(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  if (s < 60) return `${s} giây`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes} phút`;
  const rest = minutes % 60;
  return rest ? `${Math.floor(minutes / 60)} giờ ${rest} phút` : `${minutes / 60} giờ`;
}

export const TABULAR = { fontVariantNumeric: "tabular-nums" } as const;
