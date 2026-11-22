// The Kitchen screen (tablet or wall screen): Queued and Cooking tickets with their buttons,
// the reject dialog, and the Kitchen's alerts. Specified in
// .claude/skills/screen/references/screens.md ("kitchen"). It shows what the Kitchen service
// returns; a 409 is the normal end of a race (BR7) and only reloads.

import {
  Alert,
  Button,
  Grid,
  List,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  Title,
  VisuallyHidden,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle } from "@tabler/icons-react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { ApiError, detailMessage } from "../../api/http";
import type { Alert as KitchenAlert, Ticket } from "../../api/kitchen";
import { kitchenApi } from "../../api/kitchen";
import { clock, ServiceBanner, TABULAR } from "../../components/common";
import { ALERT_KIND, KITCHEN_STATUS } from "../../labels";
import { RejectModal } from "./RejectModal";
import { type TicketAction, TicketCard } from "./TicketCard";

/** Tickets shown per column before "Xem thêm". */
const PAGE = 20;

interface Request {
  orderId: string;
  action: TicketAction;
  reason?: string;
  spoiled?: string[];
}

/** The Kitchen screen; the demo page embeds it beside a branch (``embedded``: a level-2
 * heading and one card per row in each column). */
export function KitchenScreen({ embedded = false }: { embedded?: boolean } = {}) {
  const client = useQueryClient();
  // A page of each column, not every ticket: a long queue made the screen lag when it
  // reloaded every 2 seconds. "Xem thêm" grows the page.
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
      notifications.show({ color: "green", message });
      setRejecting(null);
      setRefused(null);
      reload();
    },
    onError: (failure, request) => {
      if (failure instanceof ApiError && (failure.status === 409 || failure.status === 404)) {
        notifications.show({ color: "yellow", message: "Phiếu vừa đổi trạng thái, đã tải lại" });
        setRejecting(null);
        reload();
      } else if (failure instanceof ApiError && failure.status === 400) {
        setRefused(detailMessage(failure.body) ?? "lý do hoặc nguyên liệu không hợp lệ");
      } else {
        notifications.show({
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
    <Stack gap="md">
      <Title order={embedded ? 2 : 1}>Bếp</Title>
      {(tickets.isError || alerts.isError) && (
        <ServiceBanner
          service="Bếp"
          lastAnswer={Math.max(tickets.dataUpdatedAt, alerts.dataUpdatedAt)}
        />
      )}
      <KitchenAlerts alerts={alerts.data ?? []} />
      {tickets.isPending && !tickets.isError ? (
        <Loader size="sm" aria-label="Đang tải phiếu" />
      ) : (
        <Grid gap="md">
          <Column
            span={{ base: 12, md: 6, xl: embedded ? 6 : 8 }}
            cards={embedded ? { base: 1 } : { base: 1, xl: 2 }}
            level={embedded ? 3 : 2}
            title="Chờ nấu"
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
          </Column>
          <Column
            span={{ base: 12, md: 6, xl: embedded ? 6 : 4 }}
            cards={{ base: 1 }}
            level={embedded ? 3 : 2}
            title="Đang nấu"
            total={counts.data?.DANG_NAU}
            onMore={more}
            empty="Chưa có phiếu nào đang nấu."
          >
            {cooking.map((t) => (
              <TicketCard
                key={t.order_id}
                ticket={t}
                busy={busyFor(t.order_id)}
                onAction={(a) => onAction(t, a)}
              />
            ))}
          </Column>
        </Grid>
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
      <VisuallyHidden>
        <div role="status" aria-live="polite">
          {announcement}
        </div>
      </VisuallyHidden>
    </Stack>
  );
}

/** One status column. On a wall screen the Queued column is wider and holds two cards a row. */
function Column({
  span,
  cards,
  level,
  title,
  total,
  onMore,
  empty,
  children,
}: {
  span: { base: number; md: number; xl: number };
  cards: { base: number; xl?: number };
  level: 2 | 3;
  title: string;
  /** The column's total from GET /tickets/counts; never shown below the tickets on screen,
   * since the two requests are not one snapshot. */
  total: number | undefined;
  onMore: () => void;
  empty: string;
  children: React.ReactNode[];
}) {
  const count = Math.max(total ?? 0, children.length);
  const hidden = count - children.length;
  return (
    <Grid.Col span={span} style={{ minWidth: 0 }}>
      <section aria-label={title}>
        <Stack gap="sm">
          <Title order={level} size="h3">
            {title} ({count})
          </Title>
          {children.length ? (
            <SimpleGrid cols={cards} spacing="sm">
              {children}
            </SimpleGrid>
          ) : (
            <Text c="dimmed">{empty}</Text>
          )}
          {hidden > 0 && (
            <Button variant="light" onClick={onMore}>
              Xem thêm (còn {hidden} phiếu)
            </Button>
          )}
        </Stack>
      </section>
    </Grid.Col>
  );
}

/** The Kitchen's Flow D alerts (section 8 of the specification): wrong-branch cancel requests
 * and orders that need review. */
function KitchenAlerts({ alerts }: { alerts: KitchenAlert[] }) {
  if (!alerts.length) return null;
  return (
    <section aria-label="Cảnh báo của Bếp">
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

function describe(alert: KitchenAlert): string {
  const detail = alert.detail as { origin_branch?: unknown; dismissed?: unknown; error?: unknown };
  if (alert.kind === "HUY_SAI_CHI_NHANH") {
    const dismissed = Array.isArray(detail.dismissed) ? detail.dismissed.join(", ") : "?";
    return `gốc ${String(detail.origin_branch ?? "?")}, bỏ qua ${dismissed}: kiểm tra cấu hình chi nhánh gửi`;
  }
  return `tin trên ${alert.source_topic} đã chuyển vào dlq`;
}

/** One polite announcement per ticket status change between two reads. */
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
