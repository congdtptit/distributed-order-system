// The branch's orders as the service returns them (GET /orders, newest first): status, cancel
// flag, the Kitchen's notice, the send states of BR5, and the Cancel button where section 6 allows.

import { Receipt, X } from "lucide-react";
import type { Order } from "../../api/branch";
import { clock, duration, OrderId, StatusBadge, TABULAR } from "../../components/common";
import {
  CANCEL_FLAG,
  CANCEL_MESSAGE,
  CANCEL_SEND_STATE,
  ORDER_STATUS,
  reasonLabel,
  SEND_STATE,
} from "../../labels";
import {
  Button,
  cn,
  EmptyState,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../ui";

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
      <EmptyState icon={Receipt}>
        Chưa có đơn nào. Đơn tạo ở chi nhánh này sẽ hiện ở đây, kèm trạng thái Kho và Bếp trả về.
      </EmptyState>
    );
  }
  return (
    <TableContainer>
      <Table className="min-w-[740px]">
        <TableHead>
          <TableRow className="hover:bg-transparent">
            <TableHeaderCell>Đơn</TableHeaderCell>
            <TableHeaderCell>Giờ tạo</TableHeaderCell>
            <TableHeaderCell>Món</TableHeaderCell>
            <TableHeaderCell>Trạng thái</TableHeaderCell>
            <TableHeaderCell>Gửi đi</TableHeaderCell>
            <TableHeaderCell className="text-right">Thao tác</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {orders.map((order) => (
            <OrderRow key={order.order_id} order={order} onCancel={onCancel} />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
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

  const sendDot =
    order.send_state === "DA_GUI"
      ? "bg-emerald-500"
      : order.send_state === "DANG_GUI"
        ? "bg-amber-500"
        : "bg-slate-400";

  return (
    <TableRow>
      <TableCell>
        <OrderId id={order.order_id} />
      </TableCell>
      <TableCell style={TABULAR}>
        <span className="font-mono text-xs text-ink-secondary">{clock(order.created_at)}</span>
      </TableCell>
      <TableCell>
        <span className="text-sm font-medium text-ink">
          {order.items.map((item) => `${item.name} ×${item.quantity}`).join(", ")}
        </span>
      </TableCell>
      <TableCell>
        <div className="flex flex-col items-start gap-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <StatusBadge code={order.status} table={ORDER_STATUS} />
            {flag && (
              <StatusBadge
                code={flag}
                table={CANCEL_FLAG}
                variant="outline"
                {...(waited ? { suffix: waited } : {})}
              />
            )}
          </div>
          {reason && <span className="text-xs text-ink-secondary">{reason}</span>}
          {notice && <span className="text-xs font-medium text-rose-700">{notice}</span>}
        </div>
      </TableCell>
      <TableCell>
        <div className="space-y-0.5">
          {sendState && (
            <span className="inline-flex items-center gap-1.5 text-xs text-ink-secondary">
              <span
                className={cn("h-1.5 w-1.5 shrink-0 rounded-full", sendDot)}
                aria-hidden="true"
              />
              <span>{sendState}</span>
            </span>
          )}
          {cancelState && <p className="text-xs font-medium text-orange-800">{cancelState}</p>}
        </div>
      </TableCell>
      <TableCell className="text-right">
        {canCancel && (
          <Button size="xs" variant="danger-soft" onClick={() => onCancel(order.order_id)}>
            <X className="h-3 w-3" aria-hidden="true" />
            Hủy đơn
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
