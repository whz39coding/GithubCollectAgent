import { BulbOutlined, StarFilled, TrophyOutlined } from "@ant-design/icons";
import {
  Card,
  Col,
  Empty,
  Row,
  Space,
  Tag,
  Typography,
} from "antd";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Insight, Overview, Trends } from "../api";
import { Metric } from "../components/Metric";
import { LanguageDatum } from "../types";

const { Title, Text, Paragraph } = Typography;

// Reading this as: Web dashboard redesign for GitHub Insight Agent console, with a calm, high-end minimalist B2B SaaS vibe, leaning toward a refined typography, clean dark/light card-less UI, and restrained chart areas.
const DESIGN_VARIANCE = 6;
const MOTION_INTENSITY = 3;
const VISUAL_DENSITY = 5;

type DashboardProps = {
  overview: Overview | null;
  trends: Trends | null;
  languageData: LanguageDatum[];
  insights: Insight[];
  loading: boolean;
  onOpen: (id: number) => void;
};

export function Dashboard({
  overview,
  trends,
  languageData,
  insights,
  loading,
  onOpen,
}: DashboardProps) {
  return (
    <Space direction="vertical" size={24} className="full-width">
      <Row gutter={16}>
        <Metric title="总收录项目" value={overview?.total_projects || 0} />
        <Metric title="今日新收录" value={overview?.today_new || 0} />
        <Metric title="今日更新数" value={overview?.today_updated || 0} />
        <Metric title="探员平均评分" value={overview?.average_score || 0} suffix=" / 5" />
        <Metric title="缓存命中数" value={overview?.cache_hit_count || 0} />
      </Row>

      <section>
        <Title level={4} style={{ marginTop: 8, marginBottom: 16, color: "#0f172a" }}>
          🔥 今日精选：高分开源项目洞察报告
        </Title>
        {insights.length ? (
          <Row gutter={[24, 24]}>
            {insights.slice(0, 6).map((item) => (
              <Col xs={24} md={12} lg={8} key={item.id}>
                <Card
                  hoverable
                  onClick={() => onOpen(item.id)}
                  className="insight-list-card"
                  style={{
                    borderRadius: 12,
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    border: "1px solid #e2e8f0",
                  }}
                  bodyStyle={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    gap: 12,
                    padding: 20,
                  }}
                >
                  <div className="card-title-row">
                    <Title level={5} style={{ margin: 0, color: "#4f46e5" }} ellipsis>
                      {item.project_name}
                    </Title>
                    <Tag icon={<StarFilled />} color="gold" style={{ margin: 0, display: "flex", alignItems: "center", gap: 2 }}>
                      {item.score}
                    </Tag>
                  </div>

                  <Space wrap size={[0, 6]}>
                    <Tag color="cyan">{item.language}</Tag>
                    <Tag color="default">★ {item.stars}</Tag>
                    <Tag color="blue">{item.category}</Tag>
                  </Space>

                  <Paragraph ellipsis={{ rows: 2 }} className="muted-summary">
                    {item.summary || "暂无摘要内容..."}
                  </Paragraph>

                  {item.tech_stack && item.tech_stack.length > 0 && (
                    <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: 10, marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 6 }}>核心技术：</Text>
                      <Space wrap size={[0, 4]}>
                        {item.tech_stack.slice(0, 4).map((tech) => (
                          <Tag key={tech} bordered={false} style={{ background: "#f1f5f9", color: "#64748b", fontSize: 11, margin: 0 }}>
                            {tech}
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  )}

                  <div className="business-box">
                    <Text strong className="business-title">
                      <BulbOutlined /> 商业开发潜力：
                    </Text>
                    <Paragraph ellipsis={{ rows: 2 }} className="business-text">
                      {item.business_potential || "未分析"}
                    </Paragraph>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Card style={{ borderRadius: 12 }}>
            <Empty description="暂无精选项目报告" />
          </Card>
        )}
      </section>

      <section style={{ marginTop: 8 }}>
        <Title level={5} style={{ marginBottom: 16, color: "#64748b" }}>
          📊 数据概览与分析趋势
        </Title>
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={12}>
            <Card title="分析趋势追踪 (近 30 天)" loading={loading} style={{ borderRadius: 12 }} size="small">
              {trends?.daily.length ? (
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={trends.daily} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Line type="monotone" dataKey="new_count" name="新收录" stroke="#4f46e5" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
                    <Line type="monotone" dataKey="updated_count" name="信息更新" stroke="#10b981" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Empty />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="收录语言分布" loading={loading} style={{ borderRadius: 12 }} size="small">
              {languageData.length ? (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={languageData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="language" axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#f8fafc" }} />
                    <Bar dataKey="count" name="项目数量" fill="#6366f1" radius={[3, 3, 0, 0]} maxBarSize={30} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Empty />
              )}
            </Card>
          </Col>
        </Row>
      </section>
    </Space>
  );
}

const tooltipStyle = {
  borderRadius: 8,
  border: "none",
  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
};
