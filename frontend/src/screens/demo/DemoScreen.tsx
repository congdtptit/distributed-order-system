// The demo page: a branch and the Kitchen side by side, so that a race (scenario 3) or a cancel
// that reaches the Kitchen before the order (scenario 1) can be shown live. It reuses the two
// screens and keeps no state of its own; the guide below is fixed text from section 12 of the
// specification. Specified in .claude/skills/screen/references/screens.md ("demo").

import { Accordion, Badge, Code, Grid, Group, List, Paper, Stack, Text } from "@mantine/core";
import { IconTerminal2 } from "@tabler/icons-react";
import { useParams } from "react-router";
import { isBranch } from "../../api/branch";
import { PageHeader, Panel } from "../../components/layout";
import { BranchPanel } from "../branch/BranchScreen";
import { KitchenScreen } from "../kitchen/KitchenScreen";

export function DemoScreen() {
  const { branchId } = useParams();
  if (!isBranch(branchId)) {
    return <Text>Không có chi nhánh {branchId}.</Text>;
  }
  return (
    <Stack gap="lg">
      <PageHeader
        title="Demo"
        description="Chi nhánh và Bếp đặt cạnh nhau để trình diễn các kịch bản tranh chấp và mất mạng. Mở một kịch bản để xem các bước."
      />
      <Guide branch={branchId.toLowerCase()} />
      <Grid gap="lg">
        <Grid.Col span={{ base: 12, lg: 6 }} style={{ minWidth: 0 }}>
          <Paper p="md" bg="gray.0" shadow="none">
            <BranchPanel key={branchId} branch={branchId} embedded />
          </Paper>
        </Grid.Col>
        <Grid.Col span={{ base: 12, lg: 6 }} style={{ minWidth: 0 }}>
          <Paper p="md" bg="gray.0" shadow="none">
            <KitchenScreen embedded />
          </Paper>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

interface Scenario {
  n: number;
  title: string;
  steps: string[];
  expected: string;
}

function scenarios(branch: string): Scenario[] {
  return [
    {
      n: 1,
      title: "Yêu cầu hủy tới Bếp trước đơn",
      steps: [
        "Tắt Kho: bin/chaos stop inventory-1 (và inventory-2 nếu chạy profile full).",
        "Tạo đơn ở chi nhánh, chờ dòng gửi đi báo đã gửi, rồi bấm Hủy đơn.",
        'Chi nhánh hiện "Bếp sẽ không nấu". Bật lại Kho: bin/chaos start inventory-1.',
      ],
      expected: "Không có phiếu nào; đơn chuyển Đã hủy; Kho hoàn kho đúng một lần.",
    },
    {
      n: 3,
      title: "Hủy và Bắt đầu nấu cùng lúc",
      steps: [
        "Tạo đơn, chờ đơn Đã giữ và phiếu hiện ở cột Chờ nấu.",
        "Bấm Hủy đơn ở chi nhánh và Bắt đầu nấu ở Bếp gần như cùng lúc: yêu cầu hủy còn phải đi qua Kafka, nên thường Bắt đầu nấu thắng.",
        "Làm lại với đơn mới: bấm Hủy đơn trước, khoảng nửa giây sau mới bấm Bắt đầu nấu, để thấy hủy thắng.",
      ],
      expected:
        'Mỗi lần đúng một thao tác thắng; chi nhánh, Bếp và Kho cùng một kết cục (Đã hủy, hoặc "Không hủy được: bếp đã bắt đầu nấu"); bên thua nhận "Phiếu vừa đổi trạng thái".',
    },
    {
      n: 4,
      title: "Bếp từ chối phiếu khi Kho đang tắt",
      steps: [
        "Tạo đơn, chờ phiếu ở cột Chờ nấu. Tắt Kho: bin/chaos stop inventory-1.",
        "Từ chối phiếu ở Bếp. Bật lại Kho: bin/chaos start inventory-1.",
      ],
      expected: "Chi nhánh thấy Đã hủy ngay; Kho hoàn kho đúng một lần khi bật lại (xem màn Kho).",
    },
    {
      n: 10,
      title: "Mất mạng, tạo đơn rồi hủy (đơn chưa từng gửi)",
      steps: [
        `Cắt mạng chi nhánh: bin/chaos offline ${branch}; chờ thanh trên báo mất kết nối Kafka.`,
        "Tạo đơn (dòng gửi đi báo chưa gửi), rồi bấm Hủy đơn.",
        'Chờ khoảng 1 phút (chế độ demo của bin/demo): form đặt món hiện "Tình trạng món có thể đã thay đổi", món Hết đổi thành "Có thể đã hết" và vẫn đặt được.',
        `Nối mạng lại: bin/chaos online ${branch}.`,
      ],
      expected:
        "Đơn Đã hủy ngay tại chi nhánh; không gì được gửi; Kho và Bếp không có bản ghi; đơn không bao giờ được nấu. Có mạng lại thì chi nhánh lấy lại tình trạng món và món Hết lại bị khóa.",
    },
    {
      n: 36,
      title: "Mất mạng sau khi đã gửi đơn, Bếp nấu trước khi yêu cầu hủy tới",
      steps: [
        "Tạo đơn, chờ đơn Đã giữ.",
        `Cắt mạng chi nhánh: bin/chaos offline ${branch}; bấm Hủy đơn (Đang yêu cầu hủy).`,
        `Bấm Bắt đầu nấu ở Bếp, rồi nối mạng lại: bin/chaos online ${branch}. Bấm Hoàn tất.`,
      ],
      expected:
        'Chi nhánh hiện "Không hủy được: bếp đã bắt đầu nấu"; đơn đi tiếp tới Hoàn tất; nguyên liệu không được hoàn kho. Đi cặp với kịch bản 10: đó là ranh giới của cam kết khi hủy lúc mất mạng.',
    },
  ];
}

function Guide({ branch }: { branch: string }) {
  return (
    <Panel title="Kịch bản demo" flush>
      <Accordion chevronPosition="left">
        {scenarios(branch).map((s) => (
          <Accordion.Item key={s.n} value={String(s.n)}>
            <Accordion.Control>
              <Group gap="sm" wrap="nowrap">
                <Badge variant="filled" color="indigo" w={44} style={{ flex: "none" }}>
                  {s.n}
                </Badge>
                <Text size="sm">
                  <Text span fw={600}>{`Kịch bản ${s.n}`}</Text>
                  <Text span> · {s.title}</Text>
                </Text>
              </Group>
            </Accordion.Control>
            <Accordion.Panel>
              <List type="ordered" size="sm" spacing={6}>
                {s.steps.map((step) => (
                  <List.Item key={step}>
                    <Command text={step} />
                  </List.Item>
                ))}
              </List>
              <Paper mt="sm" p="sm" bg="green.0" shadow="none" withBorder={false}>
                <Text size="sm">
                  <Text span fw={600} c="green.9">
                    Kết quả mong đợi:
                  </Text>{" "}
                  {s.expected}
                </Text>
              </Paper>
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>
    </Panel>
  );
}

/** A step with its ``bin/chaos`` command set in code type. */
function Command({ text }: { text: string }) {
  const parts = text.split(/(bin\/chaos [a-z]+ [a-z0-9-]+)/).filter(Boolean);
  return (
    <>
      {parts.map((part) =>
        part.startsWith("bin/chaos") ? (
          <Code key={part} fz="xs">
            <IconTerminal2 size={12} aria-hidden style={{ verticalAlign: -2, marginRight: 4 }} />
            {part}
          </Code>
        ) : (
          part
        ),
      )}
    </>
  );
}
