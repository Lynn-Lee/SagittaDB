import { useState } from 'react'
import { Card, Col, InputNumber, Row, Select, Statistic, Space, Typography, Divider } from 'antd'
import {
  FileTextOutlined, CheckCircleOutlined, ClockCircleOutlined,
  DatabaseOutlined, SearchOutlined, MonitorOutlined,
  CloseCircleOutlined, WarningOutlined, StopOutlined, SyncOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, PieChart, Pie, Cell, ResponsiveContainer,
} from 'recharts'
import apiClient from '@/api/client'

const { Title, Text } = Typography
const { Option } = Select

const STATUS_LABELS: Record<string, string> = {
  pending_review: '待审核', review_rejected: '审批驳回', review_pass: '审核通过',
  timing: '定时执行', queuing: '队列中', executing: '执行中',
  finish: '执行成功', exception: '执行异常', canceled: '已取消',
}
const STATUS_ICONS: Record<string, any> = {
  pending_review: <ClockCircleOutlined />, review_rejected: <CloseCircleOutlined />,
  review_pass: <CheckCircleOutlined />, timing: <ClockCircleOutlined />,
  queuing: <SyncOutlined />, executing: <SyncOutlined spin />,
  finish: <CheckCircleOutlined />, exception: <WarningOutlined />, canceled: <StopOutlined />,
}
const STATUS_COLORS_MAP: Record<string, string> = {
  pending_review: '#faad14', review_rejected: '#f5222d', review_pass: '#1558A8',
  timing: '#722ed1', queuing: '#13c2c2', executing: '#1558A8',
  finish: '#52c41a', exception: '#fa8c16', canceled: '#AEAEB2',
}
const LINE_COLORS = {
  submit: '#1558A8', finish: '#52c41a', reject: '#f5222d',
  exception: '#fa8c16', canceled: '#AEAEB2',
}
const PIE_COLORS = ['#1558A8', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#fa8c16', '#AEAEB2']

export default function DashboardPage() {
  const [statDays, setStatDays] = useState<number>(30)
  const [statDaysInput, setStatDaysInput] = useState<number>(30)
  const [trendDays, setTrendDays] = useState<number>(7)
  const [trendDaysInput, setTrendDaysInput] = useState<number>(7)

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats', statDays],
    queryFn: () => apiClient.get(`/monitor/dashboard/stats/?days=${statDays}`).then(r => r.data),
    refetchInterval: 30000,
  })
  const { data: trend } = useQuery({
    queryKey: ['dashboard-trend', trendDays],
    queryFn: () => apiClient.get(`/monitor/dashboard/workflow-trend/?days=${trendDays}`).then(r => r.data.items),
    refetchInterval: 60000,
  })
  const { data: dist } = useQuery({
    queryKey: ['dashboard-dist'],
    queryFn: () => apiClient.get('/monitor/dashboard/instance-dist/').then(r => r.data.items),
    refetchInterval: 60000,
  })

  const byStatus = stats?.workflow_by_status || {}
  const statusCards = Object.entries(STATUS_LABELS).map(([key, label]) => ({
    key, label, value: byStatus[key] ?? 0,
    icon: STATUS_ICONS[key], color: STATUS_COLORS_MAP[key],
  }))
  const pieData = statusCards.filter(c => c.value > 0).map(c => ({ name: c.label, value: c.value }))

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={2} style={{ margin: 0 }}>Dashboard</Title>
        <Space align="center" size={8}>
          <Text type="secondary" style={{ fontSize: 13 }}>统计周期：</Text>
          <Select value={statDays} onChange={v => { setStatDays(v); setStatDaysInput(v) }}
            style={{ width: 90 }} size="small">
            {[7, 14, 30, 60, 90].map(d => <Option key={d} value={d}>近{d}天</Option>)}
          </Select>
          <Text type="secondary" style={{ fontSize: 12 }}>或自定义</Text>
          <InputNumber
            min={1} max={365} value={statDaysInput} size="small" style={{ width: 70 }}
            onChange={v => setStatDaysInput(v || 30)}
            onPressEnter={() => setStatDays(statDaysInput)}
            onBlur={() => setStatDays(statDaysInput)}
            addonAfter="天"
          />
          <Text type="secondary" style={{ fontSize: 12 }}>共 {stats?.workflow_total ?? 0} 个工单</Text>
        </Space>
      </div>

      {/* 全局统计 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {[
          { title: '接入实例', value: stats?.instance_total ?? 0, icon: <DatabaseOutlined />, color: '#722ed1' },
          { title: '今日查询', value: stats?.query_today_total ?? 0, icon: <SearchOutlined />, color: '#13c2c2' },
          { title: '监控实例', value: stats?.monitor_instance_total ?? 0, icon: <MonitorOutlined />, color: '#f5222d' },
        ].map(c => (
          <Col key={c.title} xs={24} sm={8}>
            <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }} styles={{ body: { padding: '16px 20px' } }}>
              <Statistic title={c.title} value={c.value}
                prefix={<span style={{ color: c.color, marginRight: 4 }}>{c.icon}</span>}
                valueStyle={{ color: c.color, fontWeight: 600 }} />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 工单各状态卡片 */}
      <Row gutter={[10, 10]} style={{ marginBottom: 20 }}>
        {statusCards.map(card => (
          <Col key={card.key} xs={12} sm={8} md={6} lg={4} xl={card.value > 0 ? 3 : 4}>
            <Card
              style={{
                borderRadius: 10,
                border: `1px solid ${card.color}33`,
                background: card.value > 0 ? `${card.color}0D` : undefined,
              }}
              styles={{ body: { padding: '10px 14px' } }}>
              <Statistic
                title={<span style={{ fontSize: 12, color: '#636366' }}>{card.label}</span>}
                value={card.value}
                prefix={<span style={{ color: card.color, marginRight: 2, fontSize: 12 }}>{card.icon}</span>}
                valueStyle={{ color: card.color, fontWeight: 700, fontSize: 20 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        {/* 工单趋势图 */}
        <Col xs={24} lg={16}>
          <Card
            title="工单趋势"
            style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
            extra={
              <Space size={6}>
                <Select value={trendDays} onChange={v => { setTrendDays(v); setTrendDaysInput(v) }}
                  style={{ width: 80 }} size="small">
                  {[7, 14, 30, 60].map(d => <Option key={d} value={d}>{d}天</Option>)}
                </Select>
                <Text type="secondary" style={{ fontSize: 12 }}>自定义</Text>
                <InputNumber
                  min={1} max={90} value={trendDaysInput} size="small" style={{ width: 65 }}
                  onChange={v => setTrendDaysInput(v || 7)}
                  onPressEnter={() => setTrendDays(trendDaysInput)}
                  onBlur={() => setTrendDays(trendDaysInput)}
                  addonAfter="天"
                />
              </Space>
            }
          >
            {trend && trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={trend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="submit" stroke={LINE_COLORS.submit} name="提交" strokeWidth={2} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="finish" stroke={LINE_COLORS.finish} name="执行成功" strokeWidth={2} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="reject" stroke={LINE_COLORS.reject} name="审批驳回" strokeWidth={2} dot={{ r: 2 }} />
                  <Line type="monotone" dataKey="exception" stroke={LINE_COLORS.exception} name="执行异常" strokeWidth={1.5} dot={{ r: 2 }} strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="canceled" stroke={LINE_COLORS.canceled} name="已取消" strokeWidth={1} dot={{ r: 2 }} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#AEAEB2' }}>
                暂无工单数据
              </div>
            )}
          </Card>
        </Col>

        {/* 右侧饼图 */}
        <Col xs={24} lg={8}>
          <Row gutter={[0, 14]}>
            <Col span={24}>
              <Card title="工单状态分布" style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}>
                {pieData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        outerRadius={65}
                        label={({ percent }) => percent > 0.05 ? `${(percent*100).toFixed(0)}%` : ''}
                        labelLine={false}>
                        {pieData.map((_: any, i: number) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                      </Pie>
                      <Tooltip />
                      <Legend iconSize={10} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#AEAEB2' }}>暂无工单</div>
                )}
              </Card>
            </Col>
            <Col span={24}>
              <Card title="实例类型分布" style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}>
                {dist && dist.length > 0 ? (
                  <ResponsiveContainer width="100%" height={140}>
                    <PieChart>
                      <Pie data={dist} dataKey="count" nameKey="db_type" cx="50%" cy="50%"
                        outerRadius={55}
                        label={({ db_type, percent }) => `${db_type} ${(percent*100).toFixed(0)}%`}
                        labelLine={false}>
                        {dist.map((_: any, i: number) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ height: 140, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#AEAEB2' }}>暂无实例</div>
                )}
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>
    </div>
  )
}
