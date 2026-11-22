// The two dialogs of the Inventory screen: a stock receipt (POST /stock/receipts) and the end
// of a stock check (POST /ingredients/{id}/clear-check, BR6), with the answers of section 6.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { ApiError, detailMessage } from "../../api/http";
import type { StockItem } from "../../api/inventory";
import { amount, inventoryApi } from "../../api/inventory";
import { Alert, Button, cn, Dialog, toast } from "../../ui";

const QUANTITY = /^\d{1,9}([.,]\d{1,3})?$/;
const INVALID = "Số lượng không hợp lệ: số dương, tối đa 3 chữ số thập phân.";

function parse(text: string): string | null {
  const trimmed = text.trim();
  return QUANTITY.test(trimmed) ? trimmed.replace(",", ".") : null;
}

function useReload() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["inventory"] });
}

function noAnswer() {
  toast.show({
    color: "red",
    title: "Không kết nối được tới Kho",
    message: "Thao tác chưa được ghi nhận; bấm xác nhận lại để thử lại.",
  });
}

export function ReceiptModal({ item, onClose }: { item: StockItem | null; onClose: () => void }) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputId = useId();
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
        toast.show({
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
        toast.show({
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
    <Dialog
      open={item !== null}
      onOpenChange={(open) => {
        if (!open) close();
      }}
      title={`Nhập kho ${item?.name ?? ""}`}
    >
      <div className="space-y-4">
        <p className="text-sm text-ink-secondary">
          Số lượng nhập được cộng vào lượng còn có thể giữ cho đơn mới.
        </p>
        <div className="space-y-1.5">
          <label htmlFor={inputId} className="block text-sm font-medium text-ink">
            {`Số lượng nhập (${item?.unit ?? ""})`}
          </label>
          <input
            id={inputId}
            type="text"
            inputMode="decimal"
            autoFocus
            value={text}
            onChange={(event) => {
              setText(event.currentTarget.value);
              setError(null);
            }}
            className={cn(
              "h-10 w-full rounded-lg border bg-surface px-3 font-mono text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30",
              error ? "border-rose-500" : "border-line-strong",
            )}
          />
          {error && <p className="text-xs font-medium text-rose-700">{error}</p>}
        </div>
        <div className="flex items-center justify-between pt-1">
          <Button variant="secondary" onClick={close}>
            Đóng
          </Button>
          <Button variant="primary" onClick={confirm} loading={receive.isPending}>
            Xác nhận nhập kho
          </Button>
        </div>
      </div>
    </Dialog>
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
  const inputId = useId();
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
        toast.show({ color: "green", message: `Đã gỡ cờ kiểm kho của ${item.name}` });
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
        toast.show({
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
    <Dialog
      open={item !== null}
      onOpenChange={(open) => {
        if (!open) close();
      }}
      title={`Kiểm kho xong: ${item?.name ?? ""}`}
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-ink-secondary">
          Gỡ cờ thì Kho lại giữ được nguyên liệu này cho đơn mới, và cảnh báo trên phiếu bếp biến
          mất. Nếu nhập tồn đếm được (gồm cả lượng đang giữ), Kho đặt lại lượng còn có thể giữ; để
          trống thì giữ nguyên.
        </p>
        <div className="space-y-1.5">
          <label htmlFor={inputId} className="block text-sm font-medium text-ink">
            {`Tồn đếm được (${item?.unit ?? ""})`}
          </label>
          <p className="text-xs text-ink-muted">Không bắt buộc</p>
          <input
            id={inputId}
            type="text"
            inputMode="decimal"
            autoFocus
            value={text}
            onChange={(event) => {
              setText(event.currentTarget.value);
              setError(null);
            }}
            className={cn(
              "h-10 w-full rounded-lg border bg-surface px-3 font-mono text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent/30",
              error ? "border-rose-500" : "border-line-strong",
            )}
          />
          {error && <p className="text-xs font-medium text-rose-700">{error}</p>}
        </div>

        {blocked && item && (
          <Alert tone="orange" role="alert" className="text-xs">
            Tồn đếm được ít hơn lượng đang giữ {amount(blocked)} {item.unit}. Hãy từ chối các phiếu
            còn giữ {item.name} trên màn Bếp (lý do Nguyên liệu hỏng) rồi kiểm kho lại.
          </Alert>
        )}

        <div className="flex items-center justify-between pt-1">
          <Button variant="secondary" onClick={close}>
            Đóng
          </Button>
          <Button variant="accent" onClick={confirm} loading={clear.isPending}>
            Gỡ cờ kiểm kho
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
