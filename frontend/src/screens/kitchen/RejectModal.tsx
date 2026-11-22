// The reject dialog (Flow A, section 5 of the specification): a reason from the
// Kitchen-rejection group of section 10; for "Spoiled ingredient", at least one ingredient of
// this ticket's reserved list. The Kitchen checks both again and answers 400 if it refuses.

import { useState } from "react";
import type { Ticket } from "../../api/kitchen";
import { KITCHEN_REJECTION_REASONS, REASON } from "../../labels";
import { Alert, Button, Checkbox, Dialog, Select } from "../../ui";

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

  const toggleIngredient = (id: string, checked: boolean) => {
    setSpoiled((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)));
    setError(null);
  };

  return (
    <Dialog
      open={ticket !== null}
      onOpenChange={(open) => {
        if (!open) close();
      }}
      title={`Từ chối phiếu ${short}`}
    >
      <div className="space-y-4">
        <p className="rounded-lg bg-subtle px-3 py-2.5 text-sm leading-relaxed text-ink-secondary">
          Phiếu bị từ chối thì đơn chuyển sang Đã hủy ngay ở chi nhánh, và Kho nhận lệnh hoàn kho
          theo lý do: nguyên liệu hỏng thì ghi hao hụt và chặn nguyên liệu đó tới khi kiểm kho.
        </p>

        <Select
          label="Lý do từ chối"
          placeholder="Chọn lý do"
          required
          options={KITCHEN_REJECTION_REASONS.map((code) => ({ value: code, label: REASON[code] }))}
          value={reason}
          onValueChange={(value) => {
            setReason(value);
            setError(null);
          }}
          error={!needsIngredient ? error : null}
        />

        {needsIngredient && ticket && (
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-ink">
              Nguyên liệu bị hỏng<span className="ml-0.5 text-rose-600">*</span>
            </legend>
            <div className="space-y-1.5">
              {ticket.reserved.map((line) => (
                <Checkbox
                  key={line.ingredient_id}
                  label={line.name ?? line.ingredient_id}
                  checked={spoiled.includes(line.ingredient_id)}
                  onCheckedChange={(checked) => toggleIngredient(line.ingredient_id, checked)}
                />
              ))}
            </div>
            {error && <p className="text-xs font-medium text-rose-700">{error}</p>}
          </fieldset>
        )}

        {refused && (
          <Alert tone="danger" role="alert" className="py-2 text-xs">
            Bếp không nhận lựa chọn này: {refused}
          </Alert>
        )}

        <div className="flex items-center justify-between pt-2">
          <Button variant="secondary" size="md" onClick={close}>
            Đóng
          </Button>
          <Button variant="danger" size="md" onClick={confirm} loading={pending}>
            Xác nhận từ chối
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
