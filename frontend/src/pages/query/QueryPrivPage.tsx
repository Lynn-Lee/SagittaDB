import { useState } from 'react'
import { Button, Card, DatePicker, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography, message, Tabs } from 'antd'
import { PlusOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { queryApi } from '@/api/query'
import { instanceApi } from '@/api/instance'
import { resourceGroupApi } from '@/api/system'
import { useAuthStore } from '@/store/auth'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { Option } = Select

const STATUS_MAP: Record<number, { label: string; color: string }> = {
  0: { label: '待审核', color: 'processing' },
  1: { label: '已通过', color: 'success' },
  2: { label: '已驳回', color: 'error' },
  3: { label: '已取消', color: 'default' },
}

export default function QueryPrivPage() {
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const [applyModalOpen, setApplyModalOpen] = useState(false)
  const [applyForm] = Form.useForm()
  const [instanceId, setInstanceId] = useState<number | undefined>()
  const [msgApi, msgCtx] = message.useMessage()
  const isReviewer = user?.is_superuser || user?.permissions?.includes('query_review')

  // 我的权限列表
  const { data: privData } = useQuery({
    queryKey: ['my-query-privs'],
    queryFn: () => queryApi.listPrivileges(),
  })

  // 申请列表
  const { data: applyData, refetch: refetchApplies } = useQuery({
    queryKey: ['query-priv-applies'],
    queryFn: () => queryApi.listApplies({ page_size: 50 }),
  })

  // 实例、资源组
  const { data: instanceData } = useQuery({
    queryKey: ['instances-for-priv'],
    queryFn: () => instanceApi.list({ page_size: 200 }),
  })
  const { data: rgData } = useQuery({
    queryKey: ['rg-for-priv'],
    queryFn: () => resourceGroupApi.list({ page_size: 100 }),
  })
  const { data: dbData } = useQuery({
    queryKey: ['dbs-for-priv', instanceId],
    queryFn: () => instanceApi.getDatabases(instanceId!),
    enabled: !!instanceId,
  })

  const applyMut = useMutation({
    mutationFn: queryApi.applyPrivilege,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['query-priv-applies'] }); setApplyModalOpen(false); msgApi.success('申请已提交') },
    onError: (e: any) => msgApi.error(e.response?.data?.msg || '提交失败'),
  })

  const auditMut = useMutation({
    mutationFn: ({ apply_id, action }: any) => queryApi.auditApply(apply_id, { action }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['query-priv-applies'] }); msgApi.success('审批完成') },
    onError: (e: any) => msgApi.error(e.response?.data?.msg || '审批失败'),
  })

  const handleApply = async () => {
    try {
      const values = await applyForm.validateFields()
      applyMut.mutate({
        ...values,
        valid_date: values.valid_date.format('YYYY-MM-DD'),
        instance_id: instanceId,
      })
    } catch { /* validation */ }
  }

  const privColumns = [
    { title: '实例ID', dataIndex: 'instance_id', width: 80 },
    { title: '数据库', dataIndex: 'db_name' },
    { title: '表名', dataIndex: 'table_name', render: (v: string) => v || <Text type="secondary">全库</Text> },
    { title: '行数限制', dataIndex: 'limit_num', width: 90 },
    {
      title: '有效期', dataIndex: 'valid_date', width: 110,
      render: (v: string) => {
        const expired = dayjs(v).isBefore(dayjs())
        return <Tag color={expired ? 'default' : 'success'}>{v}{expired ? ' (已过期)' : ''}</Tag>
      },
    },
  ]

  const applyColumns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '申请数据库', dataIndex: 'db_name' },
    { title: '申请理由', dataIndex: 'apply_reason', ellipsis: true },
    {
      title: '状态', dataIndex: 'status', width: 90,
      render: (v: number) => <Tag color={STATUS_MAP[v]?.color}>{STATUS_MAP[v]?.label}</Tag>,
    },
    {
      title: '提交时间', dataIndex: 'created_at', width: 140,
      render: (v: string) => v ? dayjs(v).format('MM-DD HH:mm') : '—',
    },
    isReviewer ? {
      title: '操作', width: 130,
      render: (_: any, r: any) => r.status === 0 ? (
        <Space>
          <Button size="small" type="primary" icon={<CheckOutlined />}
            onClick={() => auditMut.mutate({ apply_id: r.id, action: 'pass' })}>通过</Button>
          <Button size="small" danger icon={<CloseOutlined />}
            onClick={() => auditMut.mutate({ apply_id: r.id, action: 'reject' })}>驳回</Button>
        </Space>
      ) : null,
    } : null,
  ].filter(Boolean)

  const tabItems = [
    {
      key: 'privs',
      label: `我的权限（${privData?.items?.length ?? 0}）`,
      children: (
        <Table dataSource={privData?.items} columns={privColumns}
          rowKey="id" size="small" pagination={{ pageSize: 20 }} />
      ),
    },
    {
      key: 'applies',
      label: `申请记录（${applyData?.total ?? 0}）`,
      children: (
        <Table dataSource={applyData?.items} columns={applyColumns as any}
          rowKey="id" size="small" pagination={{ pageSize: 20 }} />
      ),
    },
  ]

  return (
    <div>
      {msgCtx}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={2} style={{ margin: 0 }}>查询权限</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { applyForm.resetFields(); setApplyModalOpen(true) }}>
          申请查询权限
        </Button>
      </div>

      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}>
        <Tabs items={tabItems} />
      </Card>

      <Modal title="申请查询权限" open={applyModalOpen}
        onOk={handleApply} onCancel={() => setApplyModalOpen(false)}
        confirmLoading={applyMut.isPending} width={520}>
        <Form form={applyForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="title" label="申请标题" rules={[{ required: true }]}>
            <Input placeholder="简明描述申请用途" />
          </Form.Item>
          <Form.Item label="目标实例" required>
            <Select placeholder="选择实例" onChange={v => setInstanceId(v)} showSearch optionFilterProp="label">
              {instanceData?.items?.map((i: any) => (
                <Option key={i.id} value={i.id} label={i.instance_name}>
                  <Tag color="blue">{i.db_type.toUpperCase()}</Tag> {i.instance_name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="group_id" label="资源组" rules={[{ required: true }]}>
            <Select placeholder="选择资源组">
              {rgData?.items?.map((rg: any) => <Option key={rg.id} value={rg.id}>{rg.group_name}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="db_name" label="数据库" rules={[{ required: true }]}>
            <Select placeholder="选择数据库" showSearch disabled={!instanceId}>
              {dbData?.databases?.map((db: string) => <Option key={db} value={db}>{db}</Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="valid_date" label="有效期至" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} disabledDate={d => d.isBefore(dayjs())} />
          </Form.Item>
          <Form.Item name="limit_num" label="行数限制" initialValue={100}>
            <InputNumber min={1} max={100000} style={{ width: '100%' }} addonAfter="行" />
          </Form.Item>
          <Form.Item name="apply_reason" label="申请理由">
            <Input.TextArea rows={3} placeholder="说明申请原因" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
