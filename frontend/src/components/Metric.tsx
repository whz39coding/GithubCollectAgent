import { Card, Col, Statistic } from "antd";

type MetricProps = {
  title: string;
  value: number;
  suffix?: string;
};

export function Metric({ title, value, suffix }: MetricProps) {
  return (
    <Col flex="1 1 180px">
      <Card>
        <Statistic title={title} value={value} suffix={suffix} />
      </Card>
    </Col>
  );
}
