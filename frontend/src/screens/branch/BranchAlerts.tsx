// Flow D at the branch (section 8 of the specification), from GET /monitor: orders waiting for
// Inventory too long (with Request cancellation), orders about to pass X, orders with the
// cancel flag, and status messages the branch could not read. Nothing here changes an order.

import { Alert, Button, Group, List, Stack, Text } from "@mantine/core";
import {
  IconAlertTriangle,
  IconClockExclamation,
  IconHandStop,
  IconMailX,
} from "@tabler/icons-react";
import type { Monitor } from "../../api/branch";
import { clock, duration, OrderId, StatusBadge, TABULAR } from "../../components/common";
import { ALERT_KIND, CANCEL_FLAG } from "../../labels";

export function BranchAlerts({
  monitor,
  onCancel,
}: {
  monitor: Monitor;
  onCancel: (orderId: string) => void;
}) {
  const now = Date.now();
  const alerts = monitor.message_alerts;
  return (
    <Stack gap="sm">
      {monitor.awaiting_inventory.length > 0 && (
        <Alert
          color="yellow"
          icon={<IconClockExclamation aria-hidden />}
          title="Đơn chờ Kho quá lâu"
          role="alert"
          aria-label="Đơn chờ Kho quá lâu"
        >
          <List spacing={4} size="sm">
            {monitor.awaiting_inventory.map((order) => (
              <List.Item key={order.order_id}>
                <Group gap="xs">
                  <OrderId id={order.order_id} />
                  <Text size="sm" style={TABULAR}>
                    đã chờ {duration(order.waited_s)}
                  </Text>
                  {order.cancel_flag in CANCEL_FLAG ? (
                    <StatusBadge code={order.cancel_flag} table={CANCEL_FLAG} variant="outline" />
                  ) : (
                    <Button
                      size="xs"
                      color="red"
                      variant="light"
                      onClick={() => onCancel(order.order_id)}
                    >
                      Yêu cầu hủy
                    </Button>
                  )}
                </Group>
              </List.Item>
            ))}
          </List>
        </Alert>
      )}
      {monitor.about_to_expire.length > 0 && (
        <Alert
          color="orange"
          icon={<IconAlertTriangle aria-hidden />}
          title="Đơn sắp quá hạn"
          role="alert"
          aria-label="Đơn sắp quá hạn"
        >
          <Text size="sm" mb={4}>
            Các đơn này chưa gửi được; Kho sẽ trả Thất bại cho đơn đã quá hạn khi nhận được.
          </Text>
          <List spacing={4} size="sm">
            {monitor.about_to_expire.map((order) => (
              <List.Item key={order.order_id}>
                <Group gap="xs">
                  <OrderId id={order.order_id} />
                  <Text size="sm" style={TABULAR}>
                    {new Date(order.expires_at).getTime() < now ? "đã quá hạn lúc" : "hết hạn lúc"}{" "}
                    {clock(order.expires_at)}
                  </Text>
                </Group>
              </List.Item>
            ))}
          </List>
        </Alert>
      )}
      {monitor.cancel_requested.length > 0 && (
        <Alert
          color="orange"
          variant="outline"
          icon={<IconHandStop aria-hidden />}
          title="Đơn đang yêu cầu hủy"
          aria-label="Đơn đang yêu cầu hủy"
        >
          <List spacing={4} size="sm">
            {monitor.cancel_requested.map((order) => (
              <List.Item key={order.order_id}>
                <Group gap="xs">
                  <OrderId id={order.order_id} />
                  <StatusBadge code={order.cancel_flag} table={CANCEL_FLAG} variant="outline" />
                  {order.waited_s !== null && (
                    <Text size="sm" style={TABULAR}>
                      đã chờ {duration(order.waited_s)}
                    </Text>
                  )}
                </Group>
              </List.Item>
            ))}
          </List>
        </Alert>
      )}
      {alerts.count > 0 && (
        <Alert
          color="red"
          icon={<IconMailX aria-hidden />}
          title={`${alerts.count} tin trạng thái không đọc được hoặc không nhận ra`}
        >
          <List spacing={4} size="sm">
            {alerts.latest.map((alert) => (
              <List.Item key={`${alert.source_topic}-${alert.created_at}-${alert.event_id ?? ""}`}>
                <Text size="sm" style={TABULAR}>
                  {clock(alert.created_at)} ·{" "}
                  {ALERT_KIND[alert.kind as keyof typeof ALERT_KIND] ?? alert.kind}
                  {alert.order_id ? ` · đơn ${alert.order_id.slice(0, 8)}` : ""}
                </Text>
              </List.Item>
            ))}
          </List>
        </Alert>
      )}
    </Stack>
  );
}
