import {
  BarChartOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { Badge, Button, Layout, Menu, Space, Typography, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import {
  fetchInsight,
  fetchInsights,
  fetchOverview,
  fetchRuns,
  fetchTrends,
  InsightDetail,
  InsightPage,
  Overview,
  RunLog,
  Trends,
  triggerRun,
} from "./api";
import { Dashboard } from "./pages/Dashboard";
import { AgentSettings } from "./pages/AgentSettings";
import { InsightDetailView } from "./pages/InsightDetailView";
import { InsightLibrary } from "./pages/InsightLibrary";
import { RunLogs } from "./pages/RunLogs";
import { Filters } from "./types";

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

function App() {
  const [activeKey, setActiveKey] = useState("dashboard");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trends, setTrends] = useState<Trends | null>(null);
  const [runs, setRuns] = useState<RunLog[]>([]);
  const [insights, setInsights] = useState<InsightPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
  });
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    page: 1,
    page_size: 20,
    sort_by: "score",
  });
  const [selected, setSelected] = useState<InsightDetail | null>(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [overviewData, trendsData, runsData, insightData] =
        await Promise.all([
          fetchOverview(),
          fetchTrends(),
          fetchRuns(),
          fetchInsights(filters),
        ]);
      setOverview(overviewData);
      setTrends(trendsData);
      setRuns(runsData);
      setInsights(insightData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [filters]);

  const [triggering, setTriggering] = useState(false);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      const res = await triggerRun();
      message.success(res.message);
      loadAll();
    } catch (err: any) {
      if (err.response && err.response.status === 409) {
        message.warning(err.response?.data?.detail || "分析任务正在运行中，请勿重复触发");
      } else {
        message.error("触发分析任务失败，请检查网络或后台日志");
      }
    } finally {
      setTriggering(false);
    }
  };

  const latestRun = overview?.latest_run;

  useEffect(() => {
    let timer: any = null;
    if (latestRun?.status === "running") {
      timer = setInterval(() => {
        Promise.all([fetchOverview(), fetchRuns()])
          .then(([overviewData, runsData]) => {
            setOverview(overviewData);
            setRuns(runsData);
          })
          .catch((err) => console.error("Polling run status failed:", err));
      }, 5000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [latestRun?.status]);
  const languageData = useMemo(() => {
    const totals = new Map<string, number>();
    trends?.languages.forEach((item) => {
      totals.set(item.language, (totals.get(item.language) || 0) + item.count);
    });
    return Array.from(totals.entries()).map(([language, count]) => ({
      language,
      count,
    }));
  }, [trends]);

  const openInsight = async (id: number) => {
    setSelected(await fetchInsight(id));
  };

  return (
    <Layout className="app-shell">
      <Sider width={232} className="sidebar">
        <div className="brand">
          <div className="brand-mark">GI</div>
          <div>
            <strong>GitHub 洞察探员</strong>
            <span>系统控制台</span>
          </div>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[activeKey]}
          onClick={(item) => setActiveKey(item.key)}
          items={[
            { key: "dashboard", icon: <BarChartOutlined />, label: "数据大盘" },
            { key: "insights", icon: <DatabaseOutlined />, label: "开源洞察库" },
            { key: "runs", icon: <HistoryOutlined />, label: "任务日志" },
            { key: "settings", icon: <SettingOutlined />, label: "探员设置" },
          ]}
        />
      </Sider>
      <Layout>
        <Header className="topbar">
          <div>
            <Title level={4}>GitHub 开源智能洞察大盘</Title>
            <Text type="secondary">
              每日定时抓取热门项目，使用 LLM 深度阅读并挖掘其核心亮点与商业开发潜力
            </Text>
          </div>
          <Space>
            <Badge
              status={
                latestRun?.status === "success"
                  ? "success"
                  : latestRun?.status === "failed"
                    ? "error"
                    : "processing"
              }
            />
            <Text>
              {latestRun
                ? `最近分析运行：${dayjs(latestRun.started_at).format("YYYY-MM-DD HH:mm")}`
                : "暂无分析运行记录"}
            </Text>
            <Button onClick={loadAll}>同步刷新</Button>
            <Button
              type="primary"
              loading={triggering || latestRun?.status === "running"}
              onClick={handleTrigger}
            >
              {latestRun?.status === "running" ? "正在执行分析..." : "手动触发分析"}
            </Button>
          </Space>
        </Header>
        <Content className="content">
          {selected ? (
            <InsightDetailView insight={selected} onBack={() => setSelected(null)} />
          ) : (
            <>
              {activeKey === "dashboard" && (
                <Dashboard
                  overview={overview}
                  trends={trends}
                  languageData={languageData}
                  insights={insights.items}
                  loading={loading}
                  onOpen={openInsight}
                />
              )}
              {activeKey === "insights" && (
                <InsightLibrary
                  data={insights}
                  loading={loading}
                  filters={filters}
                  setFilters={setFilters}
                  onOpen={openInsight}
                  onChanged={loadAll}
                />
              )}
              {activeKey === "runs" && <RunLogs runs={runs} loading={loading} />}
              {activeKey === "settings" && <AgentSettings />}
            </>
          )}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
