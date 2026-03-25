import { Card, Typography } from 'antd'
const { Title } = Typography
export default function MonitorDetail() {
  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>MonitorDetail</Title>
      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}>
        <div style={{ padding: 48, textAlign: 'center', color: '#AEAEB2' }}>
          MonitorDetail — Sprint 1/2/3 实现
        </div>
      </Card>
    </div>
  )
}
