// Flow D at the branch (section 8 of the specification), from GET /monitor: orders waiting for
// Inventory too long (with Request cancellation), orders about to pass X, orders with the
// cancel flag, and status messages the branch could not read. Nothing here changes an order.

import { AlertTriangle, Clock, Hand, MailX } from "lucide-react";
import type { Monitor } from "../../api/branch";
import { clock, duration, OrderId, StatusBadge, TABULAR } from "../../components/common";
import { ALERT_KIND, CANCEL_FLAG } from "../../labels";
import { Alert, Button } from "../../ui";

export function BranchAlerts({
  monitor,
  onCancel,
}: {
  monitor: Monitor;
  onCancel: (orderId: string) => void;
}) {
  const now = Date.now();
  const alerts = monitor.message_alerts;
  const hasAny =
    monitor.awaiting_inventory.length > 0 ||
    monitor.about_to_expire.length > 0 ||
    monitor.cancel_requested.length > 0 ||
    alerts.count > 0;

  if (!hasAny) return null;

  return (
    <div className="space-y-2.5">
      {monitor.awaiting_inventory.length > 0 && (
        <Alert
          tone="warning"
          icon={<Clock className="h-4 w-4" />}
          title="Đơn chờ Kho quá lâu"
          role="alert"
          aria-label="Đơn chờ Kho quá lâu"
        >
          <ul className="mt-1 space-y-1.5">
            {monitor.awaiting_inventory.map((order) => (
              <li key={order.order_id} className="flex flex-wrap items-center gap-2">
                <OrderId id={order.order_id} />
                <span className="text-xs text-amber-900" style={TABULAR}>
                  đã chờ {duration(order.waited_s)}
                </span>
                {order.cancel_flag in CANCEL_FLAG ? (
                  <StatusBadge code={order.cancel_flag} table={CANCEL_FLAG} variant="outline" />
                ) : (
                  <Button size="xs" variant="danger-soft" onClick={() => onCancel(order.order_id)}>
                    Yêu cầu hủy
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {monitor.about_to_expire.length > 0 && (
        <Alert
          tone="orange"
          icon={<AlertTriangle className="h-4 w-4" />}
          title="Đơn sắp quá hạn"
          role="alert"
          aria-label="Đơn sắp quá hạn"
        >
          <p className="mb-1.5 text-xs text-orange-900">
            Các đơn này chưa gửi được; Kho sẽ trả Thất bại cho đơn đã quá hạn khi nhận được.
          </p>
          <ul className="space-y-1">
            {monitor.about_to_expire.map((order) => (
              <li key={order.order_id} className="flex flex-wrap items-center gap-2">
                <OrderId id={order.order_id} />
                <span className="text-xs text-orange-900" style={TABULAR}>
                  {new Date(order.expires_at).getTime() < now ? "đã quá hạn lúc" : "hết hạn lúc"}{" "}
                  {clock(order.expires_at)}
                </span>
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {monitor.cancel_requested.length > 0 && (
        <Alert
          tone="orange"
          icon={<Hand className="h-4 w-4" />}
          title="Đơn đang yêu cầu hủy"
          aria-label="Đơn đang yêu cầu hủy"
        >
          <ul className="mt-1 space-y-1.5">
            {monitor.cancel_requested.map((order) => (
              <li key={order.order_id} className="flex flex-wrap items-center gap-2">
                <OrderId id={order.order_id} />
                <StatusBadge code={order.cancel_flag} table={CANCEL_FLAG} variant="outline" />
                {order.waited_s !== null && (
                  <span className="text-xs text-orange-900" style={TABULAR}>
                    đã chờ {duration(order.waited_s)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      {alerts.count > 0 && (
        <Alert
          tone="danger"
          icon={<MailX className="h-4 w-4" />}
          title={`${alerts.count} tin trạng thái không đọc được hoặc không nhận ra`}
        >
          <ul className="mt-1 space-y-1">
            {alerts.latest.map((alert) => (
              <li
                key={`${alert.source_topic}-${alert.created_at}-${alert.event_id ?? ""}`}
                className="text-xs text-rose-900"
                style={TABULAR}
              >
                {clock(alert.created_at)} ·{" "}
                {ALERT_KIND[alert.kind as keyof typeof ALERT_KIND] ?? alert.kind} ·{" "}
                {alert.source_topic}
              </li>
            ))}
          </ul>
        </Alert>
      )}
    </div>
  );
}
