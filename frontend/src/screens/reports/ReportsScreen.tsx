// The Management screen: chain-wide figures from the Central Order Replica, which may lag behind
// the branches (section 8 of the specification, the Management row and the paragraph below it).
// Each branch shows its own "data as of" time; a branch whose replication is cut keeps an old
// time that grows older while the others stay current (scenario 55). The screen reads one API,
// GET /reports/summary, and changes nothing. Specified in
// .claude/skills/screen/references/screens.md ("reports").

import { Card, Center, Loader, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";
import { IconAlertTriangle, IconBan, IconCircleCheck, IconReceipt } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import type { BranchSummary } from "../../api/reports";
import { reportsApi } from "../../api/reports";
import { clock, duration, ServiceBanner, TABULAR } from "../../components/common";
import { Figures, PageHeader, Panel } from "../../components/layout";
import { ORDER_STATUS, reasonLabel } from "../../labels";

const STATUSES = ["CHO_KHO", "DA_GIU", "HOAN_TAT", "DA_HUY", "THAT_BAI"] as const;

export function ReportsScreen() {
  const report = useQuery({ queryKey: ["reports", "summary"], queryFn: reportsApi.summary });
  const branches = report.data?.branches ?? [];
  const sum = (pick: (b: BranchSummary) => number) => branches.reduce((n, b) => n + pick(b), 0);

  return (
    <Stack gap="lg">
      <PageHeader
        title="Quản lý"
        description={
          'Số liệu lấy từ bản sao trung tâm nên có thể chậm hơn dữ liệu ở chi nhánh: mỗi chi nhánh có mốc "dữ liệu tính đến" riêng. Chỉ trạng thái đơn ở chi nhánh được tính; yêu cầu hủy đang chờ ở Bếp không được tính.'
        }
      />
      {report.isError && <ServiceBanner service="Báo cáo" lastAnswer={report.dataUpdatedAt} />}
      {report.isPending && !report.isError ? (
        <Center py="xl">
          <Loader aria-label="Đang tải" />
        </Center>
      ) : (
        <>
          <Figures
            figures={[
              {
                label: "Tổng số đơn toàn chuỗi",
                value: sum((b) => b.total),
                icon: IconReceipt,
                color: "indigo",
              },
              {
                label: "Đơn đã hoàn tất",
                value: sum((b) => b.by_status.HOAN_TAT),
                icon: IconCircleCheck,
                color: "green",
              },
              {
                label: "Đơn bị hủy",
                value: sum((b) => b.by_status.DA_HUY),
                icon: IconBan,
                color: "gray",
              },
              {
                label: "Đơn thất bại",
                value: sum((b) => b.by_status.THAT_BAI),
                icon: IconAlertTriangle,
                color: "red",
              },
            ]}
          />
          <Panel title="Đơn theo trạng thái" label="Bảng đơn theo trạng thái" flush>
            <StatusTable branches={branches} />
          </Panel>
          <Stack gap="sm">
            <Title order={2} size="h4">
              Lý do hủy và thất bại
            </Title>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
              {branches.map((b) => (
                <Reasons key={b.branch_id} branch={b} />
              ))}
            </SimpleGrid>
          </Stack>
        </>
      )}
    </Stack>
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
    <Table.ScrollContainer minWidth={720}>
      <Table aria-label="Đơn theo trạng thái" style={TABULAR}>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Chi nhánh</Table.Th>
            <Table.Th>Dữ liệu tính đến</Table.Th>
            {STATUSES.map((s) => (
              <Table.Th key={s} ta="right">
                {ORDER_STATUS[s].label}
              </Table.Th>
            ))}
            <Table.Th ta="right">Tổng</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {branches.map((b) => (
            <Table.Tr key={b.branch_id}>
              <Table.Th scope="row" fz="sm" c="dark" fw={600}>
                {b.branch_id}
              </Table.Th>
              <Table.Td>
                <Text size="sm" c={b.data_as_of === null ? "dimmed" : "dark"}>
                  {asOf(b)}
                </Text>
              </Table.Td>
              {STATUSES.map((s) => (
                <Table.Td key={s} ta="right">
                  {b.by_status[s]}
                </Table.Td>
              ))}
              <Table.Td ta="right" fw={600}>
                {b.total}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
        <Table.Tfoot>
          <Table.Tr bg="gray.0" style={{ borderTop: "2px solid var(--mantine-color-gray-3)" }}>
            <Table.Th scope="row" fz="sm" c="dark" fw={700}>
              Toàn chuỗi
            </Table.Th>
            <Table.Td />
            {chain.map((n, i) => (
              <Table.Td key={STATUSES[i]} ta="right" fw={600}>
                {n}
              </Table.Td>
            ))}
            <Table.Td ta="right" fw={600}>
              {total}
            </Table.Td>
          </Table.Tr>
        </Table.Tfoot>
      </Table>
    </Table.ScrollContainer>
  );
}

function Reasons({ branch }: { branch: BranchSummary }) {
  const title = `Lý do ở ${branch.branch_id}`;
  return (
    <Card padding="md" component="section" aria-label={title}>
      <Title order={3} size="h4" mb="xs">
        {branch.branch_id}
      </Title>
      {branch.reasons.length === 0 ? (
        <Text size="sm" c="dimmed">
          Chưa có đơn nào bị hủy hay thất bại.
        </Text>
      ) : (
        <Table verticalSpacing={4} style={TABULAR}>
          <Table.Tbody>
            {branch.reasons.map((r) => (
              <Table.Tr key={`${r.status}-${r.reason_code ?? ""}`}>
                <Table.Td>
                  <Text size="sm">{reasonLabel(r.reason_code) ?? "Không ghi lý do"}</Text>
                  <Text size="xs" c="dimmed">
                    {ORDER_STATUS[r.status as "DA_HUY" | "THAT_BAI"]?.label ?? r.status}
                  </Text>
                </Table.Td>
                <Table.Td ta="right" fw={600}>
                  {r.count}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Card>
  );
}
