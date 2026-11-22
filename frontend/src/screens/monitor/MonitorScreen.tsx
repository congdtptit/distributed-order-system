// The Monitor screen (the operator): Flow D of every service in one place (section 8).
// Read-only: zero <button> elements inside <main>.

import { type UseQueryResult, useQueries, useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bell, CheckCircle2, Clock, PlugZap } from "lucide-react";
import { type ReactNode, useState } from "react";
import type { Monitor as BranchMonitor } from "../../api/branch";
import { BRANCHES, branchApi } from "../../api/branch";
import { inventoryApi } from "../../api/inventory";
import type { ConsumerMonitor } from "../../api/kitchen";
import { kitchenApi } from "../../api/kitchen";
import { clock, duration, TABULAR } from "../../components/common";
import { ALERT_KIND } from "../../labels";
import {
  Alert,
  Badge,
  cn,
  EmptyState,
  Panel,
  SegmentedRadio,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../ui";

interface AnyAlert {
  service: string;
  kind: string;
  order_id: string | null;
  source_topic: string;
  created_at: string;
}

export function MonitorScreen() {
  const branchQueries = useQueries({
    queries: BRANCHES.map((branch) => ({
      queryKey: ["branch", branch, "monitor"],
      queryFn: branchApi(branch).monitor,
    })),
  });
  const branches = BRANCHES.map((branch, i) => ({
    branch,
    query: branchQueries[i] as UseQueryResult<BranchMonitor>,
  }));
  const inventory = useQuery({ queryKey: ["inventory", "monitor"], queryFn: inventoryApi.monitor });
  const kitchen = useQuery({ queryKey: ["kitchen", "monitor"], queryFn: kitchenApi.monitor });
  const inventoryAlerts = useQuery({
    queryKey: ["inventory", "alerts"],
    queryFn: inventoryApi.alerts,
  });
  const kitchenAlerts = useQuery({ queryKey: ["kitchen", "alerts"], queryFn: kitchenApi.alerts });

  const alerts: AnyAlert[] = [
    ...(kitchenAlerts.data ?? []).map((a) => ({ ...a, service: "Bếp" })),
    ...(inventoryAlerts.data ?? []).map((a) => ({ ...a, service: "Kho" })),
    ...branches.flatMap(({ branch, query }) =>
      (query.data?.message_alerts.latest ?? []).map((a) => ({ ...a, service: branch })),
    ),
  ].sort((a, b) => b.created_at.localeCompare(a.created_at));

  const consumers = [
    { service: "Kho", query: inventory },
    { service: "Bếp", query: kitchen },
  ];
  const services = [...branches.map((b) => b.query), inventory, kitchen];
  const answeringCount = services.filter((q) => !q.isError).length;
  const offline = branches.filter((b) => b.query.data?.connection.connected === false).length;
  const waiting = branches.reduce((sum, b) => sum + (b.query.data?.waiting_to_send ?? 0), 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-ink">Giám sát</h1>
        <div className="flex flex-wrap items-center gap-2" style={TABULAR}>
          <Badge tone={answeringCount < services.length ? "red" : "green"}>
            {answeringCount}/{services.length} dịch vụ trả lời
          </Badge>
          {offline > 0 && <Badge tone="red">Mất Kafka: {offline}</Badge>}
          <Badge tone={waiting > 0 ? "orange" : "gray"}>Chờ gửi: {waiting}</Badge>
          {alerts.length > 0 && <Badge tone="orange">Cảnh báo: {alerts.length}</Badge>}
        </div>
      </div>

      <Panel title="Các dịch vụ" flush>
        <TableContainer>
          <Table className="min-w-[740px]">
            <TableHead>
              <TableRow className="hover:bg-transparent">
                <TableHeaderCell>Dịch vụ</TableHeaderCell>
                <TableHeaderCell>Tình trạng</TableHeaderCell>
                <TableHeaderCell>Kafka</TableHeaderCell>
                <TableHeaderCell>Chi tiết</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {branches.map(({ branch, query }) => (
                <ServiceRow key={branch} name={branch} query={query}>
                  {(data) => <BranchDetail monitor={data} />}
                </ServiceRow>
              ))}
              {consumers.map(({ service, query }) => (
                <ServiceRow key={service} name={service} query={query}>
                  {(data) => <ConsumerDetail monitor={data} />}
                </ServiceRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Panel>

      <SlowConsumers consumers={consumers} />
      <Alerts alerts={alerts} />
    </div>
  );
}

function ServiceRow<T extends BranchMonitor | ConsumerMonitor>({
  name,
  query,
  children,
}: {
  name: string;
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
}) {
  const answering = !query.isError;
  const data = query.data;
  const connected = data
    ? "connection" in data
      ? data.connection.connected
      : data.kafka_reachable
    : undefined;

  return (
    <TableRow className={cn(!answering && "bg-rose-50/60")}>
      <TableCell>
        <span className="inline-flex items-center gap-2 font-semibold text-ink">
          <span
            aria-hidden="true"
            className={cn(
              "h-2 w-2 rounded-full",
              !answering ? "bg-rose-500" : connected === false ? "bg-amber-500" : "bg-emerald-500",
            )}
          />
          {name}
        </span>
      </TableCell>
      <TableCell>
        {query.isPending && answering ? (
          <Spinner size="xs" label="Đang tải" />
        ) : (
          <Badge
            tone={answering ? "green" : "red"}
            icon={
              answering ? (
                <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
              ) : (
                <PlugZap className="h-3 w-3" aria-hidden="true" />
              )
            }
          >
            {answering ? "Đang trả lời" : "Không trả lời"}
          </Badge>
        )}
      </TableCell>
      <TableCell>
        {answering && connected !== undefined && (
          <span
            className={cn(
              "text-sm",
              connected === false ? "font-semibold text-rose-700" : "text-ink-secondary",
            )}
          >
            {connected === true
              ? "Đã kết nối"
              : connected === false
                ? "Mất kết nối Kafka"
                : "Chưa rõ"}
          </span>
        )}
      </TableCell>
      <TableCell>
        {!answering ? (
          <span className="text-xs text-ink-muted" style={TABULAR}>
            {query.dataUpdatedAt
              ? `Lần trả lời cuối lúc ${clock(new Date(query.dataUpdatedAt))}`
              : "Chưa nhận được dữ liệu"}
          </span>
        ) : (
          data && children(data)
        )}
      </TableCell>
    </TableRow>
  );
}

function BranchDetail({ monitor }: { monitor: BranchMonitor }) {
  const parts = [
    `${monitor.waiting_to_send} mục chờ gửi`,
    monitor.awaiting_inventory.length && `${monitor.awaiting_inventory.length} đơn chờ Kho quá lâu`,
    monitor.about_to_expire.length && `${monitor.about_to_expire.length} đơn sắp quá hạn`,
    monitor.cancel_requested.length && `${monitor.cancel_requested.length} đơn đang yêu cầu hủy`,
    monitor.message_alerts.count && `${monitor.message_alerts.count} tin không đọc được`,
  ].filter((p): p is string => Boolean(p));
  return (
    <span className="text-xs text-ink-secondary" style={TABULAR}>
      {parts.join(" · ")}
    </span>
  );
}

function ConsumerDetail({ monitor }: { monitor: ConsumerMonitor }) {
  const unread = monitor.topics.reduce((sum, t) => sum + t.unread, 0);
  const slow = monitor.topics.filter((t) => t.slow).length;
  return (
    <span className="text-xs text-ink-secondary" style={TABULAR}>
      {unread} tin chưa đọc trên {monitor.topics.length} topic
      {slow ? ` · ${slow} topic chậm` : ""}
    </span>
  );
}

function SlowConsumers({
  consumers,
}: {
  consumers: { service: string; query: UseQueryResult<ConsumerMonitor> }[];
}) {
  const slow = consumers.flatMap(({ service, query }) =>
    (query.data?.topics ?? [])
      .filter((t) => t.slow)
      .map((t) => ({ ...t, service, limit: query.data?.slow_after_s ?? 0 })),
  );
  return (
    <Panel title="Consumer chậm" count={slow.length}>
      {slow.length > 0 ? (
        <Alert tone="orange" icon={<Clock className="h-4 w-4" />} title="Có topic đọc chậm">
          <ul className="mt-1 space-y-1">
            {slow.map((t) => (
              <li
                key={`${t.service}-${t.topic}`}
                className="text-xs text-orange-950"
                style={TABULAR}
              >
                {t.service} · <span className="font-mono font-semibold">{t.topic}</span> ·{" "}
                {t.unread} tin chưa đọc, cũ nhất {duration(t.oldest_unread_age_s ?? 0)} (ngưỡng{" "}
                {duration(t.limit)})
              </li>
            ))}
          </ul>
        </Alert>
      ) : (
        <div className="flex items-center gap-2 text-sm text-ink-secondary">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
          <span>Không có consumer nào chậm: mọi tin chưa đọc đều mới hơn ngưỡng 5 phút.</span>
        </div>
      )}
    </Panel>
  );
}

const KINDS = ["ALL", "CAN_KIEM_TRA", "LENH_KHONG_KHOP", "HUY_SAI_CHI_NHANH"] as const;

function Alerts({ alerts }: { alerts: AnyAlert[] }) {
  const [kind, setKind] = useState<string>("ALL");
  const shown = kind === "ALL" ? alerts : alerts.filter((a) => a.kind === kind);
  return (
    <Panel
      title="Cảnh báo"
      count={shown.length}
      flush
      actions={
        <SegmentedRadio
          aria-label="Lọc theo loại cảnh báo"
          size="sm"
          value={kind}
          onChange={setKind}
          options={KINDS.map((k) => ({
            value: k,
            label: k === "ALL" ? "Tất cả" : ALERT_KIND[k],
          }))}
        />
      }
    >
      {shown.length === 0 ? (
        <EmptyState icon={Bell}>
          Không có cảnh báo nào{kind === "ALL" ? "" : " thuộc loại này"}. Tin không đọc được, lệnh
          không khớp và yêu cầu hủy sai chi nhánh sẽ hiện ở đây.
        </EmptyState>
      ) : (
        <div className="divide-y divide-line">
          {shown.map((a) => (
            <div
              key={`${a.service}-${a.source_topic}-${a.created_at}-${a.kind}`}
              className="flex items-center gap-2.5 px-4 py-2.5 text-xs text-ink"
              style={TABULAR}
            >
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-orange-600" aria-hidden="true" />
              <span>
                {clock(a.created_at)} · {a.service} ·{" "}
                {ALERT_KIND[a.kind as keyof typeof ALERT_KIND] ?? a.kind}
                {a.order_id ? ` · đơn ${a.order_id.slice(0, 8)}` : ""} ·{" "}
                <span className="font-mono text-ink-secondary">{a.source_topic}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
