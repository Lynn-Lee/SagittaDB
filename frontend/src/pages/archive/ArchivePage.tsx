import { useState } from 'react'
import {
  Alert, Button, Card, Col, Divider, Form, Input, InputNumber,
  Modal, Row, Select, Space, Steps, Switch, Table, Tag, Typography, message,
} from 'antd'
import {
  DeleteOutlined, ExperimentOutlined, PlayCircleOutlined,
  QuestionCircleOutlined, WarningOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation } from '@tanstack/react-query'
import { instanceApi } from '@/api/instance'
import apiClient from '@/api/client'

const { Title, Text, Paragraph } = Typography
const { Option } = Select

const MODE_COLORS: Record<string, string> = { purge: 'red', dest: 'blue' }
const DB_SUPPORT_COLORS: Record<string, string> = {
  true: 'success', false: 'default',
}

export default function ArchivePage() {
  const [form] = Form.useForm()
  const [step, setStep] = useState(0)
  const [estimateResult, setEstimateResult] = useState<any>(null)
  const [runResult, setRunResult] = useState<any>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [srcInstanceId, setSrcInstanceId] = useState<number | undefined>()
  const [mode, setMode] = useState('purge')
  const [msgApi, msgCtx] = message.useMessage()

  // 支持矩阵
  const { data: supportData } = useQuery({
    queryKey: ['archive-support'],
    queryFn: () => apiClient.get('/archive/support/').then(r => r.data),
  })

  // 实例列表
  const { data: instances } = useQuery({
    queryKey: ['instances-for-archive'],
    queryFn: () => instanceApi.list({ page_size: 200 }),
  })

  // 源实例数据库列表
  const { data: srcDbs } = useQuery({
    queryKey: ['src-dbs-archive', srcInstanceId],
    queryFn: () => instanceApi.listRegisteredDbs(srcInstanceId!),
    enabled: !!srcInstanceId,
  })

  // 估算
  const estimateMut = useMutation({
    mutationFn: (data: any) => apiClient.post('/archive/estimate/', data).then(r => r.data),
    onSuccess: (res) => {
      setEstimateResult(res)
      if (res.supported === false) {
        msgApi.warning(res.msg)
      } else {
        setStep(1)
        msgApi.info(`估算完成：${res.msg}`)
      }
    },
    onError: (e: any) => msgApi.error(e.response?.data?.detail || '估算失败'),
  })

  // 执行归档
  const runMut = useMutation({
    mutationFn: (data: any) => apiClient.post('/archive/run/', data).then(r => r.data),
    onSuccess: (res) => {
      setRunResult(res)
      setConfirmOpen(false)
      setStep(2)
      if (res.success) {
        msgApi.success(res.msg)
      } else {
        msgApi.error(res.msg)
      }
    },
    onError: (e: any) => {
      setConfirmOpen(false)
      msgApi.error(e.response?.data?.detail || '归档执行失败')
    },
  })

  const handleEstimate = async () => {
    try {
      const values = await form.validateFields()
      estimateMut.mutate({ ...values, dry_run: true })
    } catch { /* validation */ }
  }

  const handleRun = async () => {
    try {
      const values = await form.validateFields()
      runMut.mutate({ ...values, dry_run: false })
    } catch { /* validation */ }
  }

  const handleReset = () => {
    setStep(0); setEstimateResult(null); setRunResult(null)
    form.resetFields()
  }

  // 支持矩阵表格
  const supportCols = [
    { title: '数据库类型', dataIndex: 'db_type', key: 'db_type',
      render: (v: string) => <Tag>{v.toUpperCase()}</Tag> },
    { title: 'purge（直接删除）', dataIndex: 'purge', key: 'purge', width: 140,
      render: (v: boolean) => v
        ? <Tag color="success">✅ 支持</Tag>
        : <Tag color="default">❌ 不支持</Tag> },
    { title: 'dest（迁移到目标）', dataIndex: 'dest', key: 'dest', width: 140,
      render: (v: boolean) => v
        ? <Tag color="success">✅ 支持</Tag>
        : <Tag color="default">❌ 不支持</Tag> },
    { title: '说明', dataIndex: 'reason', key: 'reason',
      render: (v: string) => v ? <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text> : null },
  ]

  const supportRows = supportData
    ? Object.entries(supportData.support).map(([db_type, cfg]: any) => ({
        key: db_type, db_type, ...cfg,
      }))
    : []

  return (
    <div>
      {msgCtx}
      <Title level={2} style={{ marginBottom: 4 }}>数据归档</Title>
      <Text type="secondary" style={{ fontSize: 13 }}>
        分批删除或迁移历史数据，默认先估算影响范围，确认后再执行
      </Text>

      <Row gutter={16} style={{ marginTop: 20 }}>
        {/* 左侧：操作面板 */}
        <Col xs={24} lg={14}>
          <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)', marginBottom: 16 }}>
            <Steps current={step} size="small" style={{ marginBottom: 24 }}
              items={[
                { title: '配置归档参数' },
                { title: '确认影响范围', description: estimateResult ? `${estimateResult.count} 行` : '' },
                { title: '归档完成' },
              ]}
            />

            <Form form={form} layout="vertical"
              initialValues={{ archive_mode: 'purge', batch_size: 1000, sleep_ms: 100 }}>

              <Row gutter={12}>
                <Col span={14}>
                  <Form.Item name="source_instance_id" label="源实例" rules={[{ required: true }]}>
                    <Select placeholder="选择实例" showSearch optionFilterProp="label"
                      onChange={(v) => { setSrcInstanceId(v); form.setFieldValue('source_db', undefined) }}>
                      {instances?.items?.map((i: any) => (
                        <Option key={i.id} value={i.id} label={i.instance_name}>
                          <Tag color="blue" style={{ fontSize: 11 }}>{i.db_type.toUpperCase()}</Tag>
                          {i.instance_name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={10}>
                  <Form.Item name="source_db" label="数据库" rules={[{ required: true }]}>
                    <Select placeholder="选择数据库" disabled={!srcInstanceId} showSearch>
                      {srcDbs?.items?.map((d: any) => (
                        <Option key={d.db_name} value={d.db_name}>{d.db_name}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item name="source_table" label="表名" rules={[{ required: true }]}>
                <Input placeholder="如：order_logs" />
              </Form.Item>

              <Form.Item name="condition" label="归档条件（WHERE 子句）" rules={[{ required: true }]}>
                <Input.TextArea rows={2}
                  placeholder="如：created_at < '2024-01-01'（MongoDB 填 JSON：{&quot;created_at&quot;: {&quot;$lt&quot;: ...}}）" />
              </Form.Item>

              <Row gutter={12}>
                <Col span={8}>
                  <Form.Item name="archive_mode" label="归档模式">
                    <Select onChange={setMode}>
                      <Option value="purge"><Tag color="red">purge</Tag> 直接删除</Option>
                      <Option value="dest"><Tag color="blue">dest</Tag> 迁移到目标</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="batch_size" label="批次大小">
                    <InputNumber min={1} max={10000} style={{ width: '100%' }} addonAfter="行/批" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="sleep_ms" label="批次间隔">
                    <InputNumber min={0} max={10000} style={{ width: '100%' }} addonAfter="ms" />
                  </Form.Item>
                </Col>
              </Row>

              {mode === 'dest' && (
                <Card size="small" style={{ background: '#f5f5f7', marginBottom: 16 }}>
                  <Text strong>目标实例配置</Text>
                  <Row gutter={12} style={{ marginTop: 12 }}>
                    <Col span={14}>
                      <Form.Item name="dest_instance_id" label="目标实例" rules={[{ required: mode === 'dest' }]}>
                        <Select placeholder="选择目标实例" showSearch optionFilterProp="label">
                          {instances?.items?.map((i: any) => (
                            <Option key={i.id} value={i.id} label={i.instance_name}>{i.instance_name}</Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={10}>
                      <Form.Item name="dest_db" label="目标数据库">
                        <Input placeholder="不填则同源库名" />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item name="dest_table" label="目标表名" style={{ marginBottom: 0 }}>
                    <Input placeholder="不填则同源表名" />
                  </Form.Item>
                </Card>
              )}

              {/* 估算结果 */}
              {estimateResult && (
                <Alert
                  type={estimateResult.supported === false ? 'error' : estimateResult.count > 10000 ? 'warning' : 'info'}
                  showIcon
                  message={estimateResult.msg}
                  description={estimateResult.count > 10000
                    ? `影响 ${estimateResult.count} 行，数据量较大，请确认批次配置`
                    : estimateResult.count > 0
                    ? `将分批处理，每批 ${form.getFieldValue('batch_size')} 行`
                    : undefined}
                  style={{ marginBottom: 16 }}
                />
              )}

              {/* 执行结果 */}
              {runResult && (
                <Alert
                  type={runResult.success ? 'success' : 'error'}
                  showIcon icon={runResult.success ? undefined : <WarningOutlined />}
                  message={runResult.msg}
                  style={{ marginBottom: 16 }}
                />
              )}

              <Space>
                <Button icon={<ExperimentOutlined />} loading={estimateMut.isPending}
                  onClick={handleEstimate}>
                  第一步：估算影响范围
                </Button>
                {step >= 1 && estimateResult?.supported !== false && estimateResult?.count > 0 && (
                  <Button type="primary" danger icon={<PlayCircleOutlined />}
                    onClick={() => setConfirmOpen(true)}>
                    第二步：执行归档
                  </Button>
                )}
                {step > 0 && (
                  <Button onClick={handleReset}>重置</Button>
                )}
              </Space>
            </Form>
          </Card>
        </Col>

        {/* 右侧：支持矩阵 */}
        <Col xs={24} lg={10}>
          <Card title={<Space><QuestionCircleOutlined />各数据库归档支持情况</Space>}
            style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
            styles={{ body: { padding: 0 } }}>
            <Table dataSource={supportRows} columns={supportCols}
              size="small" pagination={false}
              rowClassName={(r) => r.purge || r.dest ? '' : 'opacity-50'}
            />
          </Card>
        </Col>
      </Row>

      {/* 执行确认 Modal */}
      <Modal
        title={<Space><WarningOutlined style={{ color: '#f5222d' }} />确认执行归档</Space>}
        open={confirmOpen}
        onOk={handleRun}
        onCancel={() => setConfirmOpen(false)}
        confirmLoading={runMut.isPending}
        okText="确认执行"
        okButtonProps={{ danger: true }}
      >
        <Alert type="warning" showIcon style={{ marginBottom: 16 }}
          message="此操作不可逆，删除/迁移后无法自动恢复！" />
        <Paragraph>
          即将删除 <Text strong>{estimateResult?.count}</Text> 行数据，
          表：<Text code>{form.getFieldValue('source_table')}</Text>，
          条件：<Text code>{form.getFieldValue('condition')}</Text>
        </Paragraph>
        <Text type="secondary">执行前请确认已有数据备份，归档将在后台分批进行。</Text>
      </Modal>
    </div>
  )
}
