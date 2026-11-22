// Pieces every screen uses (.claude/skills/screen/references/design.md): status badges with an
// icon and a label, short order ids, the banner for a service that does not answer, times.

import { ActionIcon, Alert, Badge, CopyButton, Group, Text, Tooltip } from "@mantine/core";
import {
  IconAlertTriangle,
  IconBan,
  IconCheck,
  IconCircleCheck,
  IconClock,
  IconCopy,
  IconFlame,
  IconHandStop,
  IconPackage,
  IconPlugConnectedX,
  IconToolsKitchen2,
} from "@tabler/icons-react";
import type { ComponentType } from "react";
import type { StatusLabel } from "../labels";

const ICONS: Record<string, ComponentType<{ size?: number; "aria-hidden"?: boolean }>> = {
  CHO_KHO: IconClock,
  DA_GIU: IconPackage,
  DANG_GIU: IconPackage,
  CHO_NAU: IconToolsKitchen2,
  HUY_CHO_DON: IconHandStop,
  DANG_NAU: IconFlame,
  HOAN_TAT: IconCircleCheck,
  DA_DUNG: IconCircleCheck,
  DA_HUY: IconBan,
  DA_TRA: IconBan,
  THAT_BAI: IconAlertTriangle,
  CHO_KIEM_KHO: IconAlertTriangle,
  DANG_YEU_CAU: IconHandStop,
  BEP_KHONG_NAU: IconHandStop,
};

/** A status or flag as a badge: colour, icon and label, never colour alone. A code missing
 * from the table is shown as it is rather than hidden. */
export function StatusBadge({
  code,
  table,
  variant = "light",
  suffix,
}: {
  code: string;
  table: Record<string, StatusLabel>;
  variant?: "light" | "outline";
  suffix?: string;
}) {
  const entry = table[code];
  const Icon = ICONS[code];
  return (
    <Badge
      color={entry?.color ?? "gray"}
      variant={variant}
      leftSection={Icon ? <Icon size={12} aria-hidden /> : null}
      styles={{ label: { textTransform: "none" } }}
    >
      {entry?.label ?? code}
      {suffix ? ` · ${suffix}` : ""}
    </Badge>
  );
}

/** The first 8 characters of an order id; the full id in a tooltip and copyable. */
export function OrderId({ id }: { id: string }) {
  return (
    <Group gap={4} wrap="nowrap">
      <Tooltip label={id}>
        <Text ff="monospace" size="sm" span>
          {id.slice(0, 8)}
        </Text>
      </Tooltip>
      <CopyButton value={id}>
        {({ copied, copy }) => (
          <ActionIcon
            variant="subtle"
            size="md"
            color={copied ? "teal" : "gray"}
            onClick={copy}
            aria-label={copied ? "Đã chép mã đơn" : `Chép mã đơn ${id.slice(0, 8)}`}
          >
            {copied ? <IconCheck size={14} aria-hidden /> : <IconCopy size={14} aria-hidden />}
          </ActionIcon>
        )}
      </CopyButton>
    </Group>
  );
}

/** The banner of a service that does not answer; the screen keeps its last data. */
export function ServiceBanner({ service, lastAnswer }: { service: string; lastAnswer: number }) {
  return (
    <Alert
      color="red"
      icon={<IconPlugConnectedX aria-hidden />}
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
