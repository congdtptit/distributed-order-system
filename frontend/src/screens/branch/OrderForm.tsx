// The order form: the branch's own dish catalogue (GET /dishes, available offline) and a
// quantity per dish; POST /orders. The order then shows as Awaiting Inventory until a status
// message arrives (section 4 of the specification).

import { Alert, Button, Card, NumberInput, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { BranchId } from "../../api/branch";
import { branchApi } from "../../api/branch";
import { ApiError, detailMessage } from "../../api/http";

export function OrderForm({ branch }: { branch: BranchId }) {
  const api = branchApi(branch);
  const client = useQueryClient();
  const dishes = useQuery({
    queryKey: ["branch", branch, "dishes"],
    queryFn: api.dishes,
    refetchInterval: false,
  });
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
        <Title order={2} size="h4">
          Tạo đơn
        </Title>
        {dishes.isPending ? (
          <Text c="dimmed" size="sm">
            Đang tải danh mục món…
          </Text>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 1 }} spacing="xs">
            {(dishes.data ?? []).map((dish) => (
              <NumberInput
                key={dish.dish_id}
                label={dish.name}
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
