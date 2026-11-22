// The branch screen (POS counter and Online ordering): place orders, follow their statuses,
// cancel, and see Flow D. Specified in .claude/skills/screen/references/screens.md ("branch").
// It shows what the Branch service returns and decides nothing itself.

import {
  Badge,
  Grid,
  Group,
  Loader,
  SegmentedControl,
  Stack,
  Text,
  Title,
  VisuallyHidden,
} from "@mantine/core";
import { IconPlugConnected, IconPlugConnectedX, IconQuestionMark } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import type { BranchId, Monitor, Order } from "../../api/branch";
import { BRANCHES, branchApi, isBranch } from "../../api/branch";
import { ServiceBanner } from "../../components/common";
import { ORDER_STATUS } from "../../labels";
import { BranchAlerts } from "./BranchAlerts";
import { CancelModal } from "./CancelModal";
import { OrderForm } from "./OrderForm";
import { OrdersTable } from "./OrdersTable";

export function BranchScreen() {
  const { branchId } = useParams();
  if (!isBranch(branchId)) {
    return <Text>Không có chi nhánh {branchId}.</Text>;
  }
  return <Branch key={branchId} branch={branchId} />;
}

function Branch({ branch }: { branch: BranchId }) {
  const api = branchApi(branch);
  const navigate = useNavigate();
  const orders = useQuery({ queryKey: ["branch", branch, "orders"], queryFn: api.orders });
  const monitor = useQuery({ queryKey: ["branch", branch, "monitor"], queryFn: api.monitor });
  const [cancelling, setCancelling] = useState<string | null>(null);
  const announcement = useStatusAnnouncer(orders.data);

  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="wrap" gap="sm">
        <Title order={1}>Chi nhánh {branch}</Title>
        <Group gap="sm" wrap="wrap">
          <Connection monitor={monitor.data} answering={!monitor.isError} />
          <SegmentedControl
            aria-label="Chọn chi nhánh"
            data={[...BRANCHES]}
            value={branch}
            onChange={(value) => navigate(`/branch/${value}`)}
          />
        </Group>
      </Group>

      {(orders.isError || monitor.isError) && (
        <ServiceBanner
          service={`chi nhánh ${branch}`}
          lastAnswer={Math.max(orders.dataUpdatedAt, monitor.dataUpdatedAt)}
        />
      )}

      {monitor.data && <BranchAlerts monitor={monitor.data} onCancel={setCancelling} />}

      <Grid gap="md">
        <Grid.Col span={{ base: 12, lg: 3 }} style={{ minWidth: 0 }}>
          <OrderForm branch={branch} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 9 }} style={{ minWidth: 0 }}>
          <Stack gap="xs">
            <Title order={2} size="h4">
              Đơn của chi nhánh
            </Title>
            {orders.isPending && !orders.isError ? (
              <Loader size="sm" aria-label="Đang tải đơn" />
            ) : (
              <OrdersTable orders={orders.data ?? []} onCancel={setCancelling} />
            )}
          </Stack>
        </Grid.Col>
      </Grid>

      <CancelModal branch={branch} orderId={cancelling} onClose={() => setCancelling(null)} />
      <VisuallyHidden>
        <div role="status" aria-live="polite">
          {announcement}
        </div>
      </VisuallyHidden>
    </Stack>
  );
}

/** Connection to Kafka and the entries waiting to be sent, from GET /monitor (section 8). */
function Connection({ monitor, answering }: { monitor: Monitor | undefined; answering: boolean }) {
  const connected = answering ? monitor?.connection.connected : undefined;
  const badge =
    connected === true
      ? { color: "green", label: "Đã kết nối Kafka", Icon: IconPlugConnected }
      : connected === false
        ? { color: "red", label: "Mất kết nối Kafka", Icon: IconPlugConnectedX }
        : { color: "gray", label: "Chưa rõ kết nối Kafka", Icon: IconQuestionMark };
  return (
    <Group gap="xs">
      <Badge
        color={badge.color}
        variant="light"
        leftSection={<badge.Icon size={12} aria-hidden />}
        styles={{ label: { textTransform: "none" } }}
      >
        {badge.label}
      </Badge>
      {monitor && (
        <Text size="sm" style={{ fontVariantNumeric: "tabular-nums" }}>
          {monitor.waiting_to_send} mục chờ gửi
        </Text>
      )}
    </Group>
  );
}

/** One polite announcement per status change between two reads (design.md, "Behaviour"). */
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
