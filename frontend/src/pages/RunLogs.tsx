import { Card, Table, Tag } from "antd";
import dayjs from "dayjs";
import { RunLog } from "../api";

type RunLogsProps = {
  runs: RunLog[];
  loading: boolean;
};

export function RunLogs({ runs, loading }: RunLogsProps) {
  return (
    <Card title="定时任务运行记录">
      <Table
        rowKey="id"
        loading={loading}
        dataSource={runs}
        columns={[
          {
            title: "状态",
            dataIndex: "status",
            render: (value) => (
              <Tag color={value === "success" ? "green" : value === "failed" ? "red" : "blue"}>
                {value}
              </Tag>
            ),
          },
          {
            title: "开始时间",
            dataIndex: "started_at",
            render: (value) => dayjs(value).format("YYYY-MM-DD HH:mm"),
          },
          { title: "抓取", dataIndex: "fetched_count" },
          { title: "处理", dataIndex: "processed_count" },
          { title: "新增", dataIndex: "new_count" },
          { title: "更新", dataIndex: "updated_count" },
          { title: "LLM", dataIndex: "llm_call_count" },
          { title: "缓存", dataIndex: "cache_hit_count" },
          { title: "失败", dataIndex: "failed_count" },
          {
            title: "错误摘要",
            dataIndex: "error_summary",
            render: (value) => value || "-",
          },
        ]}
      />
    </Card>
  );
}
