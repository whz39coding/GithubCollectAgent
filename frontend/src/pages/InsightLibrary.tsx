import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Card, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";
import { createInsight, deleteInsight, Insight, InsightPage, InsightPayload, updateInsight } from "../api";
import { Filters } from "../types";

type InsightLibraryProps = {
  data: InsightPage;
  loading: boolean;
  filters: Filters;
  setFilters: (filters: Filters) => void;
  onOpen: (id: number) => void;
  onChanged: () => void;
};

export function InsightLibrary({
  data,
  loading,
  filters,
  setFilters,
  onOpen,
  onChanged,
}: InsightLibraryProps) {
  const [form] = Form.useForm();
  const [editing, setEditing] = useState<Insight | null>(null);
  const [open, setOpen] = useState(false);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ score: 3, stars: 0, language: "Unknown", category: "未分类" });
    setOpen(true);
  };

  const openEdit = (record: Insight) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      tech_stack_text: record.tech_stack?.join(", "),
    });
    setOpen(true);
  };

  const submit = async () => {
    const values = await form.validateFields();
    const payload: InsightPayload = {
      repository_url: values.repository_url,
      project_name: values.project_name,
      summary: values.summary,
      category: values.category || "未分类",
      language: values.language || "Unknown",
      score: values.score || 3,
      stars: values.stars || 0,
      tech_stack: String(values.tech_stack_text || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      business_potential: values.business_potential || "文档未提及",
      activity_level: values.activity_level || "未知",
      community_health: values.community_health || "未知",
    };
    if (editing) {
      await updateInsight(editing.id, payload);
      message.success("项目记录已更新");
    } else {
      await createInsight(payload);
      message.success("项目记录已新增");
    }
    setOpen(false);
    onChanged();
  };

  const remove = async (id: number) => {
    await deleteInsight(id);
    message.success("项目记录已删除");
    onChanged();
  };

  const columns: ColumnsType<Insight> = [
    {
      title: "项目名称",
      dataIndex: "project_name",
      render: (value, record) => <Button type="link" onClick={() => onOpen(record.id)}>{value}</Button>,
    },
    {
      title: "项目地址",
      dataIndex: "repository_url",
      render: (value) => <a href={value} target="_blank" rel="noreferrer">{value}</a>,
    },
    {
      title: "分析摘要",
      dataIndex: "summary",
      ellipsis: true,
    },
    {
      title: "开发语言",
      dataIndex: "language",
      width: 120,
      render: (value) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: "推荐评分",
      dataIndex: "score",
      width: 90,
      render: (value) => <Tag color="gold">{value}</Tag>,
    },
    {
      title: "操作",
      width: 150,
      render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="确认删除这条项目记录？" onConfirm={() => remove(record.id)}>
            <Button danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={16} className="full-width">
      <Card>
        <Space wrap>
          <Input.Search
            placeholder="搜索项目或摘要..."
            allowClear
            onSearch={(keyword) => setFilters({ ...filters, page: 1, keyword })}
            style={{ width: 300 }}
          />
          <DatePicker
            onChange={(date) => setFilters({ ...filters, page: 1, date: date?.format("YYYY-MM-DD") })}
            placeholder="筛选日期"
          />
          <Select
            placeholder="最低评分"
            allowClear
            style={{ width: 140 }}
            onChange={(min_score) => setFilters({ ...filters, page: 1, min_score })}
            options={[1, 2, 3, 4, 5].map((value) => ({ value, label: `${value} 星及以上` }))}
          />
          <Select
            value={filters.sort_by}
            style={{ width: 160 }}
            onChange={(sort_by) => setFilters({ ...filters, sort_by })}
            options={[
              { value: "score", label: "按评分排序" },
              { value: "stars", label: "按 Stars 排序" },
              { value: "date", label: "按日期排序" },
            ]}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增记录
          </Button>
        </Space>
      </Card>

      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={data.items}
        pagination={{
          current: data.page,
          pageSize: data.page_size,
          total: data.total,
          showSizeChanger: true,
        }}
        onChange={(pagination) => setFilters({ ...filters, page: pagination.current || 1, page_size: pagination.pageSize || 20 })}
      />

      <Modal
        title={editing ? "编辑项目记录" : "新增项目记录"}
        open={open}
        onOk={submit}
        onCancel={() => setOpen(false)}
        width={720}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item label="项目名称" name="project_name" rules={[{ required: true }]}>
            <Input placeholder="owner/repo" />
          </Form.Item>
          <Form.Item label="项目地址" name="repository_url" rules={[{ required: true }]}>
            <Input placeholder="https://github.com/owner/repo" />
          </Form.Item>
          <Form.Item label="分析摘要" name="summary" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Space size={16} wrap>
            <Form.Item label="开发语言" name="language">
              <Input style={{ width: 160 }} />
            </Form.Item>
            <Form.Item label="项目分类" name="category">
              <Input style={{ width: 160 }} />
            </Form.Item>
            <Form.Item label="推荐评分 (1-5)" name="score">
              <InputNumber min={1} max={5} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item label="星标数 (Stars)" name="stars">
              <InputNumber min={0} style={{ width: 140 }} />
            </Form.Item>
          </Space>
          <Form.Item label="核心技术栈 (英文逗号分隔)" name="tech_stack_text">
            <Input placeholder="Python, FastAPI, React" />
          </Form.Item>
          <Form.Item label="商业价值与开发潜力" name="business_potential">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Space size={16} wrap>
            <Form.Item label="开发活跃度" name="activity_level">
              <Input style={{ width: 260 }} />
            </Form.Item>
            <Form.Item label="社区健康度" name="community_health">
              <Input style={{ width: 260 }} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Space>
  );
}
