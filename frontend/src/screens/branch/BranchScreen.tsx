// The branch screen (POS counter and Online ordering): place orders, follow their statuses,
// cancel, and see Flow D. Specified in .claude/skills/screen/references/screens.md ("branch").
// It shows what the Branch service returns and decides nothing itself.

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { HelpCircle, Plug, PlugZap } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import type { BranchId, Monitor, Order } from "../../api/branch";
import { BRANCHES, branchApi, isBranch } from "../../api/branch";
import { ServiceBanner, TABULAR } from "../../components/common";
import { ORDER_STATUS } from "../../labels";
import { Badge, Button, Panel, SegmentedRadio, Spinner } from "../../ui";
import { BranchAlerts } from "./BranchAlerts";
import { CancelModal } from "./CancelModal";
import { OrderForm } from "./OrderForm";
import { OrdersTable } from "./OrdersTable";

/** Orders shown before "Xem thêm"; the branch lists at most 200 (GET /orders). */
const PAGE = 20;
const MAX_ORDERS = 200;

export function BranchScreen() {
  const { branchId } = useParams();
  if (!isBranch(branchId)) {
    return <p className="text-sm text-ink-secondary">Không có chi nhánh {branchId}.</p>;
  }
  return <BranchPanel key={branchId} branch={branchId} />;
}

function BranchPanel({ branch }: { branch: BranchId }) {
  const api = branchApi(branch);
  const navigate = useNavigate();
  const [limit, setLimit] = useState(PAGE);
  const orders = useQuery({
    queryKey: ["branch", branch, "orders", limit],
    queryFn: () => api.orders(limit),
    placeholderData: keepPreviousData,
  });
  const monitor = useQuery({ queryKey: ["branch", branch, "monitor"], queryFn: api.monitor });
  const [cancelling, setCancelling] = useState<string | null>(null);
  const announcement = useStatusAnnouncer(orders.data);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-ink">Chi nhánh {branch}</h1>
        <div className="flex flex-wrap items-center gap-2">
          <Connection monitor={monitor.data} answering={!monitor.isError} />
          <SegmentedRadio
            aria-label="Chọn chi nhánh"
            options={BRANCHES.map((b) => ({ value: b, label: b }))}
            value={branch}
            onChange={(value) => navigate(`/branch/${value}`)}
          />
        </div>
      </div>

      {(orders.isError || monitor.isError) && (
        <ServiceBanner
          service={`chi nhánh ${branch}`}
          lastAnswer={Math.max(orders.dataUpdatedAt, monitor.dataUpdatedAt)}
        />
      )}

      {monitor.data && <BranchAlerts monitor={monitor.data} onCancel={setCancelling} />}

      <OrderForm branch={branch} offline={monitor.data?.connection.connected === false} />

      <Panel title="Đơn của chi nhánh" level={2} count={orders.data?.length} flush>
        {orders.isPending && !orders.isError ? (
          <div className="flex justify-center py-10">
            <Spinner size="md" label="Đang tải đơn" />
          </div>
        ) : (
          <>
            <OrdersTable orders={orders.data ?? []} onCancel={setCancelling} />
            {(orders.data?.length ?? 0) >= limit && limit < MAX_ORDERS && (
              <div className="flex justify-center border-t border-line p-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setLimit((l) => Math.min(l + PAGE, MAX_ORDERS))}
                >
                  Xem thêm {PAGE} đơn cũ hơn
                </Button>
              </div>
            )}
          </>
        )}
      </Panel>

      <CancelModal branch={branch} orderId={cancelling} onClose={() => setCancelling(null)} />
      <div role="status" aria-live="polite" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}

/** Connection to Kafka and the entries waiting to be sent, from GET /monitor (section 8). */
function Connection({ monitor, answering }: { monitor: Monitor | undefined; answering: boolean }) {
  const connected = answering ? monitor?.connection.connected : undefined;
  const badge =
    connected === true
      ? { tone: "green" as const, label: "Đã kết nối Kafka", Icon: Plug }
      : connected === false
        ? { tone: "red" as const, label: "Mất kết nối Kafka", Icon: PlugZap }
        : { tone: "gray" as const, label: "Chưa rõ kết nối Kafka", Icon: HelpCircle };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge tone={badge.tone} icon={<badge.Icon className="h-3.5 w-3.5" aria-hidden="true" />}>
        {badge.label}
      </Badge>
      {monitor && (
        <Badge tone={monitor.waiting_to_send > 0 ? "orange" : "gray"}>
          <span style={TABULAR}>{monitor.waiting_to_send} mục chờ gửi</span>
        </Badge>
      )}
    </div>
  );
}

/** One polite announcement per status change between two reads. */
function useStatusAnnouncer(orders: Order[] | undefined): string {
  const previous = useRef<Map<string, string> | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!orders) return;
    const now = new Map(orders.map((o) => [o.order_id, o.status]));
    const before = previous.current;
    previous.current = now;
    if (!before) return;
    const changes = orders
      .filter((o) => before.has(o.order_id) && before.get(o.order_id) !== o.status)
      .map((o) => {
        const label = ORDER_STATUS[o.status as keyof typeof ORDER_STATUS]?.label ?? o.status;
        return `Đơn ${o.order_id.slice(0, 8)} đã chuyển sang ${label}`;
      });
    if (changes.length) setMessage(changes.join(". "));
  }, [orders]);
  return message;
}
