// One ticket of the Kitchen Display System (KDS): dishes & quantities first, origin branch,
// time, reserved ingredients, red warning for a flagged ingredient, and 44px+ action buttons.

import { AlertTriangle, Check, Clock, Play, X } from "lucide-react";
import type { Ticket } from "../../api/kitchen";
import { ticketItems } from "../../api/kitchen";
import { clock, OrderId, TABULAR } from "../../components/common";
import { Alert, Badge, Button, Card, cn } from "../../ui";

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
    <Card
      as="article"
      data-ticket={ticket.order_id}
      className={cn(
        "flex h-full flex-col justify-between gap-3.5 p-4",
        queued ? "border-blue-200/90" : "border-amber-200/90",
      )}
    >
      <div className="space-y-3">
        {/* Top Meta */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <OrderId id={ticket.order_id} />
            <Badge tone="gray">Chi nhánh {ticket.origin_branch ?? "?"}</Badge>
          </div>
          {ticket.order_created_at && (
            <span
              className="inline-flex items-center gap-1 font-mono text-xs text-ink-muted"
              style={TABULAR}
            >
              <Clock className="h-3.5 w-3.5" aria-hidden="true" />
              đặt lúc {clock(ticket.order_created_at)}
            </span>
          )}
        </div>

        {/* Hero: Dishes */}
        <div className="space-y-1">
          {ticketItems(ticket).map((item) => (
            <p
              key={item.dish_id || item.name}
              className="text-lg font-bold leading-snug tracking-[-0.01em] text-ink"
              style={TABULAR}
            >
              {`${item.name} ×${item.quantity}`}
            </p>
          ))}
        </div>

        {/* Reserved Ingredients */}
        <div
          className="rounded-lg border border-line bg-subtle px-2.5 py-2 text-xs leading-relaxed text-ink-secondary"
          style={TABULAR}
        >
          <span className="font-semibold text-ink">Nguyên liệu đã giữ: </span>
          {ticket.reserved
            .map((r) => `${r.name ?? r.ingredient_id}${quantity(r.quantity, r.unit)}`)
            .join(", ")}
        </div>

        {/* Flagged Stock Warning */}
        {flagged.length > 0 && (
          <Alert
            tone="danger"
            role="alert"
            icon={<AlertTriangle className="h-4 w-4" />}
            className="px-3 py-2 text-xs"
          >
            {flagged.join(", ")} đang chờ kiểm kho. Kiểm tra trước khi nấu; nếu hỏng thật thì từ
            chối phiếu với lý do Nguyên liệu hỏng.
          </Alert>
        )}
      </div>

      {/* Pinned Footer Actions (min 44px high, 8px apart) */}
      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
        {queued ? (
          <>
            <Button
              size="kds"
              variant="primary"
              className="min-w-[136px] flex-1"
              onClick={() => onAction("start")}
              loading={busy === "start"}
              disabled={busy !== null && busy !== "start"}
            >
              <Play className="h-4 w-4" aria-hidden="true" />
              Bắt đầu nấu
            </Button>
            <Button
              size="kds"
              variant="danger-soft"
              className="flex-1"
              onClick={() => onAction("reject")}
              disabled={busy !== null}
            >
              <X className="h-4 w-4" aria-hidden="true" />
              Từ chối
            </Button>
          </>
        ) : (
          <Button
            size="kds"
            className="w-full flex-1 bg-emerald-600 text-white hover:bg-emerald-700"
            onClick={() => onAction("complete")}
            loading={busy === "complete"}
          >
            <Check className="h-4 w-4" aria-hidden="true" />
            Hoàn tất
          </Button>
        )}
      </div>
    </Card>
  );
}
