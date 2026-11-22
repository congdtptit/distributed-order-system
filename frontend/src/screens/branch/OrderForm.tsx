// The order form: the branch's own dish catalogue with each dish's cached status (GET /menu,
// available offline) and a quantity per dish; POST /orders. The order then shows as Awaiting
// Inventory until a status message arrives (section 4 of the specification).
//
// Flow C (section 7): while the data is fresh, a Sold-out dish cannot be selected; when it is
// stale or the branch is offline, it shows "May be sold out" and can still be ordered, under
// one general line. A Hidden dish is never shown. This is the one rule enforced only on screen
// (point 5 in section 8 of document 02): Inventory still decides every order.

import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Group,
  NumberInput,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconAlertTriangle, IconMinus, IconPlus, IconSend } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { BranchId } from "../../api/branch";
import { branchApi } from "../../api/branch";
import { ApiError, detailMessage } from "../../api/http";
import { Panel } from "../../components/layout";
import { DISH_FRESH, DISH_STALE, MENU_STALE_LINE } from "../../labels";

const MAX_QUANTITY = 99;

export function OrderForm({
  branch,
  headingLevel = 2,
  offline = false,
}: {
  branch: BranchId;
  headingLevel?: 2 | 3;
  /** The branch's last Kafka probe failed (GET /monitor): treat the dish data as stale. */
  offline?: boolean;
}) {
  const api = branchApi(branch);
  const client = useQueryClient();
  const menu = useQuery({ queryKey: ["branch", branch, "menu"], queryFn: api.menu });
  const stale = offline || (menu.data?.stale ?? true);
  const shown = (menu.data?.dishes ?? []).filter((dish) => dish.status !== "AN");
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [refused, setRefused] = useState<string | null>(null);
  const blocked = (status: string | null) => status === "HET" && !stale;
  // Only dishes on the form now and selectable go into the order: a quantity typed while the
  // data was stale must not travel once the dish is blocked or Hidden (section 7).
  const selectable = new Set(shown.filter((d) => !blocked(d.status)).map((d) => d.dish_id));
  const items = Object.entries(quantities)
    .filter(([dish_id, q]) => q > 0 && selectable.has(dish_id))
    .map(([dish_id, quantity]) => ({ dish_id, quantity }));

  const place = useMutation({
    mutationFn: () => api.place({ items }),
    onSuccess: (order) => {
      notifications.show({
        color: "green",
        message: `Đã tạo đơn ${order.order_id.slice(0, 8)}, đang chờ Kho`,
      });
      setQuantities({});
      setRefused(null);
      client.invalidateQueries({ queryKey: ["branch", branch] });
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.status === 400) {
        setRefused(detailMessage(failure.body) ?? "Kiểm tra lại món và số lượng.");
      } else {
        notifications.show({
          color: "red",
          title: `Không kết nối được tới chi nhánh ${branch}`,
          message: "Đơn chưa được tạo. Bấm Tạo đơn để thử lại.",
        });
      }
    },
  });

  const set = (dishId: string, quantity: number) =>
    setQuantities((current) => ({
      ...current,
      [dishId]: Math.max(0, Math.min(MAX_QUANTITY, quantity)),
    }));
  const portions = items.reduce((sum, item) => sum + item.quantity, 0);
  const names = new Map(shown.map((d) => [d.dish_id, d.name]));

  return (
    <Panel title="Tạo đơn" level={headingLevel}>
      <Stack gap="md">
        {stale && menu.data && (
          <Alert color="yellow" variant="light" icon={<IconAlertTriangle aria-hidden />} py="xs">
            {MENU_STALE_LINE}
          </Alert>
        )}
        {menu.isPending ? (
          <Stack gap="xs">
            <SimpleGrid cols={3} spacing="sm">
              {[1, 2, 3].map((n) => (
                <Skeleton key={n} h={96} radius="md" />
              ))}
            </SimpleGrid>
            <Text c="dimmed" size="sm">
              Đang tải danh mục món…
            </Text>
          </Stack>
        ) : (
          <SimpleGrid
            cols={headingLevel === 3 ? { base: 2, xl: 3 } : { base: 2, sm: 3, xl: 6 }}
            spacing="sm"
          >
            {shown.map((dish) => {
              const off = blocked(dish.status);
              const quantity = off ? 0 : (quantities[dish.dish_id] ?? 0);
              const picked = quantity > 0;
              return (
                <Card
                  key={dish.dish_id}
                  padding="sm"
                  shadow="none"
                  bg={off ? "gray.0" : picked ? "indigo.0" : "white"}
                  style={{
                    borderColor: picked
                      ? "var(--mantine-color-indigo-4)"
                      : "var(--mantine-color-gray-3)",
                    transition: "background-color 120ms, border-color 120ms",
                  }}
                >
                  <NumberInput
                    label={dish.name}
                    description={
                      dish.status === "HET" ? (stale ? DISH_STALE.HET : DISH_FRESH.HET) : undefined
                    }
                    inputWrapperOrder={["label", "description", "input", "error"]}
                    labelProps={{ fw: 600, mb: 2, c: off ? "dimmed" : "dark" }}
                    descriptionProps={{ c: stale ? "orange.9" : "red.8", fw: 600, mb: 6 }}
                    styles={{
                      root: { display: "flex", flexDirection: "column", height: "100%" },
                      wrapper: { marginTop: "auto" },
                      input: { textAlign: "center", fontWeight: 600 },
                    }}
                    disabled={off}
                    min={0}
                    max={MAX_QUANTITY}
                    allowDecimal={false}
                    allowNegative={false}
                    hideControls
                    placeholder="0"
                    value={off ? "" : (quantities[dish.dish_id] ?? "")}
                    onChange={(value) => set(dish.dish_id, typeof value === "number" ? value : 0)}
                    leftSectionPointerEvents="all"
                    rightSectionPointerEvents="all"
                    leftSection={
                      <ActionIcon
                        variant="subtle"
                        color="gray"
                        disabled={off || !picked}
                        onClick={() => set(dish.dish_id, quantity - 1)}
                        aria-label={`Bớt một ${dish.name}`}
                      >
                        <IconMinus size={16} aria-hidden />
                      </ActionIcon>
                    }
                    rightSection={
                      <ActionIcon
                        variant="subtle"
                        disabled={off}
                        onClick={() => set(dish.dish_id, quantity + 1)}
                        aria-label={`Thêm một ${dish.name}`}
                      >
                        <IconPlus size={16} aria-hidden />
                      </ActionIcon>
                    }
                  />
                </Card>
              );
            })}
          </SimpleGrid>
        )}
        {refused && (
          <Alert color="red" title="Đơn không hợp lệ">
            {refused}
          </Alert>
        )}
        <Group justify="space-between" wrap="wrap" gap="sm">
          <Text size="sm" c={items.length ? "dark" : "dimmed"} style={{ minWidth: 0, flex: 1 }}>
            {items.length
              ? `${portions} phần: ${items
                  .map((item) => `${names.get(item.dish_id) ?? item.dish_id} ×${item.quantity}`)
                  .join(", ")}`
              : "Chọn số lượng món để tạo đơn."}
          </Text>
          <Group gap="xs">
            <Button
              variant="default"
              onClick={() => setQuantities({})}
              disabled={!items.length || place.isPending}
            >
              Xóa chọn
            </Button>
            <Button
              onClick={() => place.mutate()}
              loading={place.isPending}
              disabled={!items.length}
              leftSection={<IconSend size={16} aria-hidden />}
            >
              Tạo đơn
            </Button>
          </Group>
        </Group>
      </Stack>
    </Panel>
  );
}
