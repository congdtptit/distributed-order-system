// The order form: POS-style floating menu tiles directly on the canvas + Dark Slate-Navy
// order slip on the right (GET /menu, POST /orders). Eliminates white-on-white box nesting.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CupSoda,
  Minus,
  Plus,
  ReceiptText,
  Send,
  Trash2,
  UtensilsCrossed,
} from "lucide-react";
import { useState } from "react";
import type { BranchId } from "../../api/branch";
import { branchApi } from "../../api/branch";
import { ApiError, detailMessage } from "../../api/http";
import { DISH_FRESH, DISH_STALE, MENU_STALE_LINE } from "../../labels";
import { Alert, cn, toast } from "../../ui";

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
  const selectable = new Set(shown.filter((d) => !blocked(d.status)).map((d) => d.dish_id));
  const items = Object.entries(quantities)
    .filter(([dish_id, q]) => q > 0 && selectable.has(dish_id))
    .map(([dish_id, quantity]) => ({ dish_id, quantity }));

  const place = useMutation({
    mutationFn: () => api.place({ items }),
    onSuccess: (order) => {
      toast.show({
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
        toast.show({
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
  const embedded = headingLevel === 3;
  const Heading = headingLevel === 2 ? "h2" : "h3";

  return (
    <section aria-label="Tạo đơn" className="space-y-3">
      <Heading className="text-sm font-semibold tracking-[-0.01em] text-ink">Tạo đơn</Heading>

      {stale && menu.data && (
        <Alert tone="warning" icon={<AlertTriangle className="h-4 w-4" />} className="py-2.5">
          {MENU_STALE_LINE}
        </Alert>
      )}

      <div className={cn("grid gap-4", embedded ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-12")}>
        {/* Left: Floating White POS Dish Cards directly on #EAEFF5 canvas */}
        <div className={embedded ? "" : "lg:col-span-8"}>
          {menu.isPending ? (
            <div className="space-y-2">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-28 animate-pulse rounded-xl bg-white/70" />
                ))}
              </div>
              <p className="text-xs text-ink-muted">Đang tải danh mục món…</p>
            </div>
          ) : (
            <div
              className={cn(
                "grid gap-3",
                embedded
                  ? "grid-cols-1 sm:grid-cols-2"
                  : "grid-cols-1 sm:grid-cols-2 xl:grid-cols-3",
              )}
            >
              {shown.map((dish) => {
                const off = blocked(dish.status);
                const quantity = off ? 0 : (quantities[dish.dish_id] ?? 0);
                const picked = quantity > 0;
                const inputId = `dish-${branch}-${dish.dish_id}`;
                const descId = dish.status === "HET" ? `${inputId}-desc` : undefined;
                const isDrink = dish.dish_id.includes("TRA");

                return (
                  <div
                    key={dish.dish_id}
                    className={cn(
                      "group relative flex flex-col justify-between gap-3 rounded-xl border p-3.5 transition-all duration-150",
                      off
                        ? "border-slate-300/80 bg-slate-200/60 shadow-none"
                        : picked
                          ? "border-blue-600 bg-blue-50/85 shadow-sm ring-1 ring-blue-600/30"
                          : dish.status === "HET" && stale
                            ? "border-amber-400 bg-amber-50/90 shadow-[var(--shadow-card)] hover:border-amber-500"
                            : "border-line bg-surface shadow-[var(--shadow-card)] hover:border-line-strong",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 space-y-1">
                        <label
                          htmlFor={inputId}
                          className={cn(
                            "block text-sm font-semibold leading-snug",
                            off ? "cursor-not-allowed text-ink-muted" : "cursor-pointer text-ink",
                          )}
                        >
                          {dish.name}
                        </label>
                        {dish.status === "HET" && (
                          <span
                            id={descId}
                            className={cn(
                              "inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset",
                              stale
                                ? "bg-amber-100 text-amber-900 ring-amber-300"
                                : "bg-rose-100 text-rose-800 ring-rose-300",
                            )}
                          >
                            {stale ? DISH_STALE.HET : DISH_FRESH.HET}
                          </span>
                        )}
                      </div>
                      <span
                        aria-hidden="true"
                        className={cn(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
                          off
                            ? "bg-slate-300/70 text-slate-500"
                            : picked
                              ? "bg-blue-600 text-white"
                              : "bg-slate-100 text-slate-500 group-hover:bg-blue-50 group-hover:text-blue-700",
                        )}
                      >
                        {isDrink ? (
                          <CupSoda className="h-3.5 w-3.5" />
                        ) : (
                          <UtensilsCrossed className="h-3.5 w-3.5" />
                        )}
                      </span>
                    </div>

                    <div className="flex items-center justify-between gap-1.5 rounded-lg border border-line bg-subtle/80 px-1 py-1">
                      <button
                        type="button"
                        disabled={off || !picked}
                        onClick={() => set(dish.dish_id, quantity - 1)}
                        aria-label={`Bớt một ${dish.name}`}
                        className="flex h-7 w-7 items-center justify-center rounded-md text-ink-secondary transition-colors hover:bg-white hover:text-ink disabled:cursor-not-allowed disabled:opacity-35"
                      >
                        <Minus className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                      <input
                        id={inputId}
                        type="text"
                        inputMode="numeric"
                        disabled={off}
                        aria-describedby={descId}
                        placeholder="0"
                        value={off ? "" : quantity > 0 ? String(quantity) : ""}
                        onChange={(event) => {
                          const digits = event.currentTarget.value.replace(/\D/g, "");
                          set(dish.dish_id, digits ? Number.parseInt(digits, 10) : 0);
                        }}
                        className="w-12 bg-transparent text-center font-mono text-sm font-semibold text-ink tabular-nums placeholder:text-ink-muted focus:outline-none disabled:cursor-not-allowed"
                      />
                      <button
                        type="button"
                        disabled={off}
                        onClick={() => set(dish.dish_id, quantity + 1)}
                        aria-label={`Thêm một ${dish.name}`}
                        className="flex h-7 w-7 items-center justify-center rounded-md text-ink-secondary transition-colors hover:bg-blue-100 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-35"
                      >
                        <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Dark Slate-Navy Order Slip */}
        <div
          className={cn(
            "flex flex-col justify-between rounded-xl border border-slate-800 bg-[#0f172a] p-4 text-slate-100 shadow-md",
            embedded ? "" : "lg:col-span-4",
          )}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-2">
                <ReceiptText className="h-4 w-4 text-blue-400" aria-hidden="true" />
                <span className="text-xs font-semibold uppercase tracking-[0.06em] text-slate-300">
                  Phiếu đặt món
                </span>
              </div>
              {portions > 0 && (
                <span className="inline-flex items-center rounded-md bg-blue-500/20 px-2 py-0.5 text-xs font-semibold text-blue-300 ring-1 ring-inset ring-blue-400/35">
                  {portions} phần
                </span>
              )}
            </div>

            {items.length === 0 ? (
              <p className="py-7 text-center text-xs leading-relaxed text-slate-400">
                Chọn số lượng món để tạo đơn.
              </p>
            ) : (
              <ul className="space-y-2">
                {items.map((item) => (
                  <li
                    key={item.dish_id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-slate-700/80 bg-slate-800/75 px-3 py-2 text-sm"
                  >
                    <span className="min-w-0 truncate font-medium text-white">
                      {names.get(item.dish_id) ?? item.dish_id}
                    </span>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-blue-300 tabular-nums">
                        ×{item.quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() => set(item.dish_id, 0)}
                        aria-label={`Xóa ${names.get(item.dish_id) ?? item.dish_id}`}
                        className="rounded p-1 text-slate-400 hover:bg-rose-500/20 hover:text-rose-300"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {items.length > 0 && (
              <p className="text-xs text-slate-300">
                {`${portions} phần: ${items
                  .map((item) => `${names.get(item.dish_id) ?? item.dish_id} ×${item.quantity}`)
                  .join(", ")}`}
              </p>
            )}

            {refused && (
              <Alert tone="danger" title="Đơn không hợp lệ" className="py-2 text-xs">
                {refused}
              </Alert>
            )}
          </div>

          <div className="mt-4 flex items-center gap-2 border-t border-slate-800 pt-3">
            <button
              type="button"
              onClick={() => setQuantities({})}
              disabled={!items.length || place.isPending}
              className="inline-flex h-8 flex-1 cursor-pointer items-center justify-center rounded-lg border border-slate-700 bg-slate-800 px-3 text-xs font-semibold text-slate-200 transition-colors hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-45"
            >
              Xóa chọn
            </button>
            <button
              type="button"
              onClick={() => place.mutate()}
              disabled={!items.length || place.isPending}
              className="inline-flex h-8 flex-[1.6] cursor-pointer items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 text-xs font-semibold text-white shadow-xs transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:border disabled:border-slate-700 disabled:bg-slate-800/90 disabled:text-slate-300/80"
            >
              <Send className="h-3.5 w-3.5" aria-hidden="true" />
              Tạo đơn
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
