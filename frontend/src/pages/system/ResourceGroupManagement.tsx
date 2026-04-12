import { useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm,
  Select, Space, Table, Tag, Transfer, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, TeamOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { resourceGroupApi, userApi, userGroupApi } from '@/api/system'
import apiClient from '@/api/client'

const { Title, Text } = Typography

export default function ResourceGroupManagement() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [memberModalOpen, setMemberModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [currentRg, setCurrentRg] = useState<any>(null)
  const [search, setSearch] = useState('')
  const [selectedKeys, setSelectedKeys] = useState<string[]>([])
  const [targetKeys, setTargetKeys] = useState<string[]>([])
  const [ugTargetKeys, setUgTargetKeys] = useState<string[]>([])
  const [form] = Form.useForm()
  const [msgApi, msgCtx] = message.useMessage()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['resource-groups', search],
    queryFn: () => resourceGroupApi.list({ search: search || undefined, page_size: 100 }),
  })

  const { data: allUsers } = useQuery({
    queryKey: ['all-users-for-rg'],
    queryFn: () => userApi.list({ page_size: 200 }),
    enabled: memberModalOpen,
  })

  const { data: allGroups } = useQuery({
    queryKey: ['all-user-groups-for-rg'],
    queryFn: () => userGroupApi.list({ page: 1, page_size: 200 }),
    enabled: memberModalOpen,
  })

  const { data: currentMembers } = useQuery({
    queryKey: ['rg-members', currentRg?.id],
    queryFn: () => apiClient.get(`/system/resource-groups/${currentRg.id}/members/`).then(r => r.data),
    enabled: !!currentRg?.id && memberModalOpen,
    onSuccess: (d: any) => {
      setTargetKeys(d.items.map((m: any) => String(m.id)))
    },
  } as any)

  const createMut = useMutation({
    mutationFn: resourceGroupApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['resource-groups'] }); setModalOpen(false); msgApi.success('资源组创建成功') },
    onError: (e: any) => msgApi.error(e.response?.data?.msg || '创建失败'),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: any) => resourceGroupApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['resource-groups'] }); setModalOpen(false); msgApi.success('已更新') },
  })
  const deleteMut = useMutation({
    mutationFn: resourceGroupApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['resource-groups'] }); msgApi.success('已删除') },
    onError: (e: any) => msgApi.error(e.response?.data?.msg || '删除失败'),
  })
  const updateMembersMut = useMutation({
    mutationFn: ({ rgId, userIds }: any) =>
      apiClient.post(`/system/resource-groups/${rgId}/members/`, { user_ids: userIds }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['resource-groups'] })
      qc.invalidateQueries({ queryKey: ['rg-members', currentRg?.id] })
      setMemberModalOpen(false)
      msgApi.success('成员已更新')
      refetch()
    },
    onError: (e: any) => msgApi.error(e.response?.data?.msg || '更新失败'),
  })

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      editId ? updateMut.mutate({ id: editId, data: values }) : createMut.mutate(values)
    } catch { /* validation */ }
  }

  const openCreate = () => { setEditId(null); form.resetFields(); setModalOpen(true) }
  const openEdit = (r: any) => { setEditId(r.id); form.setFieldsValue(r); setModalOpen(true) }
  const openMembers = async (r: any) => {
    setCurrentRg(r)
    setTargetKeys([])
    // Fetch currently linked user groups for this resource group
    try {
      const resp = await apiClient.get(`/system/resource-groups/${r.id}/user-groups/`).then(res => res.data)
      setUgTargetKeys((resp.items ?? []).map((ug: any) => String(ug.id)))
    } catch {
      setUgTargetKeys([])
    }
    setMemberModalOpen(true)
  }

  const transferData = (allUsers?.items || []).map((u: any) => ({
    key: String(u.id),
    title: `${u.username}${u.display_name ? ` (${u.display_name})` : ''}`,
    description: u.email,
  }))

  const ugTransferData = (allGroups?.items ?? []).map((g: any) => ({
    key: String(g.id),
    title: g.name_cn || g.name,
  }))

  const handleSaveMembers = async () => {
    try {
      await updateMembersMut.mutateAsync({ rgId: currentRg.id, userIds: targetKeys.map(Number) })
      await apiClient.put(`/system/resource-groups/${currentRg.id}/user-groups/`, {
        user_group_ids: ugTargetKeys.map(Number),
      })
      qc.invalidateQueries({ queryKey: ['resource-groups'] })
      setMemberModalOpen(false)
      msgApi.success('成员和用户组关联已更新')
      refetch()
    } catch (e: any) {
      msgApi.error(e.response?.data?.detail || e.response?.data?.msg || '更新失败')
    }
  }

  const columns = [
    {
      title: '资源组', key: 'name',
      render: (_: any, r: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{r.group_name}</Text>
          {r.group_name_cn && <Text type="secondary" style={{ fontSize: 12 }}>{r.group_name_cn}</Text>}
        </Space>
      ),
    },
    {
      title: '成员数', dataIndex: 'member_count', width: 90,
      render: (v: number, r: any) => (
        <Button type="link" size="small" icon={<TeamOutlined />} onClick={() => openMembers(r)}>
          {v} 人
        </Button>
      ),
    },
    {
      title: '钉钉 Webhook', dataIndex: 'ding_webhook', width: 180, ellipsis: true,
      render: (v: string) => v
        ? <Text type="secondary" style={{ fontSize: 11 }} title={v}>{v.slice(0, 30)}...</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: '飞书 Webhook', dataIndex: 'feishu_webhook', width: 180, ellipsis: true,
      render: (v: string) => v
        ? <Text type="secondary" style={{ fontSize: 11 }} title={v}>{v.slice(0, 30)}...</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: '状态', dataIndex: 'is_active', width: 80,
      render: (v: boolean) => v ? <Tag color="success">启用</Tag> : <Tag>停用</Tag>,
    },
    {
      title: '操作', width: 120,
      render: (_: any, r: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          <Popconfirm title="确认删除？删除后成员关联将清除"
            onConfirm={() => deleteMut.mutate(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      {msgCtx}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={2} style={{ margin: 0 }}>资源组管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建资源组</Button>
      </div>

      <Card style={{ marginBottom: 12, borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: '12px 16px' } }}>
        <Input.Search placeholder="搜索资源组名称" allowClear style={{ width: 260 }}
          onSearch={setSearch} onChange={e => !e.target.value && setSearch('')} />
      </Card>

      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: 0 } }}>
        <Table dataSource={data?.items} columns={columns} rowKey="id" loading={isLoading}
          pagination={{ total: data?.total, pageSize: 20, showSizeChanger: false }} />
      </Card>

      {/* 新建/编辑资源组 Modal */}
      <Modal title={editId ? '编辑资源组' : '新建资源组'} open={modalOpen}
        onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        confirmLoading={createMut.isPending || updateMut.isPending}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="group_name" label="资源组标识（英文）"
            rules={[{ required: true, message: '请输入资源组标识' }]}>
            <Input placeholder="如 production、dev" disabled={!!editId} />
          </Form.Item>
          <Form.Item name="group_name_cn" label="中文名称">
            <Input placeholder="如 生产环境、开发环境" />
          </Form.Item>
          <Form.Item name="ding_webhook" label="钉钉 Webhook">
            <Input placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." />
          </Form.Item>
          <Form.Item name="feishu_webhook" label="飞书 Webhook">
            <Input placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 成员管理 Modal — 包含用户穿梭框 + 用户组穿梭框 */}
      <Modal
        title={`成员管理 — ${currentRg?.group_name || ''}`}
        open={memberModalOpen}
        onOk={handleSaveMembers}
        onCancel={() => setMemberModalOpen(false)}
        confirmLoading={updateMembersMut.isPending}
        width={720}
        okText="保存成员"
      >
        <div style={{ marginTop: 16 }}>
          <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>直接成员</Text>
          <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 12 }}>
            左侧为所有用户，将需要加入此资源组的用户移到右侧：
          </Text>
          <Transfer
            dataSource={transferData}
            titles={['所有用户', '资源组成员']}
            targetKeys={targetKeys}
            selectedKeys={selectedKeys}
            onChange={(nextTarget) => setTargetKeys(nextTarget as string[])}
            onSelectChange={(s, ts) => setSelectedKeys([...(s as string[]), ...(ts as string[])])}
            render={item => item.title}
            listStyle={{ width: 280, height: 280 }}
            showSearch
            filterOption={(val, item) =>
              item.title.toLowerCase().includes(val.toLowerCase())
            }
          />

          <div style={{ marginTop: 24 }}>
            <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 8 }}>关联用户组</Text>
            <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 12 }}>
              用户组关联后，组内所有成员自动获得此资源组的访问权限：
            </Text>
            <Transfer
              dataSource={ugTransferData}
              titles={['可选用户组', '已关联']}
              targetKeys={ugTargetKeys}
              onChange={(next) => setUgTargetKeys(next as string[])}
              render={item => item.title}
              listStyle={{ width: 280, height: 280 }}
              showSearch
              filterOption={(val, item) =>
                (item.title ?? '').toLowerCase().includes(val.toLowerCase())
              }
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}