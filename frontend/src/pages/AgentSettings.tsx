import { Button, Card, Form, Input, InputNumber, Select, Space, Switch, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { AgentConfig, fetchAgentConfig, updateAgentConfig } from "../api";

const { TextArea } = Input;
const { Title, Text } = Typography;

export function AgentSettings() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<AgentConfig>({ env: {}, prompt: "" });

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await fetchAgentConfig();
      setConfig(data);
      form.setFieldsValue({
        ...data.env,
        SEND_MESSAGE: data.env.SEND_MESSAGE === "true",
        CHECK_GITHUB_API: data.env.CHECK_GITHUB_API === "true",
        SAVE_README: data.env.SAVE_README === "true",
        ANALYSIS_NUM: Number(data.env.ANALYSIS_NUM || 5),
        README_MAX_LENGTH: Number(data.env.README_MAX_LENGTH || 20000),
        prompt: data.prompt,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const submit = async () => {
    const values = await form.validateFields();
    const env = {
      ...config.env,
      SEND_MESSAGE: String(Boolean(values.SEND_MESSAGE)),
      CHECK_GITHUB_API: String(Boolean(values.CHECK_GITHUB_API)),
      GITHUB_TOKEN: values.GITHUB_TOKEN || "",
      LLM_API_KEY: values.LLM_API_KEY || "",
      LLM_BASE_URL: values.LLM_BASE_URL || "",
      LLM_MODEL: values.LLM_MODEL || "",
      FEISHU_WEBHOOK: values.FEISHU_WEBHOOK || "",
      NOTIFIER_WEBHOOK: values.NOTIFIER_WEBHOOK || "",
      TRENDING_LANGUAGE: values.TRENDING_LANGUAGE || "python",
      TRENDING_SINCE: values.TRENDING_SINCE || "daily",
      ANALYSIS_NUM: String(values.ANALYSIS_NUM || 5),
      README_MAX_LENGTH: String(values.README_MAX_LENGTH || 20000),
      SAVE_README: String(Boolean(values.SAVE_README)),
      PROMPT_TEMPLATE_PATH: values.PROMPT_TEMPLATE_PATH || "Prompt.txt",
      LOG_DIR: values.LOG_DIR || "logs",
      DATABASE_URL: values.DATABASE_URL || "sqlite:///backend/database/agent.db",
      FINAL_REPORT_PATH: values.FINAL_REPORT_PATH || "final_report.txt",
      HTTP_PROXY: values.HTTP_PROXY || "",
      HTTPS_PROXY: values.HTTPS_PROXY || "",
    };
    await updateAgentConfig({ env, prompt: values.prompt || "" });
    message.success("Agent 配置已保存");
    await loadConfig();
  };

  return (
    <Space direction="vertical" size={16} className="full-width">
      <div>
        <Title level={3} style={{ marginBottom: 4 }}>Agent 配置</Title>
        <Text type="secondary">修改后会写入 backend/.env 和 Prompt.txt，下一次定时 Agent 运行时生效。</Text>
      </div>
      <Card loading={loading}>
        <Form form={form} layout="vertical">
          <Space size={16} wrap>
            <Form.Item label="分析语言" name="TRENDING_LANGUAGE">
              <Select
                showSearch
                style={{ width: 180 }}
                placeholder="选择语言"
                optionFilterProp="label"
                options={[
                  { value: "", label: "All (全部语言)" },
                  { value: "python", label: "Python" },
                  { value: "go", label: "Go" },
                  { value: "typescript", label: "TypeScript" },
                  { value: "javascript", label: "JavaScript" },
                  { value: "rust", label: "Rust" },
                  { value: "java", label: "Java" },
                  { value: "c++", label: "C++" },
                  { value: "c", label: "C" },
                  { value: "swift", label: "Swift" },
                  { value: "kotlin", label: "Kotlin" },
                  { value: "shell", label: "Shell" },
                ]}
              />
            </Form.Item>
            <Form.Item label="榜单周期" name="TRENDING_SINCE">
              <Select style={{ width: 180 }} options={[
                { value: "daily", label: "daily" },
                { value: "weekly", label: "weekly" },
                { value: "monthly", label: "monthly" },
              ]} />
            </Form.Item>
            <Form.Item label="分析条目数" name="ANALYSIS_NUM">
              <InputNumber min={1} max={50} style={{ width: 180 }} />
            </Form.Item>
            <Form.Item label="README 截断长度" name="README_MAX_LENGTH">
              <InputNumber min={1000} max={100000} step={1000} style={{ width: 180 }} />
            </Form.Item>
          </Space>

          <Space size={32} wrap>
            <Form.Item label="请求 GitHub API 指标" name="CHECK_GITHUB_API" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="发送通知" name="SEND_MESSAGE" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="保存 README 原文" name="SAVE_README" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>

          <Space size={16} wrap>
            <Form.Item label="飞书 Webhook 地址 (FEISHU_WEBHOOK)" name="FEISHU_WEBHOOK">
              <Input style={{ width: 470 }} placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
            </Form.Item>
            <Form.Item label="备用 Webhook 地址 (NOTIFIER_WEBHOOK)" name="NOTIFIER_WEBHOOK">
              <Input style={{ width: 470 }} placeholder="https://..." />
            </Form.Item>
          </Space>

          <Space size={16} wrap>
            <Form.Item label="HTTP 代理 (HTTP_PROXY)" name="HTTP_PROXY">
              <Input style={{ width: 470 }} placeholder="例如: http://127.0.0.1:7890" />
            </Form.Item>
            <Form.Item label="HTTPS 代理 (HTTPS_PROXY)" name="HTTPS_PROXY">
              <Input style={{ width: 470 }} placeholder="例如: http://127.0.0.1:7890" />
            </Form.Item>
          </Space>

          <Space size={16} wrap>
            <Form.Item label="LLM Base URL" name="LLM_BASE_URL">
              <Input style={{ width: 360 }} />
            </Form.Item>
            <Form.Item label="LLM Model" name="LLM_MODEL">
              <Input style={{ width: 240 }} />
            </Form.Item>
            <Form.Item label="GitHub Token" name="GITHUB_TOKEN">
              <Input.Password style={{ width: 320 }} />
            </Form.Item>
            <Form.Item label="LLM API Key" name="LLM_API_KEY">
              <Input.Password style={{ width: 320 }} />
            </Form.Item>
          </Space>

          <Space size={16} wrap>
            <Form.Item label="Prompt 路径" name="PROMPT_TEMPLATE_PATH">
              <Input style={{ width: 220 }} />
            </Form.Item>
            <Form.Item label="日志目录" name="LOG_DIR">
              <Input style={{ width: 180 }} />
            </Form.Item>
            <Form.Item label="数据库 URL" name="DATABASE_URL">
              <Input style={{ width: 320 }} />
            </Form.Item>
            <Form.Item label="报告路径" name="FINAL_REPORT_PATH">
              <Input style={{ width: 220 }} />
            </Form.Item>
          </Space>

          <Form.Item label="分析 Prompt" name="prompt">
            <TextArea rows={16} />
          </Form.Item>

          <Button type="primary" onClick={submit}>保存配置</Button>
        </Form>
      </Card>
    </Space>
  );
}
