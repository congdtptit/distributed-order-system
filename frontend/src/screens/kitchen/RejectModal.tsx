// The reject dialog (Flow A, section 5 of the specification): a reason from the
// Kitchen-rejection group of section 10; for "Spoiled ingredient", at least one ingredient of
// this ticket's reserved list. The Kitchen checks both again and answers 400 if it refuses.

import { Button, Checkbox, Group, Modal, Select, Stack, Text } from "@mantine/core";
import { useState } from "react";
import type { Ticket } from "../../api/kitchen";
import { KITCHEN_REJECTION_REASONS, REASON } from "../../labels";

export function RejectModal({
  ticket,
  pending,
  refused,
  onConfirm,
  onClose,
}: {
  ticket: Ticket | null;
  pending: boolean;
  /** The Kitchen's 400 message, shown in the dialog. */
  refused: string | null;
  onConfirm: (reason: string, spoiled: string[]) => void;
  onClose: () => void;
}) {
  const [reason, setReason] = useState<string | null>(null);
  const [spoiled, setSpoiled] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const short = ticket?.order_id.slice(0, 8) ?? "";
  const needsIngredient = reason === "SPOILED_INGREDIENT";

  const close = () => {
    setReason(null);
    setSpoiled([]);
    setError(null);
    onClose();
  };

  const confirm = () => {
    if (!reason) {
      setError("Chọn lý do từ chối");
      return;
    }
    if (needsIngredient && spoiled.length === 0) {
      setError("Chọn nguyên liệu bị hỏng");
      return;
    }
    setError(null);
    onConfirm(reason, needsIngredient ? spoiled : []);
  };

  return (
    <Modal opened={ticket !== null} onClose={close} title={`Từ chối phiếu ${short}`} centered>
      <Stack gap="md">
        <Text size="sm">
          Phiếu bị từ chối thì đơn chuyển sang Đã hủy ngay ở chi nhánh, và Kho nhận lệnh hoàn kho
          theo lý do: nguyên liệu hỏng thì ghi hao hụt và chặn nguyên liệu đó tới khi kiểm kho.
        </Text>
        <Select
          label="Lý do từ chối"
          placeholder="Chọn lý do"
          withAsterisk
          data={KITCHEN_REJECTION_REASONS.map((code) => ({ value: code, label: REASON[code] }))}
          value={reason}
          onChange={(value) => {
            setReason(value);
            setError(null);
          }}
          error={!needsIngredient ? error : null}
          comboboxProps={{ withinPortal: false }}
        />
        {needsIngredient && ticket && (
          <Checkbox.Group
            label="Nguyên liệu bị hỏng"
            withAsterisk
            value={spoiled}
            onChange={(value) => {
              setSpoiled(value);
              setError(null);
            }}
            error={error}
          >
            <Stack gap="xs" mt="xs">
              {ticket.reserved.map((line) => (
                <Checkbox
                  key={line.ingredient_id}
                  value={line.ingredient_id}
                  label={line.name ?? line.ingredient_id}
                />
              ))}
            </Stack>
          </Checkbox.Group>
        )}
        {refused && (
          <Text size="sm" c="red.8" role="alert">
            Bếp không nhận lựa chọn này: {refused}
          </Text>
        )}
        <Group justify="space-between" mt="sm">
          <Button variant="default" onClick={close} size="md">
            Đóng
          </Button>
          <Button color="red" onClick={confirm} loading={pending} size="md">
            Xác nhận từ chối
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
