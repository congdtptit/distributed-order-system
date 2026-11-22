// The two dialogs of the Inventory screen: a stock receipt (POST /stock/receipts) and the end
// of a stock check (POST /ingredients/{id}/clear-check, BR6), with the answers of section 6 of
// docs/02-detailed-design.md. Quantities are sent as decimal strings.

import { Alert, Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, detailMessage } from "../../api/http";
import type { StockItem } from "../../api/inventory";
import { amount, inventoryApi } from "../../api/inventory";

const QUANTITY = /^\d{1,9}([.,]\d{1,3})?$/;
const INVALID = "Số lượng không hợp lệ: số dương, tối đa 3 chữ số thập phân.";

/** "2,5" or "2.5" -> "2.5"; null if it is not a quantity NUMERIC(12,3) can hold. */
function parse(text: string): string | null {
  const trimmed = text.trim();
  return QUANTITY.test(trimmed) ? trimmed.replace(",", ".") : null;
}

function useReload() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["inventory"] });
}

function noAnswer() {
  notifications.show({
    color: "red",
    title: "Không kết nối được tới Kho",
    message: "Thao tác chưa được ghi nhận; bấm xác nhận lại để thử lại.",
  });
}

export function ReceiptModal({ item, onClose }: { item: StockItem | null; onClose: () => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const reload = useReload();
  const close = () => {
    setText("");
    setError(null);
    onClose();
  };
  const receive = useMutation({
    mutationFn: ({ id, quantity }: { id: string; quantity: string }) =>
      inventoryApi.receive(id, quantity),
    onSuccess: (_stock, { quantity }) => {
      if (item) {
        notifications.show({
          color: "green",
          message: `Đã nhập ${amount(quantity)} ${item.unit} ${item.name}`,
        });
      }
      reload();
      close();
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.status === 422) setError(INVALID);
      else if (failure instanceof ApiError && failure.status === 404) {
        notifications.show({
          color: "yellow",
          message: "Kho không có nguyên liệu này, đã tải lại",
        });
        reload();
        close();
      } else noAnswer();
    },
  });
  const confirm = () => {
    const quantity = parse(text);
    if (!item) return;
    if (quantity === null || Number(quantity) <= 0) {
      setError(INVALID);
      return;
    }
    receive.mutate({ id: item.ingredient_id, quantity });
  };
  return (
    <Modal opened={item !== null} onClose={close} title={`Nhập kho ${item?.name ?? ""}`} centered>
      <Stack gap="md">
        <Text size="sm">Số lượng nhập được cộng vào lượng còn có thể giữ cho đơn mới.</Text>
        <TextInput
          label={`Số lượng nhập (${item?.unit ?? ""})`}
          inputMode="decimal"
          value={text}
          onChange={(event) => {
            setText(event.currentTarget.value);
            setError(null);
          }}
          error={error}
          data-autofocus
        />
        <Group justify="space-between">
          <Button variant="default" onClick={close}>
            Đóng
          </Button>
          <Button onClick={confirm} loading={receive.isPending}>
            Xác nhận nhập kho
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function ClearCheckModal({
  item,
  onClose,
}: {
  item: StockItem | null;
  onClose: () => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);
  const reload = useReload();
  const close = () => {
    setText("");
    setError(null);
    setBlocked(null);
    onClose();
  };
  const clear = useMutation({
    mutationFn: ({ id, counted }: { id: string; counted: string | null }) =>
      inventoryApi.clearCheck(id, counted),
    onSuccess: () => {
      if (item) {
        notifications.show({ color: "green", message: `Đã gỡ cờ kiểm kho của ${item.name}` });
      }
      reload();
      close();
    },
    onError: (failure) => {
      if (failure instanceof ApiError && failure.status === 409) {
        const body = failure.body as { detail?: { reserved?: unknown } } | null;
        const reserved = body?.detail?.reserved;
        setBlocked(typeof reserved === "string" ? reserved : (detailMessage(failure.body) ?? "?"));
      } else if (failure instanceof ApiError && failure.status === 422) setError(INVALID);
      else if (failure instanceof ApiError && failure.status === 404) {
        notifications.show({
          color: "yellow",
          message: "Kho không có nguyên liệu này, đã tải lại",
        });
        reload();
        close();
      } else noAnswer();
    },
  });
  const confirm = () => {
    if (!item) return;
    let counted: string | null = null;
    if (text.trim()) {
      counted = parse(text);
      if (counted === null) {
        setError(INVALID);
        return;
      }
    }
    setBlocked(null);
    clear.mutate({ id: item.ingredient_id, counted });
  };
  return (
    <Modal
      opened={item !== null}
      onClose={close}
      title={`Kiểm kho xong: ${item?.name ?? ""}`}
      centered
    >
      <Stack gap="md">
        <Text size="sm">
          Gỡ cờ thì Kho lại giữ được nguyên liệu này cho đơn mới, và cảnh báo trên phiếu bếp biến
          mất. Nếu nhập tồn đếm được (gồm cả lượng đang giữ), Kho đặt lại lượng còn có thể giữ; để
          trống thì giữ nguyên.
        </Text>
        <TextInput
          label={`Tồn đếm được (${item?.unit ?? ""})`}
          description="Không bắt buộc"
          inputMode="decimal"
          value={text}
          onChange={(event) => {
            setText(event.currentTarget.value);
            setError(null);
          }}
          error={error}
          data-autofocus
        />
        {blocked && item && (
          <Alert color="orange" role="alert">
            Tồn đếm được ít hơn lượng đang giữ {amount(blocked)} {item.unit}. Hãy từ chối các phiếu
            còn giữ {item.name} trên màn Bếp (lý do Nguyên liệu hỏng) rồi kiểm kho lại.
          </Alert>
        )}
        <Group justify="space-between">
          <Button variant="default" onClick={close}>
            Đóng
          </Button>
          <Button color="teal" onClick={confirm} loading={clear.isPending}>
            Gỡ cờ kiểm kho
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
