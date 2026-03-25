import { useState } from 'react'
import {
  Button, Card, DatePicker, Input, InputNumber, Select,
  Space, Table, Tag, Typography, Tooltip,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { workflowApi } from '@/api/workflow'
import { instanceApi } from '@/api/instance'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { Option } = Select
const { RangePicker } = DatePicker

const STATUS_COLOR: Record<number, string> = {
  0: 'processing', 1: 'error', 2: 'success', 3: 'warning',
  4: 'default', 5: 'processing', 6: 'success', 7: 'error', 8: 'default',
}

export default function WorkflowList() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<number | undefined>()
  const [instanceFilter, setInstanceFilter] = useState<number | undefined>()
  const [engineerFilter, setEngineerFilter] = useState('')
  const [dbNameFilter, setDbNameFilter] = useState('')
  const [dateRange, setDateRange] = useState<[string, string] | null>(null)
  const [page, setPage] = useState(1)

  const { data: instanceData } = useQuery({
    queryKey: ['instances-for-wf-filter'],
    queryFn: () => instanceApi.list({ page_size: 200 }),
  })

  const queryParams = {
    search: search || undefined,
    status: statusFilter,
    instance_id: instanceFilter,
    engineer: engineerFilter || undefined,
    db_name: dbNameFilter || undefined,
    date_start: dateRange?.[0] || undefined,
    date_end: dateRange?.[1] || undefined,
    page,
    page_size: 20,
  }

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['workflows', queryParams],
    queryFn: () => workflowApi.list(queryParams),
  })

  const handleReset = () => {
    setSearch(''); setStatusFilter(undefined); setInstanceFilter(undefined)
    setEngineerFilter(''); setDbNameFilter(''); setDateRange(null); setPage(1)
  }

  const columns: ColumnsType<any> = [
    {
      title: 'ID', dataIndex: 'id', width: 65,
      render: (id) => (
        <a onClick={() => navigate(`/workflow/${id}`)}
          style={{ fontFamily: 'monospace', color: '#1558A8' }}>#{id}</a>
      ),
    },
    {
      title: '工单名称', dataIndex: 'workflow_name', ellipsis: true, minWidth: 160,
      render: (name, r) => (
        <Tooltip title={name}>
          <a onClick={() => navigate(`/workflow/${r.id}`)} style={{ fontWeight: 500 }}>{name}</a>
        </Tooltip>
      ),
    },
    { title: '资源组', dataIndex: 'group_name', width: 100, ellipsis: true },
    {
      title: '目标实例', key: 'instance', width: 150,
      render: (_, r) => (
        <Text style={{ fontSize: 12, fontWeight: 500 }}>
          {r.instance_name || <Text type="secondary">ID:{r.instance_id}</Text>}
        </Text>
      ),
    },
    {
      title: '数据库', dataIndex: 'db_name', width: 100,
      render: (v) => v ? <Text style={{ fontSize: 12 }}>{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: '提交人', key: 'engineer', width: 90,
      render: (_, r) => r.engineer_display || r.engineer,
    },
    {
      title: '状态', dataIndex: 'status', width: 110,
      render: (s, r) => <Tag color={STATUS_COLOR[s]}>{r.status_desc}</Tag>,
    },
    {
      title: '提交时间', dataIndex: 'created_at', width: 150,
      render: v => v ? dayjs(v).format('MM-DD HH:mm') : '—',
    },
    {
      title: '操作', width: 65, fixed: 'right',
      render: (_, r) => (
        <Button size="small" type="link" onClick={() => navigate(`/workflow/${r.id}`)}>详情</Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space align="center">
          <Title level={2} style={{ margin: 0 }}>SQL 工单</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>共 {data?.total ?? 0} 个</Text>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/workflow/submit')}>
          提交工单
        </Button>
      </div>

      {/* 查询条件 */}
      <Card style={{ marginBottom: 12, borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: '12px 16px' } }}>
        <Space wrap size={[8, 8]}>
          <Input
            placeholder="工单名称"
            allowClear
            prefix={<SearchOutlined style={{ color: '#AEAEB2' }} />}
            style={{ width: 180 }}
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
          />
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 120 }}
            value={statusFilter}
            onChange={v => { setStatusFilter(v); setPage(1) }}
          >
            <Option value={0}>待审核</Option>
            <Option value={1}>审批驳回</Option>
            <Option value={2}>审核通过</Option>
            <Option value={3}>定时执行</Option>
            <Option value={4}>队列中</Option>
            <Option value={5}>执行中</Option>
            <Option value={6}>执行成功</Option>
            <Option value={7}>执行异常</Option>
            <Option value={8}>已取消</Option>
          </Select>
          <Select
            placeholder="目标实例"
            allowClear
            style={{ width: 190 }}
            value={instanceFilter}
            onChange={v => { setInstanceFilter(v); setPage(1) }}
            showSearch
            optionFilterProp="label"
          >
            {instanceData?.items?.map((i: any) => (
              <Option key={i.id} value={i.id} label={i.instance_name}>
                <Tag color="blue" style={{ fontSize: 11 }}>{i.db_type.toUpperCase()}</Tag>
                {i.instance_name}
              </Option>
            ))}
          </Select>
          <Input
            placeholder="数据库名"
            allowClear
            style={{ width: 130 }}
            value={dbNameFilter}
            onChange={e => { setDbNameFilter(e.target.value); setPage(1) }}
          />
          <Input
            placeholder="提交人"
            allowClear
            style={{ width: 110 }}
            value={engineerFilter}
            onChange={e => { setEngineerFilter(e.target.value); setPage(1) }}
          />
          <RangePicker
            style={{ width: 230 }}
            onChange={(_, strs) => {
              setDateRange(strs[0] ? [strs[0], strs[1]] : null)
              setPage(1)
            }}
          />
          <Button onClick={handleReset}>重置</Button>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
        </Space>
      </Card>

      <Card
        style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: 0 } }}
      >
        <Table
          dataSource={data?.items}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 900 }}
          pagination={{
            total: data?.total,
            current: page,
            pageSize: 20,
            onChange: p => setPage(p),
            showSizeChanger: false,
            showTotal: t => `共 ${t} 个工单`,
          }}
        />
      </Card>
    </div>
  )
}
