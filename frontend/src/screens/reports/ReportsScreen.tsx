// The Management screen: chain-wide figures from Central Order Replica (GET /reports/summary).
// Read-only: zero <button> elements inside <main>.

import { useQuery } from "@tanstack/react-query";
import { Clock, Info } from "lucide-react";
import type { BranchSummary } from "../../api/reports";
import { reportsApi } from "../../api/reports";
import { clock, duration, ServiceBanner, TABULAR } from "../../components/common";
import { RatioBar, StackedBar } from "../../components/DataBar";
import { ORDER_STATUS, reasonLabel } from "../../labels";
import {
  Card,
  cn,
  Panel,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableFoot,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "../../ui";

const STATUSES = ["CHO_KHO", "DA_GIU", "HOAN_TAT", "DA_HUY", "THAT_BAI"] as const;

const STATUS_BAR_COLORS: Record<(typeof STATUSES)[number], { dot: string; bar: string }> = {
  CHO_KHO: { dot: "bg-slate-400", bar: "bg-slate-400" },
  DA_GIU: { dot: "bg-blue-600", bar: "bg-blue-600" },
  HOAN_TAT: { dot: "bg-emerald-500", bar: "bg-emerald-500" },
  DA_HUY: { dot: "bg-slate-700", bar: "bg-slate-700" },
  THAT_BAI: { dot: "bg-rose-500", bar: "bg-rose-500" },
};

export function ReportsScreen() {
  const report = useQuery({ queryKey: ["reports", "summary"], queryFn: reportsApi.summary });
  const branches = report.data?.branches ?? [];
  const sum = (pick: (b: BranchSummary) => number) => branches.reduce((n, b) => n + pick(b), 0);
  const total = sum((b) => b.total);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-[-0.02em] text-ink">Quản lý</h1>
        {report.data?.generated_at && (
          <span
            className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1 font-mono text-xs text-ink-secondary"
            style={TABULAR}
          >
            <Clock className="h-3.5 w-3.5 text-ink-muted" aria-hidden="true" />
            Tổng hợp lúc {clock(report.data.generated_at)}
          </span>
        )}
      </div>

      {report.isError && <ServiceBanner service="Báo cáo" lastAnswer={report.dataUpdatedAt} />}

      {report.isPending && !report.isError ? (
        <div className="flex justify-center py-12">
          <Spinner size="md" label="Đang tải" />
        </div>
      ) : (
        <>
          {/* Chain Overview + Distribution Bar */}
          <Card className="space-y-3 p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-4">
              <div>
                <p className="text-xs font-medium text-ink-muted">Tổng toàn chuỗi</p>
                <p className="font-mono text-2xl font-bold tracking-tight text-ink" style={TABULAR}>
                  {total}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2" style={TABULAR}>
                {STATUSES.map((s) => (
                  <div key={s} className="flex items-center gap-1.5 text-xs">
                    <span
                      className={cn("h-2 w-2 rounded-full", STATUS_BAR_COLORS[s].dot)}
                      aria-hidden="true"
                    />
                    <span className="text-ink-secondary">{ORDER_STATUS[s].label}:</span>
                    <span className="font-mono font-semibold text-ink">
                      {sum((b) => b.by_status[s])}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <StackedBar
              className="h-2.5"
              segments={STATUSES.map((s) => ({
                key: s,
                label: ORDER_STATUS[s].label,
                value: sum((b) => b.by_status[s]),
                colorClass: STATUS_BAR_COLORS[s].bar,
              }))}
            />
          </Card>

          <Panel title="Đơn theo trạng thái" label="Bảng đơn theo trạng thái" flush>
            <StatusTable branches={branches} />
          </Panel>

          <div className="space-y-3">
            <h2 className="text-sm font-semibold tracking-[-0.01em] text-ink">
              Lý do hủy và thất bại
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {branches.map((b) => (
                <Reasons key={b.branch_id} branch={b} />
              ))}
            </div>
          </div>

          <div className="flex items-start gap-2 rounded-xl border border-line bg-subtle px-3.5 py-2.5 text-xs text-ink-secondary">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-muted" aria-hidden="true" />
            <p>
              Số liệu lấy từ bản sao trung tâm nên có thể chậm hơn dữ liệu ở chi nhánh: mỗi chi
              nhánh có mốc "dữ liệu tính đến" riêng. Chỉ trạng thái đơn ở chi nhánh được tính; yêu
              cầu hủy đang chờ ở Bếp không được tính.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function asOf(branch: BranchSummary): string {
  if (branch.data_as_of === null) return "Chưa có dữ liệu";
  return `${clock(branch.data_as_of)} (cách đây ${duration(branch.data_age_s ?? 0)})`;
}

function StatusTable({ branches }: { branches: BranchSummary[] }) {
  const chain = STATUSES.map((s) => branches.reduce((sum, b) => sum + b.by_status[s], 0));
  const total = branches.reduce((sum, b) => sum + b.total, 0);

  return (
    <TableContainer>
      <Table aria-label="Đơn theo trạng thái" className="min-w-[720px]" style={TABULAR}>
        <TableHead>
          <TableRow className="hover:bg-transparent">
            <TableHeaderCell>Chi nhánh</TableHeaderCell>
            <TableHeaderCell>Dữ liệu tính đến</TableHeaderCell>
            {STATUSES.map((s) => (
              <TableHeaderCell key={s} className="text-right">
                {ORDER_STATUS[s].label}
              </TableHeaderCell>
            ))}
            <TableHeaderCell className="text-right">Tổng</TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {branches.map((b) => {
            const age = b.data_age_s;
            const dotColor =
              b.data_as_of === null
                ? "bg-slate-300"
                : age !== null && age > 30
                  ? "bg-amber-500"
                  : "bg-emerald-500";
            return (
              <TableRow key={b.branch_id}>
                <th
                  scope="row"
                  className="px-4 py-3 text-left text-sm font-semibold text-ink whitespace-nowrap"
                >
                  {b.branch_id}
                </th>
                <TableCell>
                  <span className="inline-flex items-center gap-2 text-xs">
                    <span
                      className={cn("h-2 w-2 shrink-0 rounded-full", dotColor)}
                      aria-hidden="true"
                    />
                    <span
                      className={b.data_as_of === null ? "text-ink-muted" : "text-ink-secondary"}
                    >
                      {asOf(b)}
                    </span>
                  </span>
                </TableCell>
                {STATUSES.map((s) => (
                  <TableCell key={s} className="text-right font-mono text-xs">
                    {b.by_status[s]}
                  </TableCell>
                ))}
                <TableCell className="text-right font-mono text-xs font-semibold">
                  {b.total}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
        <TableFoot>
          <TableRow className="hover:bg-transparent">
            <th scope="row" className="px-4 py-3 text-left text-sm font-bold text-ink">
              Toàn chuỗi
            </th>
            <TableCell />
            {chain.map((n, i) => (
              <TableCell key={STATUSES[i]} className="text-right font-mono text-xs font-semibold">
                {n}
              </TableCell>
            ))}
            <TableCell className="text-right font-mono text-xs font-bold">{total}</TableCell>
          </TableRow>
        </TableFoot>
      </Table>
    </TableContainer>
  );
}

function Reasons({ branch }: { branch: BranchSummary }) {
  const title = `Lý do ở ${branch.branch_id}`;
  const max = branch.reasons.reduce((m, r) => Math.max(m, r.count), 0);

  return (
    <Card as="section" aria-label={title} className="p-4">
      <h3 className="mb-3 text-sm font-semibold text-ink">{branch.branch_id}</h3>
      {branch.reasons.length === 0 ? (
        <p className="text-xs text-ink-muted">Chưa có đơn nào bị hủy hay thất bại.</p>
      ) : (
        <table className="w-full border-collapse text-sm" style={TABULAR}>
          <tbody className="divide-y divide-line">
            {branch.reasons.map((r) => {
              const isFailed = r.status === "THAT_BAI";
              return (
                <tr key={`${r.status}-${r.reason_code ?? ""}`}>
                  <td className="py-2 pr-3">
                    <div className="space-y-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="text-xs font-medium text-ink">
                          {reasonLabel(r.reason_code) ?? "Không ghi lý do"}
                        </span>
                        <span className="text-[11px] text-ink-muted">
                          {ORDER_STATUS[r.status as "DA_HUY" | "THAT_BAI"]?.label ?? r.status}
                        </span>
                      </div>
                      <RatioBar
                        value={r.count}
                        max={max}
                        colorClass={isFailed ? "bg-rose-500" : "bg-slate-700"}
                      />
                    </div>
                  </td>
                  <td className="py-2 text-right align-top font-mono text-xs font-semibold text-ink">
                    {r.count}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Card>
  );
}
