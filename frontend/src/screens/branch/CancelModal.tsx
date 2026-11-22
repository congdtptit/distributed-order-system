// The cancel dialog of the branch screen: a mandatory reason from the customer-cancel group
// (sections 6 and 10 of the specification), then POST /orders/{id}/cancel. The branch decides
// whether the cancel is local (200) or goes to the Kitchen (202); the dialog only reports it.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { BranchId } from "../../api/branch";
import { branchApi } from "../../api/branch";
import { ApiError, detailMessage } from "../../api/http";
import { CANCEL_EXPLANATION, CUSTOMER_CANCEL_REASONS, REASON } from "../../labels";
import { Button, Dialog, Select, toast } from "../../ui";

export function CancelModal({
  branch,
  orderId,
  onClose,
}: {
  branch: BranchId;
  orderId: string | null;
  onClose: () => void;
}) {
  const [reason, setReason] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const client = useQueryClient();
  const api = branchApi(branch);
  const short = orderId?.slice(0, 8) ?? "";

  const reload = () => client.invalidateQueries({ queryKey: ["branch", branch] });
  const close = () => {
    setReason(null);
    setError(null);
    onClose();
  };

  const cancel = useMutation({
    mutationFn: ({ id, code }: { id: string; code: string }) => api.cancel(id, code),
    onSuccess: ({ status }) => {
      toast.show(
        status === 200
          ? { color: "green", message: `Đã hủy đơn ${short} tại chi nhánh` }
          : {
              color: "blue",
              message: `Đã gửi yêu cầu hủy đơn ${short} tới Bếp. Bếp quyết định: chưa chắc hủy được.`,
            },
      );
      reload();
      close();
    },
    onError: (failure, variables) => {
      if (failure instanceof ApiError && failure.status === 409) {
        toast.show({ color: "yellow", message: "Đơn vừa đổi trạng thái, đã tải lại" });
        reload();
        close();
      } else if (failure instanceof ApiError && failure.status === 404) {
        toast.show({ color: "red", message: "Không tìm thấy đơn này ở chi nhánh" });
        reload();
        close();
      } else if (failure instanceof ApiError && failure.status === 400) {
        setError(detailMessage(failure.body) ?? "Lý do không hợp lệ");
      } else {
        toast.show({
          color: "red",
          title: `Không kết nối được tới chi nhánh ${branch}`,
          message: (
            <div className="mt-1 flex items-center gap-2">
              <span>Yêu cầu hủy chưa được ghi nhận.</span>
              <Button size="xs" variant="danger-soft" onClick={() => cancel.mutate(variables)}>
                Thử lại
              </Button>
            </div>
          ),
        });
      }
    },
  });

  const confirm = () => {
    if (!orderId) return;
    if (!reason) {
      setError("Chọn lý do hủy");
      return;
    }
    cancel.mutate({ id: orderId, code: reason });
  };

  return (
    <Dialog
      open={orderId !== null}
      onOpenChange={(open) => {
        if (!open) close();
      }}
      title={`Hủy đơn ${short}`}
    >
      <div className="space-y-4">
        <p className="rounded-lg bg-subtle px-3 py-2.5 text-sm leading-relaxed text-ink-secondary">
          {CANCEL_EXPLANATION}
        </p>
        <Select
          label="Lý do hủy"
          placeholder="Chọn lý do"
          required
          options={CUSTOMER_CANCEL_REASONS.map((code) => ({ value: code, label: REASON[code] }))}
          value={reason}
          onValueChange={(value) => {
            setReason(value);
            setError(null);
          }}
          error={error}
        />
        <div className="flex items-center justify-between pt-2">
          <Button variant="secondary" onClick={close}>
            Đóng
          </Button>
          <Button variant="danger" onClick={confirm} loading={cancel.isPending}>
            Xác nhận hủy
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
