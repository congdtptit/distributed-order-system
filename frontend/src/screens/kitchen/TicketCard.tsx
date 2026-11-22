// One ticket of the Kitchen screen: origin branch, time, dishes, reserved ingredients, the red
// warning for a flagged ingredient (Flow A step 6), and the buttons table 3.2 allows in its
// status. Buttons are at least 44px high with 8px between them (design.md, "Sizes").

import { Alert, Badge, Button, Card, Divider, Group, Stack, Text } from "@mantine/core";
import {
  IconAlertTriangle,
  IconCheck,
  IconClock,
  IconPlayerPlay,
  IconX,
} from "@tabler/icons-react";
import type { Ticket } from "../../api/kitchen";
import { ticketItems } from "../../api/kitchen";
import { clock, OrderId, StatusBadge, TABULAR } from "../../components/common";
import { KITCHEN_STATUS } from "../../labels";

export type TicketAction = "start" | "reject" | "complete";

function quantity(value: number | null | undefined, unit: string | null | undefined): string {
  if (value === null || value === undefined) return "";
  return ` ${value.toLocaleString("vi-VN")}${unit ? ` ${unit}` : ""}`;
}

/** design.md, "Sizes": Kitchen buttons at least 44px high, 8px apart. */
const KITCHEN_BUTTON = { h: 44, size: "md", style: { flex: 1 } } as const;

export function TicketCard({
  ticket,
  busy,
  onAction,
}: {
  ticket: Ticket;
  /** The action whose request is in flight, if any: its button shows a loader. */
  busy: TicketAction | null;
  onAction: (action: TicketAction) => void;
}) {
  const names = new Map(ticket.reserved.map((r) => [r.ingredient_id, r.name ?? r.ingredient_id]));
  const flagged = ticket.warnings.map((id) => names.get(id) ?? id);
  const queued = ticket.status === "CHO_NAU";

  return (
    <Card
      padding="md"
      data-ticket={ticket.order_id}
      style={{
        borderLeft: `4px solid var(--mantine-color-${queued ? "indigo" : "yellow"}-5)`,
      }}
    >
      <Stack gap="sm">
        <Group justify="space-between" wrap="nowrap">
          <OrderId id={ticket.order_id} />
          <StatusBadge code={ticket.status} table={KITCHEN_STATUS} />
        </Group>
        <Group gap={6} wrap="wrap">
          <Badge color="gray" variant="outline">
            Chi nhánh {ticket.origin_branch ?? "?"}
          </Badge>
          {ticket.order_created_at && (
            <Group gap={4} c="dimmed">
              <IconClock size={14} aria-hidden />
              <Text size="sm" c="dimmed" style={TABULAR}>
                đặt lúc {clock(ticket.order_created_at)}
              </Text>
            </Group>
          )}
        </Group>
        <Stack gap={2}>
          {ticketItems(ticket).map((item) => (
            <Text key={item.dish_id || item.name} fw={650} size="lg" lh={1.35}>
              {`${item.name} ×${item.quantity}`}
            </Text>
          ))}
        </Stack>
        <Text size="xs" c="dimmed" style={TABULAR}>
          Nguyên liệu đã giữ:{" "}
          {ticket.reserved
            .map((r) => `${r.name ?? r.ingredient_id}${quantity(r.quantity, r.unit)}`)
            .join(", ")}
        </Text>
        {flagged.length > 0 && (
          <Alert
            color="red"
            variant="light"
            icon={<IconAlertTriangle aria-hidden />}
            role="alert"
            p="xs"
            styles={{ root: { borderLeft: "3px solid var(--mantine-color-red-6)" } }}
          >
            <Text size="sm" c="red.9">
              {flagged.join(", ")} đang chờ kiểm kho. Kiểm tra trước khi nấu; nếu hỏng thật thì từ
              chối phiếu với lý do Nguyên liệu hỏng.
            </Text>
          </Alert>
        )}
        <Divider color="gray.2" />
        <Group gap="xs" wrap="nowrap">
          {queued ? (
            <>
              <Button
                {...KITCHEN_BUTTON}
                leftSection={<IconPlayerPlay size={18} aria-hidden />}
                onClick={() => onAction("start")}
                loading={busy === "start"}
                disabled={busy !== null && busy !== "start"}
              >
                Bắt đầu nấu
              </Button>
              <Button
                {...KITCHEN_BUTTON}
                style={{ flex: "0 0 auto" }}
                color="red"
                variant="outline"
                leftSection={<IconX size={18} aria-hidden />}
                onClick={() => onAction("reject")}
                disabled={busy !== null}
              >
                Từ chối
              </Button>
            </>
          ) : (
            <Button
              {...KITCHEN_BUTTON}
              color="green"
              leftSection={<IconCheck size={18} aria-hidden />}
              onClick={() => onAction("complete")}
              loading={busy === "complete"}
            >
              Hoàn tất
            </Button>
          )}
        </Group>
      </Stack>
    </Card>
  );
}
