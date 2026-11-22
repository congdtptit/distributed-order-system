// The Monitor screen (the operator): Flow D of every service in one place (section 8 of the
// specification). One row per service, the slow-consumer warnings per topic, and the alerts of
// every service filterable by kind. It has no action that changes an order: the system only
// raises alerts (section 8, first paragraph). Specified in
// .claude/skills/screen/references/screens.md ("monitor").

import {
  Alert,
  Badge,
  Group,
  List,
  Loader,
  SegmentedControl,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconBell,
  IconCircleCheck,
  IconClockExclamation,
  IconInbox,
  IconPlugConnected,
  IconPlugConnectedX,
  IconServer,
} from "@tabler/icons-react";
import { type UseQueryResult, useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { Monitor as BranchMonitor } from "../../api/branch";
import { BRANCHES, branchApi } from "../../api/branch";
import { inventoryApi } from "../../api/inventory";
import type { ConsumerMonitor } from "../../api/kitchen";
import { kitchenApi } from "../../api/kitchen";
import { clock, duration, TABULAR } from "../../components/common";
import { Empty, Figures, PageHeader, Panel } from "../../components/layout";
import { ALERT_KIND } from "../../labels";

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
  // useQueries returns one result per query, in order.
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
  const offline = branches.filter((b) => b.query.data?.connection.connected === false).length;
  const waiting = branches.reduce((sum, b) => sum + (b.query.data?.waiting_to_send ?? 0), 0);

  return (
    <Stack gap="lg">
      <PageHeader
        title="Giám sát"
        description="Màn hình chỉ báo động; hệ thống không tự đổi trạng thái đơn nào vì đơn đã chờ lâu."
      />
      <Figures
        figures={[
          {
            label: "Dịch vụ có trả lời",
            value: `${services.filter((q) => !q.isError).length}/${services.length}`,
            icon: IconServer,
            color: services.some((q) => q.isError) ? "red" : "green",
          },
          {
            label: "Chi nhánh mất Kafka",
            value: offline,
            icon: offline ? IconPlugConnectedX : IconPlugConnected,
            color: offline ? "red" : "green",
          },
          {
            label: "Mục chờ gửi ở chi nhánh",
            value: waiting,
            icon: IconInbox,
            color: waiting ? "orange" : "gray",
          },
          {
            label: "Cảnh báo đang có",
            value: alerts.length,
            icon: IconBell,
            color: alerts.length ? "orange" : "gray",
          },
        ]}
      />

      <Panel title="Các dịch vụ" flush>
        <Table.ScrollContainer minWidth={760}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Dịch vụ</Table.Th>
                <Table.Th>Tình trạng</Table.Th>
                <Table.Th>Kafka</Table.Th>
                <Table.Th>Chi tiết</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
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
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Panel>

      <SlowConsumers consumers={consumers} />
      <Alerts alerts={alerts} />
    </Stack>
  );
}

function ServiceRow<T extends BranchMonitor | ConsumerMonitor>({
  name,
  query,
  children,
}: {
  name: string;
  query: UseQueryResult<T>;
  children: (data: T) => React.ReactNode;
}) {
  const answering = !query.isError;
  const data = query.data;
  const connected = data
    ? "connection" in data
      ? data.connection.connected
      : data.kafka_reachable
    : undefined;
  return (
    <Table.Tr>
      <Table.Td>
        <Text fw={600} size="sm">
          {name}
        </Text>
      </Table.Td>
      <Table.Td>
        {query.isPending && answering ? (
          <Loader size="xs" aria-label="Đang tải" />
        ) : (
          <Badge
            color={answering ? "green" : "red"}
            leftSection={
              answering ? (
                <IconCircleCheck size={12} aria-hidden />
              ) : (
                <IconPlugConnectedX size={12} aria-hidden />
              )
            }
          >
            {answering ? "Đang trả lời" : "Không trả lời"}
          </Badge>
        )}
      </Table.Td>
      <Table.Td>
        {answering && connected !== undefined && (
          <Text size="sm" c={connected ? "dark" : "red.8"} fw={connected ? 400 : 600}>
            {connected === true
              ? "Đã kết nối"
              : connected === false
                ? "Mất kết nối Kafka"
                : "Chưa rõ"}
          </Text>
        )}
      </Table.Td>
      <Table.Td>
        {!answering ? (
          <Text size="sm" c="dimmed">
            {query.dataUpdatedAt
              ? `Lần trả lời cuối lúc ${clock(new Date(query.dataUpdatedAt))}`
              : "Chưa nhận được dữ liệu"}
          </Text>
        ) : (
          data && children(data)
        )}
      </Table.Td>
    </Table.Tr>
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
    <Text size="sm" style={TABULAR}>
      {parts.join(" · ")}
    </Text>
  );
}

function ConsumerDetail({ monitor }: { monitor: ConsumerMonitor }) {
  const unread = monitor.topics.reduce((sum, t) => sum + t.unread, 0);
  const slow = monitor.topics.filter((t) => t.slow).length;
  return (
    <Text size="sm" style={TABULAR}>
      {unread} tin chưa đọc trên {monitor.topics.length} topic
      {slow ? ` · ${slow} topic chậm` : ""}
    </Text>
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
        <Alert color="orange" icon={<IconClockExclamation aria-hidden />} title="Có topic đọc chậm">
          <List spacing={4} size="sm">
            {slow.map((t) => (
              <List.Item key={`${t.service}-${t.topic}`}>
                <Text size="sm" style={TABULAR}>
                  {t.service} ·{" "}
                  <Text span ff="monospace" size="sm">
                    {t.topic}
                  </Text>{" "}
                  · {t.unread} tin chưa đọc, cũ nhất {duration(t.oldest_unread_age_s ?? 0)} (ngưỡng{" "}
                  {duration(t.limit)})
                </Text>
              </List.Item>
            ))}
          </List>
        </Alert>
      ) : (
        <Group gap="xs">
          <IconCircleCheck size={18} color="var(--mantine-color-green-7)" aria-hidden />
          <Text size="sm" c="dimmed">
            Không có consumer nào chậm: mọi tin chưa đọc đều mới hơn ngưỡng 5 phút.
          </Text>
        </Group>
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
        <SegmentedControl
          aria-label="Lọc theo loại cảnh báo"
          size="xs"
          value={kind}
          onChange={setKind}
          data={KINDS.map((k) => ({
            value: k,
            label: k === "ALL" ? "Tất cả" : ALERT_KIND[k],
          }))}
        />
      }
    >
      {shown.length === 0 ? (
        <Empty icon={IconBell}>
          Không có cảnh báo nào{kind === "ALL" ? "" : " thuộc loại này"}. Tin không đọc được, lệnh
          không khớp và yêu cầu hủy sai chi nhánh sẽ hiện ở đây.
        </Empty>
      ) : (
        <Stack gap={0}>
          {shown.map((a) => (
            <Group
              key={`${a.service}-${a.source_topic}-${a.created_at}-${a.kind}`}
              gap="sm"
              px="md"
              py="xs"
              wrap="nowrap"
              style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}
            >
              <IconAlertTriangle size={16} color="var(--mantine-color-orange-7)" aria-hidden />
              <Text size="sm" style={TABULAR}>
                {clock(a.created_at)} · {a.service} ·{" "}
                {ALERT_KIND[a.kind as keyof typeof ALERT_KIND] ?? a.kind}
                {a.order_id ? ` · đơn ${a.order_id.slice(0, 8)}` : ""} · {a.source_topic}
              </Text>
            </Group>
          ))}
        </Stack>
      )}
    </Panel>
  );
}
