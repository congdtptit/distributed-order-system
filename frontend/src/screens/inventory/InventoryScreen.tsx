// The Inventory screen: stock ledger with visual capacity bars, stock-check priority,
// stock receipts, clear-check, and Flow D alerts.

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, AlertTriangle, CheckSquare, Package, PackagePlus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { InventoryAlert, StockItem } from "../../api/inventory";
import { amount, inventoryApi } from "../../api/inventory";
import { clock, ServiceBanner, StatusBadge, TABULAR } from "../../components/common";
import { StackedBar } from "../../components/DataBar";
import { ALERT_KIND, STOCK_CHECK } from "../../labels";
import {
  Alert,
  Badge,
  Button,
  cn,
  EmptyState,
  Panel,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../ui";
import { ClearCheckModal, ReceiptModal } from "./StockDialogs";

export function InventoryScreen() {
  const stock = useQuery({ queryKey: ["inventory", "stock"], queryFn: inventoryApi.stock });
  const alerts = useQuery({ queryKey: ["inventory", "alerts"], queryFn: inventoryApi.alerts });
  const [receiving, setReceiving] = useState<StockItem | null>(null);
  const [clearing, setClearing] = useState<StockItem | null>(null);
  const announcement = useFlagAnnouncer(stock.data);

  // Flagged ingredients first (screens.md), then the order Inventory returns.
  const items = [...(stock.data ?? [])].sort(
    (a, b) => Number(b.needs_check) - Number(a.needs_check),
  );
  const flaggedCount = items.filter((i) => i.needs_check).length;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-ink">Kho</h1>
        {stock.data && (
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="gray">{stock.data.length} nguyên liệu</Badge>
            {flaggedCount > 0 && (
              <Badge tone="red" icon={<AlertTriangle className="h-3 w-3" aria-hidden="true" />}>
                {flaggedCount} chờ kiểm kho
              </Badge>
            )}
          </div>
        )}
      </div>

      {(stock.isError || alerts.isError) && (
        <ServiceBanner
          service="Kho"
          lastAnswer={Math.max(stock.dataUpdatedAt, alerts.dataUpdatedAt)}
        />
      )}

      {flaggedCount > 0 && (
        <Alert
          tone="danger"
          icon={<AlertTriangle className="h-4 w-4" />}
          className="py-2.5 text-xs"
        >
          Có {flaggedCount} nguyên liệu đang chờ kiểm kho — món dùng nguyên liệu này tạm Hết trên
          thực đơn chi nhánh.
        </Alert>
      )}

      <InventoryAlerts alerts={alerts.data ?? []} />

      <Panel title="Tồn kho toàn chuỗi" count={items.length} flush>
        {stock.isPending && !stock.isError ? (
          <div className="flex justify-center py-10">
            <Spinner size="md" label="Đang tải tồn kho" />
          </div>
        ) : items.length === 0 ? (
          <EmptyState icon={Package}>
            Chưa có nguyên liệu nào. Kho nạp nguyên liệu từ file seed khi khởi động lần đầu.
          </EmptyState>
        ) : (
          <TableContainer>
            <Table className="min-w-[820px]">
              <TableHead>
                <TableRow className="hover:bg-transparent">
                  <TableHeaderCell>Nguyên liệu</TableHeaderCell>
                  <TableHeaderCell className="text-right">Có thể giữ</TableHeaderCell>
                  <TableHeaderCell className="text-right">Đang giữ</TableHeaderCell>
                  <TableHeaderCell className="text-right">Đã dùng</TableHeaderCell>
                  <TableHeaderCell className="text-right">Hao hụt</TableHeaderCell>
                  <TableHeaderCell>Kiểm kho</TableHeaderCell>
                  <TableHeaderCell className="text-right">Thao tác</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item) => {
                  const avail = Number(item.available) || 0;
                  const res = Number(item.reserved) || 0;
                  const waste = Number(item.wasted) || 0;
                  return (
                    <TableRow
                      key={item.ingredient_id}
                      className={cn(item.needs_check && "bg-rose-50/90 hover:bg-rose-100/70")}
                    >
                      <TableCell>
                        <div className="min-w-[140px] space-y-1.5">
                          <span className="block font-semibold text-ink">{item.name}</span>
                          <StackedBar
                            className="h-2 max-w-[140px]"
                            segments={[
                              {
                                key: "avail",
                                label: "Có thể giữ",
                                value: avail,
                                colorClass: "bg-blue-600",
                              },
                              {
                                key: "res",
                                label: "Đang giữ",
                                value: res,
                                colorClass: "bg-amber-500",
                              },
                              {
                                key: "waste",
                                label: "Hao hụt",
                                value: waste,
                                colorClass: "bg-rose-600",
                              },
                            ]}
                          />
                        </div>
                      </TableCell>
                      {[item.available, item.reserved, item.consumed, item.wasted].map(
                        (value, i) => (
                          <TableCell
                            key={["available", "reserved", "consumed", "wasted"][i]}
                            style={TABULAR}
                            className={cn(
                              "text-right font-mono text-xs",
                              i === 0
                                ? "font-bold text-ink"
                                : i === 1 && Number(value) > 0
                                  ? "font-semibold text-blue-800"
                                  : i === 3 && Number(value) > 0
                                    ? "font-semibold text-rose-700"
                                    : "text-ink-secondary",
                            )}
                          >
                            {`${amount(value)} ${item.unit}`}
                          </TableCell>
                        ),
                      )}
                      <TableCell>
                        {item.needs_check && (
                          <StatusBadge code="CHO_KIEM_KHO" table={STOCK_CHECK} />
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex flex-nowrap justify-end gap-1.5">
                          {item.needs_check && (
                            <Button size="xs" variant="accent" onClick={() => setClearing(item)}>
                              <CheckSquare className="h-3.5 w-3.5" aria-hidden="true" />
                              Kiểm kho xong
                            </Button>
                          )}
                          <Button size="xs" variant="secondary" onClick={() => setReceiving(item)}>
                            <PackagePlus className="h-3.5 w-3.5" aria-hidden="true" />
                            Nhập kho
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Panel>

      <ReceiptModal
        key={`r-${receiving?.ingredient_id ?? ""}`}
        item={receiving}
        onClose={() => setReceiving(null)}
      />
      <ClearCheckModal
        key={`c-${clearing?.ingredient_id ?? ""}`}
        item={clearing}
        onClose={() => setClearing(null)}
      />
      <div role="status" aria-live="polite" className="sr-only">
        {announcement}
      </div>
    </div>
  );
}

function InventoryAlerts({ alerts }: { alerts: InventoryAlert[] }) {
  if (!alerts.length) return null;
  return (
    <section aria-label="Cảnh báo của Kho">
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

function describe(alert: InventoryAlert): string {
  const detail = alert.detail as { event_type?: unknown; record_status?: unknown };
  if (alert.kind === "LENH_KHONG_KHOP") {
    const what = String(detail.event_type ?? "Lệnh");
    return detail.record_status
      ? `${what} cho đơn đã Thất bại; tồn kho không đổi, kiểm tra bằng tay`
      : `${what} cho đơn không có bản ghi; tồn kho không đổi, kiểm tra bằng tay`;
  }
  return `tin trên ${alert.source_topic} đã chuyển vào dlq`;
}

function useFlagAnnouncer(items: StockItem[] | undefined): string {
  const previous = useRef<Map<string, boolean> | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!items) return;
    const now = new Map(items.map((i) => [i.ingredient_id, i.needs_check]));
    const before = previous.current;
    previous.current = now;
    if (!before) return;
    const changes = items
      .filter((i) => before.has(i.ingredient_id) && before.get(i.ingredient_id) !== i.needs_check)
      .map((i) =>
        i.needs_check ? `${i.name} bị đánh dấu chờ kiểm kho` : `${i.name} đã được gỡ cờ kiểm kho`,
      );
    if (changes.length) setMessage(changes.join(". "));
  }, [items]);
  return message;
}
