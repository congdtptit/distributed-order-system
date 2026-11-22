// The order form: the branch's own dish catalogue with each dish's cached status (GET /menu,
// available offline) and a quantity per dish; POST /orders. The order then shows as Awaiting
// Inventory until a status message arrives (section 4 of the specification).
//
// Flow C (section 7): while the data is fresh, a Sold-out dish cannot be selected; when it is
// stale or the branch is offline, it shows "May be sold out" and can still be ordered, under
// one general line. A Hidden dish is never shown. This is the one rule enforced only on screen
// (point 5 in section 8 of document 02): Inventory still decides every order.

import { Alert, Button, Card, NumberInput, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { BranchId } from "../../api/branch";
import { branchApi } from "../../api/branch";
import { ApiError, detailMessage } from "../../api/http";
import { DISH_FRESH, DISH_STALE, MENU_STALE_LINE } from "../../labels";

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
  const items = Object.entries(quantities)
    .filter(([, q]) => q > 0)
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

  return (
    <Card withBorder padding="md">
      <Stack gap="sm">
        <Title order={headingLevel} size="h4">
          Tạo đơn
        </Title>
        {stale && menu.data && (
          <Text size="sm" c="orange.9">
            {MENU_STALE_LINE}
          </Text>
        )}
        {menu.isPending ? (
          <Text c="dimmed" size="sm">
            Đang tải danh mục món…
          </Text>
        ) : (
          <SimpleGrid
            cols={headingLevel === 3 ? { base: 1, xs: 2, xl: 3 } : { base: 1, sm: 2, lg: 1 }}
            spacing="xs"
          >
            {shown.map((dish) => (
              <NumberInput
                key={dish.dish_id}
                label={dish.name}
                description={
                  dish.status === "HET" ? (stale ? DISH_STALE.HET : DISH_FRESH.HET) : undefined
                }
                descriptionProps={{ c: stale ? "orange.9" : "red.8", fw: 600 }}
                disabled={dish.status === "HET" && !stale}
                min={0}
                max={99}
                allowDecimal={false}
                allowNegative={false}
                placeholder="0"
                value={quantities[dish.dish_id] ?? ""}
                onChange={(value) =>
                  setQuantities((current) => ({
                    ...current,
                    [dish.dish_id]: typeof value === "number" ? value : 0,
                  }))
                }
              />
            ))}
          </SimpleGrid>
        )}
        {refused && (
          <Alert color="red" title="Đơn không hợp lệ">
            {refused}
          </Alert>
        )}
        <Button onClick={() => place.mutate()} loading={place.isPending} disabled={!items.length}>
          Tạo đơn
        </Button>
      </Stack>
    </Card>
  );
}
