// One ticket of the Kitchen screen: origin branch, time, dishes, reserved ingredients, the red
// warning for a flagged ingredient (Flow A step 6), and the buttons table 3.2 allows in its
// status. Buttons are at least 44px high with 8px between them (design.md, "Sizes").

import { Alert, Button, Card, Group, Stack, Text } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import type { Ticket } from "../../api/kitchen";
import { ticketItems } from "../../api/kitchen";
import { clock, OrderId, StatusBadge, TABULAR } from "../../components/common";
import { KITCHEN_STATUS } from "../../labels";

export type TicketAction = "start" | "reject" | "complete";

function quantity(value: number | null | undefined, unit: string | null | undefined): string {
  if (value === null || value === undefined) return "";
  return ` ${value.toLocaleString("vi-VN")}${unit ? ` ${unit}` : ""}`;
}

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
    <Card withBorder padding="md" data-ticket={ticket.order_id}>
      <Stack gap="xs">
        <Group justify="space-between" wrap="nowrap">
          <OrderId id={ticket.order_id} />
          <StatusBadge code={ticket.status} table={KITCHEN_STATUS} />
        </Group>
        <Text size="sm" c="dimmed" style={TABULAR}>
          Chi nhánh {ticket.origin_branch ?? "?"}
          {ticket.order_created_at ? ` · đặt lúc ${clock(ticket.order_created_at)}` : ""}
        </Text>
        <Text fw={600}>
          {ticketItems(ticket)
            .map((item) => `${item.name} ×${item.quantity}`)
            .join(", ")}
        </Text>
        <Text size="sm" style={TABULAR}>
          Nguyên liệu đã giữ:{" "}
          {ticket.reserved
            .map((r) => `${r.name ?? r.ingredient_id}${quantity(r.quantity, r.unit)}`)
            .join(", ")}
        </Text>
        {flagged.length > 0 && (
          <Alert
            color="red"
            variant="filled"
            icon={<IconAlertTriangle aria-hidden />}
            role="alert"
            p="xs"
          >
            {flagged.join(", ")} đang chờ kiểm kho. Kiểm tra trước khi nấu; nếu hỏng thật thì từ
            chối phiếu với lý do Nguyên liệu hỏng.
          </Alert>
        )}
        <Group gap="xs" mt={4}>
          {queued ? (
            <>
              <Button
                size="lg"
                onClick={() => onAction("start")}
                loading={busy === "start"}
                disabled={busy !== null && busy !== "start"}
              >
                Bắt đầu nấu
              </Button>
              <Button
                size="lg"
                color="red"
                variant="light"
                onClick={() => onAction("reject")}
                disabled={busy !== null}
              >
                Từ chối
              </Button>
            </>
          ) : (
            <Button
              size="lg"
              color="green"
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
