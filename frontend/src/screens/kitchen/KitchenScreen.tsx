// The Kitchen Display screen: Queued and Cooking lanes with 44px+ buttons, reject dialog,
// and Flow D alerts. A 409 is the normal outcome of a cancel race (BR7) and reloads cleanly.

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, ChefHat, Clock, Flame } from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { ApiError, detailMessage } from "../../api/http";
import type { Alert as KitchenAlert, Ticket } from "../../api/kitchen";
import { kitchenApi } from "../../api/kitchen";
import { clock, ServiceBanner, TABULAR } from "../../components/common";
import { ALERT_KIND, KITCHEN_STATUS } from "../../labels";
import { Alert, Button, cn, EmptyState, Spinner, toast } from "../../ui";
import { RejectModal } from "./RejectModal";
import { type TicketAction, TicketCard } from "./TicketCard";

const PAGE = 20;

interface Request {
  orderId: string;
  action: TicketAction;
  reason?: string;
  spoiled?: string[];
}

export function KitchenScreen() {
  const client = useQueryClient();
  const [limit, setLimit] = useState(PAGE);
  const tickets = useQuery({
    queryKey: ["kitchen", "tickets", limit],
    queryFn: () => kitchenApi.tickets(limit),
    placeholderData: keepPreviousData,
  });
  const counts = useQuery({ queryKey: ["kitchen", "counts"], queryFn: kitchenApi.counts });
  const more = () => setLimit((l) => l + PAGE);
  const alerts = useQuery({ queryKey: ["kitchen", "alerts"], queryFn: kitchenApi.alerts });
  const [rejecting, setRejecting] = useState<Ticket | null>(null);
  const [refused, setRefused] = useState<string | null>(null);
  const announcement = useStatusAnnouncer(tickets.data);
  const reload = () => client.invalidateQueries({ queryKey: ["kitchen"] });

  const act = useMutation({
    mutationFn: (request: Request) => {
      if (request.action === "start") return kitchenApi.start(request.orderId);
      if (request.action === "complete") return kitchenApi.complete(request.orderId);
      return kitchenApi.reject(request.orderId, {
        reason_code: request.reason ?? "",
        spoiled_ingredients: request.spoiled ?? [],
      });
    },
    onSuccess: (_ticket, request) => {
      const short = request.orderId.slice(0, 8);
      const message = {
        start: `Phiếu ${short} đang nấu`,
        complete: `Phiếu ${short} đã hoàn tất`,
        reject: `Đã từ chối phiếu ${short}`,
      }[request.action];
      toast.show({ color: "green", message });
      setRejecting(null);
      setRefused(null);
      reload();
    },
    onError: (failure, request) => {
      if (failure instanceof ApiError && (failure.status === 409 || failure.status === 404)) {
        toast.show({ color: "yellow", message: "Phiếu vừa đổi trạng thái, đã tải lại" });
        setRejecting(null);
        reload();
      } else if (failure instanceof ApiError && failure.status === 400) {
        setRefused(detailMessage(failure.body) ?? "lý do hoặc nguyên liệu không hợp lệ");
      } else {
        toast.show({
          color: "red",
          title: "Không kết nối được tới Bếp",
          message: `Thao tác trên phiếu ${request.orderId.slice(0, 8)} chưa được ghi nhận; bấm lại để thử lại.`,
        });
      }
    },
  });

  const busyFor = (orderId: string): TicketAction | null =>
    act.isPending && act.variables?.orderId === orderId ? act.variables.action : null;

  const onAction = (ticket: Ticket, action: TicketAction) => {
    if (action === "reject") {
      setRefused(null);
      setRejecting(ticket);
    } else {
      act.mutate({ orderId: ticket.order_id, action });
    }
  };

  const queued = (tickets.data ?? []).filter((t) => t.status === "CHO_NAU");
  const cooking = (tickets.data ?? []).filter((t) => t.status === "DANG_NAU");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-ink">Bếp</h1>
      </div>

      {(tickets.isError || alerts.isError) && (
        <ServiceBanner
          service="Bếp"
          lastAnswer={Math.max(tickets.dataUpdatedAt, alerts.dataUpdatedAt)}
        />
      )}

      <KitchenAlerts alerts={alerts.data ?? []} />

      {tickets.isPending && !tickets.isError ? (
        <div className="flex justify-center py-12">
          <Spinner size="md" label="Đang tải phiếu" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Lane
            className="lg:col-span-8"
            cardsClass="grid-cols-1 xl:grid-cols-2"
            level={2}
            title="Chờ nấu"
            laneClass="border-blue-200/90 bg-blue-50/75"
            badgeClass="bg-blue-600 text-white"
            icon={<Clock className="h-4 w-4 text-blue-700" aria-hidden="true" />}
            total={counts.data?.CHO_NAU}
            onMore={more}
            empty="Chưa có phiếu nào đang chờ nấu. Đơn Kho đã giữ nguyên liệu sẽ hiện ở đây."
          >
            {queued.map((t) => (
              <TicketCard
                key={t.order_id}
                ticket={t}
                busy={busyFor(t.order_id)}
                onAction={(a) => onAction(t, a)}
              />
            ))}
          </Lane>

          <Lane
            className="lg:col-span-4"
            cardsClass="grid-cols-1"
            level={2}
            title="Đang nấu"
            laneClass="border-amber-200/90 bg-amber-50/80"
            badgeClass="bg-amber-500 text-slate-950"
            icon={<Flame className="h-4 w-4 text-amber-700" aria-hidden="true" />}
            total={counts.data?.DANG_NAU}
            onMore={more}
            empty="Chưa có phiếu nào đang nấu. Phiếu bấm Bắt đầu nấu sẽ chuyển sang đây."
          >
            {cooking.map((t) => (
              <TicketCard
                key={t.order_id}
                ticket={t}
                busy={busyFor(t.order_id)}
                onAction={(a) => onAction(t, a)}
              />
            ))}
          </Lane>
        </div>
      )}

      <RejectModal
        key={rejecting?.order_id ?? "none"}
        ticket={rejecting}
        pending={act.isPending && act.variables?.action === "reject"}
        refused={refused}
        onConfirm={(reason, spoiled) =>
          rejecting &&
          act.mutate({ orderId: rejecting.order_id, action: "reject", reason, spoiled })
        }
        onClose={() => setRejecting(null)}
      />
      <div role="status" aria-live="polite" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}

