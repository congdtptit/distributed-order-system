// The branch's orders as the service returns them (GET /orders, newest first): status, cancel
// flag, the Kitchen's notice, the send states of BR5, and the Cancel button where section 6 of
// the specification allows it.

import { Button, Group, Stack, Table, Text } from "@mantine/core";
import { IconReceipt, IconX } from "@tabler/icons-react";
import type { Order } from "../../api/branch";
import { clock, duration, OrderId, StatusBadge, TABULAR } from "../../components/common";
import { Empty } from "../../components/layout";
import {
  CANCEL_FLAG,
  CANCEL_MESSAGE,
  CANCEL_SEND_STATE,
  ORDER_STATUS,
  reasonLabel,
  SEND_STATE,
} from "../../labels";

/** Rank 2 of section 3.1: the Cancel button is hidden (section 6, branch side, step 1). */
const TERMINAL = new Set(["HOAN_TAT", "DA_HUY", "THAT_BAI"]);

function lookup(table: Record<string, string>, code: string | null): string | null {
  return code === null ? null : (table[code] ?? code);
}

export function OrdersTable({
  orders,
  onCancel,
}: {
  orders: Order[];
  onCancel: (orderId: string) => void;
}) {
  if (!orders.length) {
    return (
      <Empty icon={IconReceipt}>
        Chưa có đơn nào. Đơn tạo ở chi nhánh này sẽ hiện ở đây, kèm trạng thái Kho và Bếp trả về.
      </Empty>
    );
  }
  return (
    <Table.ScrollContainer minWidth={760}>
      <Table highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Đơn</Table.Th>
            <Table.Th>Giờ tạo</Table.Th>
            <Table.Th>Món</Table.Th>
            <Table.Th>Trạng thái</Table.Th>
            <Table.Th>Gửi đi</Table.Th>
            <Table.Th ta="right">Thao tác</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {orders.map((order) => (
            <OrderRow key={order.order_id} order={order} onCancel={onCancel} />
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function OrderRow({ order, onCancel }: { order: Order; onCancel: (orderId: string) => void }) {
  const flag = order.cancel_flag in CANCEL_FLAG ? order.cancel_flag : null;
  const waited =
    flag === "DANG_YEU_CAU" && order.cancel_requested_at
      ? duration((Date.now() - new Date(order.cancel_requested_at).getTime()) / 1000)
      : undefined;
  const reason = reasonLabel(order.close_reason);
  const notice = lookup(CANCEL_MESSAGE, order.cancel_message);
  const sendState = lookup(SEND_STATE, order.send_state);
  const cancelState = flag ? lookup(CANCEL_SEND_STATE, order.cancel_send_state) : null;
  const canCancel = !TERMINAL.has(order.status) && order.cancel_flag === "KHONG";

  return (
    <Table.Tr>
      <Table.Td>
        <OrderId id={order.order_id} />
      </Table.Td>
      <Table.Td style={TABULAR}>
        <Text size="sm" c="dimmed">
          {clock(order.created_at)}
        </Text>
      </Table.Td>
      <Table.Td>
        <Text size="sm" fw={500}>
          {order.items.map((item) => `${item.name} ×${item.quantity}`).join(", ")}
        </Text>
      </Table.Td>
      <Table.Td>
        <Stack gap={4} align="flex-start">
          <Group gap={4}>
            <StatusBadge code={order.status} table={ORDER_STATUS} />
            {flag && (
              <StatusBadge
                code={flag}
                table={CANCEL_FLAG}
                variant="outline"
                {...(waited ? { suffix: waited } : {})}
              />
            )}
          </Group>
          {reason && (
            <Text size="xs" c="dimmed">
              {reason}
            </Text>
          )}
          {notice && (
            <Text size="xs" c="red.8">
              {notice}
            </Text>
          )}
        </Stack>
      </Table.Td>
      <Table.Td>
        <Stack gap={2}>
          {sendState && (
            <Text size="xs" c="dimmed">
              {sendState}
            </Text>
          )}
          {cancelState && (
            <Text size="xs" c="orange.9">
              {cancelState}
            </Text>
          )}
        </Stack>
      </Table.Td>
      <Table.Td ta="right">
        {canCancel && (
          <Button
            size="xs"
            variant="light"
            color="red"
            leftSection={<IconX size={14} aria-hidden />}
            onClick={() => onCancel(order.order_id)}
          >
            Hủy đơn
          </Button>
        )}
      </Table.Td>
    </Table.Tr>
  );
}
