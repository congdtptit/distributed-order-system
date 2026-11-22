// The Inventory screen (the store keeper): the four quantities of each ingredient and its
// stock-check flag, stock receipts, ending a stock check, and Inventory's alerts. Specified in
// .claude/skills/screen/references/screens.md ("inventory"). It shows what Inventory returns.

import {
  Alert,
  Button,
  Group,
  List,
  Loader,
  Stack,
  Table,
  Text,
  Title,
  VisuallyHidden,
} from "@mantine/core";
import { IconAlertCircle } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { InventoryAlert, StockItem } from "../../api/inventory";
import { amount, inventoryApi } from "../../api/inventory";
import { clock, ServiceBanner, StatusBadge, TABULAR } from "../../components/common";
import { ALERT_KIND, STOCK_CHECK } from "../../labels";
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

  return (
    <Stack gap="md">
      <Title order={1}>Kho</Title>
      {(stock.isError || alerts.isError) && (
        <ServiceBanner
          service="Kho"
          lastAnswer={Math.max(stock.dataUpdatedAt, alerts.dataUpdatedAt)}
        />
      )}
      <InventoryAlerts alerts={alerts.data ?? []} />
      <Title order={2} size="h4">
        Tồn kho toàn chuỗi
      </Title>
      {stock.isPending && !stock.isError ? (
        <Loader size="sm" aria-label="Đang tải tồn kho" />
      ) : items.length === 0 ? (
        <Text c="dimmed">
          Chưa có nguyên liệu nào. Kho nạp nguyên liệu từ file seed khi khởi động lần đầu.
        </Text>
      ) : (
        <Table.ScrollContainer minWidth={820}>
          <Table verticalSpacing="xs" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nguyên liệu</Table.Th>
                <Table.Th ta="right">Có thể giữ</Table.Th>
                <Table.Th ta="right">Đang giữ</Table.Th>
                <Table.Th ta="right">Đã dùng</Table.Th>
                <Table.Th ta="right">Hao hụt</Table.Th>
                <Table.Th>Kiểm kho</Table.Th>
                <Table.Th>Thao tác</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((item) => (
                <Table.Tr key={item.ingredient_id}>
                  <Table.Td>
                    <Text size="sm" fw={600}>
                      {item.name}
                    </Text>
                  </Table.Td>
                  {[item.available, item.reserved, item.consumed, item.wasted].map((value, i) => (
                    <Table.Td
                      key={["available", "reserved", "consumed", "wasted"][i]}
                      ta="right"
                      style={TABULAR}
                    >
                      {amount(value)} {item.unit}
                    </Table.Td>
                  ))}
                  <Table.Td>
                    {item.needs_check && <StatusBadge code="CHO_KIEM_KHO" table={STOCK_CHECK} />}
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" wrap="nowrap">
                      <Button size="xs" variant="light" onClick={() => setReceiving(item)}>
                        Nhập kho
                      </Button>
                      {item.needs_check && (
                        <Button size="xs" color="teal" onClick={() => setClearing(item)}>
                          Kiểm kho xong
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
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
      <VisuallyHidden>
        <div role="status" aria-live="polite">
          {announcement}
        </div>
      </VisuallyHidden>
    </Stack>
  );
}

/** Inventory's Flow D alerts (section 8): unmatched commands and orders that need review. */
function InventoryAlerts({ alerts }: { alerts: InventoryAlert[] }) {
  if (!alerts.length) return null;
  return (
    <section aria-label="Cảnh báo của Kho">
      <Alert
        color="orange"
        icon={<IconAlertCircle aria-hidden />}
        title={`Cảnh báo (${alerts.length})`}
      >
        <List spacing={4} size="sm">
          {alerts.map((alert) => (
            <List.Item key={alert.id}>
              <Text size="sm" style={TABULAR}>
                {clock(alert.created_at)} ·{" "}
                {ALERT_KIND[alert.kind as keyof typeof ALERT_KIND] ?? alert.kind}
                {alert.order_id ? ` · đơn ${alert.order_id.slice(0, 8)}` : ""} · {describe(alert)}
              </Text>
            </List.Item>
          ))}
        </List>
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

/** One polite announcement when an ingredient is flagged or cleared between two reads. */
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