function Lane({
  className,
  cardsClass,
  level,
  title,
  laneClass,
  badgeClass,
  icon,
  total,
  onMore,
  empty,
  children,
}: {
  className?: string;
  cardsClass: string;
  level: 2 | 3;
  title: string;
  laneClass: string;
  badgeClass: string;
  icon: ReactNode;
  total: number | undefined;
  onMore: () => void;
  empty: string;
  children: ReactNode[];
}) {
  const count = Math.max(total ?? 0, children.length);
  const hidden = count - children.length;
  const Heading = level === 2 ? "h2" : "h3";

  return (
    <section
      aria-label={title}
      className={cn("flex flex-col gap-3 rounded-2xl border p-3.5", laneClass, className)}
    >
      <div className="flex items-center gap-2 px-1">
        {icon}
        <Heading className="flex items-center gap-2 text-sm font-semibold text-ink whitespace-nowrap">
          <span>{title}</span>{" "}
          <span
            className={cn(
              "inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 font-mono text-xs font-semibold tabular-nums",
              badgeClass,
            )}
          >
            <span className="sr-only">(</span>
            {count}
            <span className="sr-only">)</span>
          </span>
        </Heading>
      </div>

      {children.length ? (
        <div className={cn("grid items-stretch gap-3", cardsClass)}>{children}</div>
      ) : (
        <div className="rounded-xl border border-dashed border-line-strong bg-white/80">
          <EmptyState icon={ChefHat}>{empty}</EmptyState>
        </div>
      )}

      {hidden > 0 && (
        <Button variant="secondary" size="sm" onClick={onMore} className="w-full">
          Xem thêm (còn {hidden} phiếu)
        </Button>
      )}
    </section>
  );
}

function KitchenAlerts({ alerts }: { alerts: KitchenAlert[] }) {
  if (!alerts.length) return null;
  return (
    <section aria-label="Cảnh báo của Bếp">
      <Alert
        tone="orange"
        icon={<AlertCircle className="h-4 w-4" />}
        title={`Cảnh báo (${alerts.length})`}
      >
        <ul className="mt-1 space-y-1">
          {alerts.map((alert) => (
            <li key={alert.id} className="text-xs text-orange-950" style={TABULAR}>
              {clock(alert.created_at)} ·{" "}
              {ALERT_KIND[alert.kind as keyof typeof ALERT_KIND] ?? alert.kind}
              {alert.order_id ? ` · đơn ${alert.order_id.slice(0, 8)}` : ""} · {describe(alert)}
            </li>
          ))}
        </ul>
      </Alert>
    </section>
  );
}

function describe(alert: KitchenAlert): string {
  const detail = alert.detail as { origin_branch?: unknown; dismissed?: unknown; error?: unknown };
  if (alert.kind === "HUY_SAI_CHI_NHANH") {
    const dismissed = Array.isArray(detail.dismissed) ? detail.dismissed.join(", ") : "?";
    return `gốc ${String(detail.origin_branch ?? "?")}, bỏ qua ${dismissed}: kiểm tra cấu hình chi nhánh gửi`;
  }
  return `tin trên ${alert.source_topic} đã chuyển vào dlq`;
}

function useStatusAnnouncer(tickets: Ticket[] | undefined): string {
  const previous = useRef<Map<string, string> | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!tickets) return;
    const now = new Map(tickets.map((t) => [t.order_id, t.status]));
    const before = previous.current;
    previous.current = now;
    if (!before) return;
    const changes = tickets
      .filter((t) => before.has(t.order_id) && before.get(t.order_id) !== t.status)
      .map((t) => {
        const label = KITCHEN_STATUS[t.status as keyof typeof KITCHEN_STATUS]?.label ?? t.status;
        return `Phiếu ${t.order_id.slice(0, 8)} đã chuyển sang ${label}`;
      });
    if (changes.length) setMessage(changes.join(". "));
  }, [tickets]);
  return message;
}
