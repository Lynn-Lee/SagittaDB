import { useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select,
  Space, Table, Tag, Typography, message, Badge,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined,
} from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { instanceApi } from '@/api/instance'
import apiClient from '@/api/client'

const { Title, Text } = Typography
const { Option } = Select

export default function WorkflowTemplatePage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [modalOpen, setModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [sql, setSql] = useState('')
  const [search, setSearch] = useState('')
  const [form] = Form.useForm()
  const [msgApi, msgCtx] = message.useMessage()

  const { data: instances } = useQuery({
    queryKey: ['instances-for-tmpl'],
    queryFn: () => instanceApi.list({ page_size: 200 }),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['workflow-templates', search],
    queryFn: () => apiClient.get('/workflow-templates/', { params: { search: search || undefined } }).then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d: any) => apiClient.post('/workflow-templates/', d).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['workflow-templates'] }); setModalOpen(false); msgApi.success('模板创建成功') },
    onError: (e: any) => msgApi.error(e.response?.data?.msg || '创建失败'),
  })
  const updateMut = useMutation({
    mutationFn: ({ id, data }: any) => apiClient.put(`/workflow-templates/${id}/`, data).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['workflow-templates'] }); setModalOpen(false); msgApi.success('已更新') },
  })
  const deleteMut = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/workflow-templates/${id}/`).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['workflow-templates'] }); msgApi.success('已删除') },
  })
  const useMut = useMutation({
    mutationFn: (id: number) => apiClient.post(`/workflow-templates/${id}/use/`).then(r => r.data),
  })

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = { ...values, sql_content: sql }
      editId ? updateMut.mutate({ id: editId, data: payload }) : createMut.mutate(payload)
    } catch { /* validation */ }
  }

  const openCreate = () => {
    setEditId(null); setSql(''); form.resetFields()
    form.setFieldsValue({ visibility: 'public', syntax_type: 0 })
    setModalOpen(true)
  }
  const openEdit = (r: any) => {
    setEditId(r.id); setSql(r.sql_content)
    form.setFieldsValue({
      template_name: r.template_name, description: r.description,
      instance_id: r.instance_id, db_name: r.db_name,
      syntax_type: r.syntax_type, visibility: r.visibility,
    })
    setModalOpen(true)
  }

  const handleUseTemplate = (r: any) => {
    useMut.mutate(r.id)
    // 跳转到提交工单页，携带模板数据
    navigate('/workflow/submit', {
      state: {
        template: {
          sql_content: r.sql_content,
          instance_id: r.instance_id,
          db_name: r.db_name,
        }
      }
    })
  }

  const columns = [
    {
      title: '模板名称', dataIndex: 'template_name',
      render: (v: string, r: any) => (
        <Space direction="vertical" size={0}>
          <Text strong>{v}</Text>
          {r.description && <Text type="secondary" style={{ fontSize: 11 }}>{r.description}</Text>}
        </Space>
      ),
    },
    {
      title: '默认实例/库', key: 'target', width: 160,
      render: (_: any, r: any) => r.instance_id ? (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 12 }}>ID:{r.instance_id}</Text>
          {r.db_name && <Text type="secondary" style={{ fontSize: 11 }}>{r.db_name}</Text>}
        </Space>
      ) : <Text type="secondary">不指定</Text>,
    },
    {
      title: 'SQL 预览', dataIndex: 'sql_content', ellipsis: true, width: 300,
      render: (v: string) => (
        <Text code style={{ fontSize: 11, color: '#1558A8' }}>
          {v.slice(0, 80)}{v.length > 80 ? '...' : ''}
        </Text>
      ),
    },
    {
      title: '可见范围', dataIndex: 'visibility', width: 90,
      render: (v: string) => v === 'public'
        ? <Tag color="blue">公开</Tag>
        : <Tag color="default">仅我</Tag>,
    },
    {
      title: '使用次数', dataIndex: 'use_count', width: 80,
      render: (v: number) => <Badge count={v} showZero color="#1558A8" />,
    },
    {
      title: '操作', width: 140,
      render: (_: any, r: any) => (
        <Space size={4}>
          <Button size="small" type="primary" icon={<CopyOutlined />}
            onClick={() => handleUseTemplate(r)}>使用</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          <Popconfirm title="确认删除？" onConfirm={() => deleteMut.mutate(r.id)}>
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
        <Title level={2} style={{ margin: 0 }}>工单模板</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建模板</Button>
      </div>

      <Card style={{ marginBottom: 12, borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: '12px 16px' } }}>
        <Input.Search placeholder="搜索模板名称" allowClear style={{ width: 300 }}
          onSearch={setSearch} onChange={e => !e.target.value && setSearch('')} />
      </Card>

      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: 0 } }}>
        <Table dataSource={data?.items} columns={columns} rowKey="id" loading={isLoading}
          pagination={{ total: data?.total, pageSize: 20, showSizeChanger: false }} />
      </Card>

      <Modal title={editId ? '编辑工单模板' : '新建工单模板'}
        open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)}
        confirmLoading={createMut.isPending || updateMut.isPending} width={680}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="template_name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="如：清理7天前数据" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input placeholder="可选，说明此模板的用途和注意事项" />
          </Form.Item>
          <Space style={{ width: '100%', display: 'flex' }}>
            <Form.Item name="instance_id" label="默认实例（可选）" style={{ flex: 1 }}>
              <Select placeholder="不指定" allowClear showSearch optionFilterProp="label">
                {instances?.items?.map((i: any) => (
                  <Option key={i.id} value={i.id} label={i.instance_name}>{i.instance_name}</Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="db_name" label="默认数据库（可选）" style={{ flex: 1 }}>
              <Input placeholder="不指定" />
            </Form.Item>
          </Space>
          <Space style={{ width: '100%', display: 'flex' }}>
            <Form.Item name="syntax_type" label="SQL 类型" style={{ flex: 1 }} initialValue={0}>
              <Select>
                <Option value={0}>未知</Option>
                <Option value={1}>DDL</Option>
                <Option value={2}>DML</Option>
              </Select>
            </Form.Item>
            <Form.Item name="visibility" label="可见范围" style={{ flex: 1 }} initialValue="public">
              <Select>
                <Option value="public">公开（所有人可用）</Option>
                <Option value="private">私有（仅我可用）</Option>
              </Select>
            </Form.Item>
          </Space>
          <Form.Item label={<span>SQL 模板 <span style={{ color: '#f5222d' }}>*</span></span>} required>
            <div style={{ border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden' }}>
              <Editor height="200px" defaultLanguage="sql" value={sql}
                onChange={(v) => setSql(v || '')}
                options={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 13, minimap: { enabled: false }, padding: { top: 8 } }} />
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
