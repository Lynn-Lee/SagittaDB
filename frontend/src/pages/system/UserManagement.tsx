import { useState } from 'react'
import { Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { userApi, roleApi, userGroupApi } from '@/api/system'

const { Title, Text } = Typography

export default function UserManagement() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [form] = Form.useForm()
  const [msgApi, msgCtx] = message.useMessage()

  const { data, isLoading } = useQuery({
    queryKey: ['users', search],
    queryFn: () => userApi.list({ search: search || undefined }),
  })

  const { data: rolesData } = useQuery({
    queryKey: ['all-roles'],
    queryFn: () => roleApi.list({ page: 1, page_size: 200 }),
  })

  const { data: groupsData } = useQuery({
    queryKey: ['all-user-groups'],
    queryFn: () => userGroupApi.list({ page: 1, page_size: 200 }),
  })

  const roleOptions = (rolesData?.items ?? []).map((r: any) => ({
    value: r.id, label: r.name_cn || r.name,
  }))

  const allUsers = data?.items ?? []
  const managerOptions = allUsers.map((u: any) => ({
    value: u.id, label: `${u.display_name || u.username} (${u.username})`,
  }))

  const groupOptions = (groupsData?.items ?? []).map((g: any) => ({
    value: g.id, label: g.name_cn || g.name,
  }))

  const createMut = useMutation({
    mutationFn: userApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setModalOpen(false); msgApi.success('用户创建成功') },
    onError: (e: any) => msgApi.error(e.response?.data?.msg || '创建失败'),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => userApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setModalOpen(false); msgApi.success('已更新') },
  })
  const deleteMut = useMutation({
    mutationFn: userApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); msgApi.success('已删除') },
  })

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (!values.password && editId) delete values.password
      editId ? updateMut.mutate({ id: editId, data: values }) : createMut.mutate(values)
    } catch { /* validation */ }
  }
  const openCreate = () => { setEditId(null); form.resetFields(); setModalOpen(true) }
  const openEdit = (r: any) => {
    setEditId(r.id)
    form.setFieldsValue({
      ...r,
      password: '',
      role_id: r.role_id,
      manager_id: r.manager_id,
      employee_id: r.employee_id,
      department: r.department,
      title: r.title,
      user_group_ids: (r.user_groups ?? []).map((ug: any) => ug.id ?? ug),
    })
    setModalOpen(true)
  }

  const columns: ColumnsType<any> = [
    { title: '用户名', dataIndex: 'username', render: (n, r) => <Space direction="vertical" size={0}><Text strong>{n}</Text><Text type="secondary" style={{ fontSize: 12 }}>{r.display_name}</Text></Space> },
    { title: '邮箱', dataIndex: 'email', render: v => v || <Text type="secondary">—</Text> },
    { title: '角色', dataIndex: 'role_name', width: 120, render: (name, r) => {
      if (r.is_superuser) return <Tag color="red">超级管理员</Tag>
      return name ? <Tag color="blue">{name}</Tag> : <Tag>普通用户</Tag>
    }},
    { title: '认证', dataIndex: 'auth_type', width: 90, render: t => <Tag>{t}</Tag> },
    { title: '部门', dataIndex: 'department', width: 100, render: v => v || <Text type="secondary">—</Text> },
    { title: '职位', dataIndex: 'title', width: 100, render: v => v || <Text type="secondary">—</Text> },
    { title: '状态', dataIndex: 'is_active', width: 80, render: (v, r) => <Switch checked={v} size="small" onChange={c => updateMut.mutate({ id: r.id, data: { is_active: c } })} /> },
    { title: '操作', width: 100, render: (_, r) => <Space><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} /><Popconfirm title="确认删除？" onConfirm={() => deleteMut.mutate(r.id)} okText="删除" cancelText="取消"><Button size="small" danger icon={<DeleteOutlined />} /></Popconfirm></Space> },
  ]

  return (
    <div>
      {msgCtx}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={2} style={{ margin: 0 }}>用户管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建用户</Button>
      </div>
      <Card style={{ marginBottom: 16, borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }} styles={{ body: { padding: '12px 16px' } }}>
        <Input.Search placeholder="搜索用户名 / 显示名 / 邮箱" allowClear style={{ width: 300 }}
          onSearch={setSearch} onChange={e => !e.target.value && setSearch('')} />
      </Card>
      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }} styles={{ body: { padding: 0 } }}>
        <Table dataSource={data?.items} columns={columns} rowKey="id" loading={isLoading}
          pagination={{ total: data?.total, pageSize: 20, showSizeChanger: false, showTotal: t => `共 ${t} 个用户` }} />
      </Card>
      <Modal title={editId ? '编辑用户' : '新建用户'} open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        okText={editId ? '保存' : '创建'} confirmLoading={createMut.isPending || updateMut.isPending} width={640}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}><Input disabled={!!editId} /></Form.Item>
          <Form.Item name="display_name" label="显示名称"><Input /></Form.Item>
          <Form.Item name="password" label="密码" rules={editId ? [] : [{ required: true, min: 8 }]}><Input.Password placeholder={editId ? '留空不修改' : '至少 8 位'} /></Form.Item>
          <Form.Item name="email" label="邮箱"><Input type="email" /></Form.Item>
          <Form.Item name="phone" label="手机号"><Input /></Form.Item>
          <Form.Item name="role_id" label="角色">
            <Select allowClear placeholder="选择角色（留空为普通用户）" options={roleOptions} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="manager_id" label="直属上级">
            <Select allowClear placeholder="选择直属上级" options={managerOptions} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="employee_id" label="工号"><Input placeholder="如 EMP001" /></Form.Item>
          <Form.Item name="department" label="部门"><Input placeholder="如 技术部" /></Form.Item>
          <Form.Item name="title" label="职位"><Input placeholder="如 高级工程师" /></Form.Item>
          <Form.Item name="user_group_ids" label="用户组">
            <Select mode="multiple" placeholder="选择用户组" options={groupOptions} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="is_superuser" label="超级管理员" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}