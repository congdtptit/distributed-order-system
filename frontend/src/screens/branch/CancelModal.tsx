// The cancel dialog of the branch screen: a mandatory reason from the customer-cancel group
// (sections 6 and 10 of the specification), then POST /orders/{id}/cancel. The branch decides
// whether the cancel is local (200) or goes to the Kitchen (202); the dialog only reports it.

import { Button, Group, Modal, Select, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { BranchId } from "../../api/branch";
import { branchApi } from "../../api/branch";
import { ApiError, detailMessage } from "../../api/http";
import { CANCEL_EXPLANATION, CUSTOMER_CANCEL_REASONS, REASON } from "../../labels";

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
      notifications.show(
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
        notifications.show({ color: "yellow", message: "Đơn vừa đổi trạng thái, đã tải lại" });
        reload();
        close();
      } else if (failure instanceof ApiError && failure.status === 404) {
        notifications.show({ color: "red", message: "Không tìm thấy đơn này ở chi nhánh" });
        reload();
        close();
      } else if (failure instanceof ApiError && failure.status === 400) {
        setError(detailMessage(failure.body) ?? "Lý do không hợp lệ");
      } else {
        notifications.show({
          color: "red",
          title: `Không kết nối được tới chi nhánh ${branch}`,
          message: (
            <Group gap="xs">
              <Text size="sm">Yêu cầu hủy chưa được ghi nhận.</Text>
              <Button size="compact-xs" variant="light" onClick={() => cancel.mutate(variables)}>
                Thử lại
              </Button>
            </Group>
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
    <Modal opened={orderId !== null} onClose={close} title={`Hủy đơn ${short}`} centered>
      <Stack gap="md">
        <Text size="sm">{CANCEL_EXPLANATION}</Text>
        <Select
          label="Lý do hủy"
          placeholder="Chọn lý do"
          withAsterisk
          data={CUSTOMER_CANCEL_REASONS.map((code) => ({ value: code, label: REASON[code] }))}
          value={reason}
          onChange={(value) => {
            setReason(value);
            setError(null);
          }}
          error={error}
          comboboxProps={{ withinPortal: false }}
        />
        <Group justify="space-between" mt="sm">
          <Button variant="default" onClick={close}>
            Đóng
          </Button>
          <Button color="red" onClick={confirm} loading={cancel.isPending}>
            Xác nhận hủy
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
