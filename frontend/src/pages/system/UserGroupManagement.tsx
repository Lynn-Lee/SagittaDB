import { useState } from 'react'
import {
  Button, Card, Col, Form, Input, Row, Select, Space, Switch, Table, Tag, Transfer, message,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userGroupApi, userApi, resourceGroupApi } from '@/api/system'

const UserGroupManagement: React.FC = () => {
  const [modalOpen, setModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [form] = Form.useForm()
  const [messageApi, contextHolder] = message.useMessage()
  const qc = useQueryClient()

  const { data: groupsData, isLoading } = useQuery({
    queryKey: ['user-groups', search],
    queryFn: () => userGroupApi.list({ page: 1, page_size: 200 }),
  })

  const { data: usersData } = useQuery({
    queryKey: ['all-users'],
    queryFn: () => userApi.list({ page: 1, page_size: 500 }),
  })

  const { data: rgsData } = useQuery({
    queryKey: ['all-resource-groups'],
    queryFn: () => resourceGroupApi.list({ page: 1, page_size: 500 }),
  })

  const allUsers = usersData?.items ?? []
  const allRgs = rgsData?.items ?? []
  const filtered = (groupsData?.items ?? []).filter((g: any) =>
    !search || g.name.includes(search) || g.name_cn?.includes(search),
  )

  const userTransferSource = allUsers.map((u: any) => ({
    key: String(u.id),
    title: `${u.display_name || u.username}`,
  }))

  const rgTransferSource = allRgs.map((rg: any) => ({
    key: String(rg.id),
    title: rg.group_name_cn || rg.group_name,
  }))

  const createMut = useMutation({
    mutationFn: (data: any) => userGroupApi.create(data),
    onSuccess: () => {
      messageApi.success('用户组创建成功')
      qc.invalidateQueries({ queryKey: ['user-groups'] })
      setModalOpen(false)
      form.resetFields()
    },
    onError: (e: any) => messageApi.error(e.response?.data?.detail || '创建失败'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => userGroupApi.update(id, data),
    onSuccess: () => {
      messageApi.success('用户组已更新')
      qc.invalidateQueries({ queryKey: ['user-groups'] })
      setModalOpen(false)
      form.resetFields()
      setEditId(null)
    },
    onError: (e: any) => messageApi.error(e.response?.data?.detail || '更新失败'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => userGroupApi.delete(id),
    onSuccess: () => {
      messageApi.success('用户组已删除')
      qc.invalidateQueries({ queryKey: ['user-groups'] })
    },
    onError: (e: any) => messageApi.error(e.response?.data?.detail || '删除失败'),
  })

  const openCreate = () => {
    setEditId(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = async (id: number) => {
    setEditId(id)
    const group = await userGroupApi.get(id)
    form.setFieldsValue({
      name_cn: group.name_cn,
      description: group.description,
      leader_id: group.leader_id,
      parent_id: group.parent_id,
      is_active: group.is_active,
      member_ids: (group.member_ids ?? []).map(String),
      resource_group_ids: (group.resource_group_ids ?? []).map(String),
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const member_ids = (values.member_ids ?? []).map(Number)
    const resource_group_ids = (values.resource_group_ids ?? []).map(Number)
    const payload = { ...values, member_ids, resource_group_ids }
    if (editId) {
      updateMut.mutate({ id: editId, data: payload })
    } else {
      createMut.mutate(payload)
    }
  }

  const leaderOptions = allUsers.map((u: any) => ({
    value: u.id, label: `${u.display_name || u.username} (${u.username})`,
  }))

  const parentOptions = filtered.map((g: any) => ({
    value: g.id, label: g.name_cn || g.name,
  }))

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '组标识', dataIndex: 'name', width: 150 },
    { title: '中文名', dataIndex: 'name_cn', width: 150 },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '成员数', dataIndex: 'member_count', width: 90 },
    {
      title: '状态', dataIndex: 'is_active', width: 80,
      render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag>,
    },
    {
      title: '操作', width: 140,
      render: (_: any, record: any) => (
        <Space>
          <a onClick={() => openEdit(record.id)}>编辑</a>
          <a onClick={() => deleteMut.mutate(record.id)} style={{ color: '#ff4d4f' }}>删除</a>
        </Space>
      ),
    },
  ]

  return (
    <>
      {contextHolder}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>用户组管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用户组</Button>
      </div>

      <Card style={{ marginBottom: 16, borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}>
        <Input.Search
          placeholder="搜索用户组标识或中文名"
          allowClear
          onSearch={setSearch}
          style={{ maxWidth: 400 }}
        />
      </Card>

      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={filtered}
          loading={isLoading}
          pagination={false}
          size="middle"
        />
      </Card>

      <Modal
        title={editId ? '编辑用户组' : '新建用户组'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => { setModalOpen(false); form.resetFields(); setEditId(null) }}
        confirmLoading={createMut.isPending || updateMut.isPending}
        width={700}
      >
        <Form form={form} layout="vertical">
          {!editId && (
            <Form.Item name="name" label="组标识" rules={[{ required: true, min: 2, message: '至少2个字符' }]}>
              <Input placeholder="如 dev_team" />
            </Form.Item>
          )}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name_cn" label="中文名">
                <Input placeholder="如 开发组" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="leader_id" label="组长">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={leaderOptions}
                  placeholder="选择组长"
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="组用途说明" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="parent_id" label="父组">
                <Select allowClear options={parentOptions} placeholder="无（顶级组）" />
              </Form.Item>
            </Col>
            <Col span={12}>
              {editId && (
                <Form.Item name="is_active" label="启用" valuePropName="checked">
                  <Switch />
                </Form.Item>
              )}
            </Col>
          </Row>

          <Form.Item name="member_ids" label="组成员">
            <Transfer
              dataSource={userTransferSource}
              render={(item) => item.title!}
              titles={['可选用户', '已选用户']}
              showSearch
              filterOption={(input, item) => (item.title ?? '').toLowerCase().includes(input.toLowerCase())}
              listStyle={{ width: 280, height: 300 }}
            />
          </Form.Item>

          <Form.Item name="resource_group_ids" label="关联资源组">
            <Transfer
              dataSource={rgTransferSource}
              render={(item) => item.title!}
              titles={['可选资源组', '已关联']}
              listStyle={{ width: 280, height: 300 }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

export default UserGroupManagement