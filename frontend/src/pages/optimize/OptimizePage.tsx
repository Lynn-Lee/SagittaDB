import { useState } from 'react'
import { Button, Card, Select, Space, Table, Tag, Typography, message, Alert } from 'antd'
import { BulbOutlined, PlayCircleOutlined } from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useQuery } from '@tanstack/react-query'
import { instanceApi } from '@/api/instance'
import apiClient from '@/api/client'

const { Title } = Typography
const { Option } = Select

const LEVEL_COLOR: Record<string, string> = { error: 'error', warning: 'warning', info: 'processing', ok: 'success' }

export default function OptimizePage() {
  const [instanceId, setInstanceId] = useState<number | undefined>()
  const [dbName, setDbName] = useState<string>('')
  const [sql, setSql] = useState<string>('SELECT * FROM sql_users WHERE 1=1')
  const [advices, setAdvices] = useState<any[]>([])
  const [explainResult, setExplainResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [msgApi, msgCtx] = message.useMessage()

  const { data: instanceData } = useQuery({ queryKey: ['instances-optimize'], queryFn: () => instanceApi.list({ page_size: 200 }) })
  const { data: dbData } = useQuery({ queryKey: ['registered-dbs-optimize', instanceId], queryFn: () => instanceApi.listRegisteredDbs(instanceId!), enabled: !!instanceId })

  const handleAdvice = async () => {
    if (!instanceId) { msgApi.warning('请选择实例'); return }
    setLoading(true)
    try {
      const r = await apiClient.post('/optimize/advice/', { instance_id: instanceId, db_name: dbName, sql })
      setAdvices(r.data.advices || [])
    } catch (e: any) { msgApi.error(e.response?.data?.msg || '分析失败') }
    finally { setLoading(false) }
  }

  const handleExplain = async () => {
    if (!instanceId || !dbName) { msgApi.warning('请选择实例和数据库'); return }
    setLoading(true)
    try {
      const r = await apiClient.post('/optimize/explain/', { instance_id: instanceId, db_name: dbName, sql })
      setExplainResult(r.data)
    } catch (e: any) { msgApi.error(e.response?.data?.detail || 'EXPLAIN 失败') }
    finally { setLoading(false) }
  }

  const adviceCols = [
    { title: '级别', dataIndex: 'level', width: 90, render: (v: string) => <Tag color={LEVEL_COLOR[v]}>{v.toUpperCase()}</Tag> },
    { title: '规则', dataIndex: 'rule', width: 180 },
    { title: '建议', dataIndex: 'message', ellipsis: false },
  ]

  return (
    <div>
      {msgCtx}
      <Title level={2} style={{ margin: '0 0 20px' }}>SQL 优化</Title>
      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)', marginBottom: 16 }} styles={{ body: { padding: '12px 16px' } }}>
        <Space wrap>
          <Select placeholder="选择实例" style={{ minWidth: 220, maxWidth: 360 }} onChange={(v) => { setInstanceId(v); setDbName('') }} showSearch optionFilterProp="label" popupMatchSelectWidth={false}>
            {instanceData?.items?.map((i: any) => <Option key={i.id} value={i.id} label={i.instance_name} title={i.instance_name}><Tag color="blue">{i.db_type.toUpperCase()}</Tag> {i.instance_name}</Option>)}
          </Select>
          <Select placeholder="选择数据库" style={{ minWidth: 160, maxWidth: 360 }} value={dbName || undefined} onChange={setDbName} disabled={!instanceId} showSearch popupMatchSelectWidth={false} optionFilterProp="children">
            {(dbData?.items || []).map((d: any) => (
              <Option key={d.db_name} value={d.db_name} title={d.db_name}>
                {d.db_name}{!d.is_active && <Tag color="default" style={{marginLeft: 4, fontSize: 10}}>已禁用</Tag>}
              </Option>
            ))}
          </Select>
          <Button icon={<BulbOutlined />} onClick={handleAdvice} loading={loading} disabled={!instanceId}>优化建议</Button>
          <Button icon={<PlayCircleOutlined />} onClick={handleExplain} loading={loading} disabled={!instanceId || !dbName}>EXPLAIN 分析</Button>
        </Space>
      </Card>
      <Card title="SQL 输入" style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)', marginBottom: 16 }} styles={{ body: { padding: 0 } }}>
        <Editor height="180px" defaultLanguage="sql" value={sql} onChange={(v) => setSql(v || '')}
          options={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 13, minimap: { enabled: false }, padding: { top: 12 } }} />
      </Card>
      {advices.length > 0 && (
        <Card title="优化建议" style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)', marginBottom: 16 }} styles={{ body: { padding: 0 } }}>
          <Table dataSource={advices.map((r, i) => ({ key: i, ...r }))} columns={adviceCols} size="small" pagination={false} />
        </Card>
      )}
      {explainResult && (
        <Card title={`EXPLAIN 结果（${explainResult.db_type?.toUpperCase()}）`} style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }} styles={{ body: { padding: 0 } }}>
          <Table
            dataSource={(explainResult.rows || []).map((r: any[], i: number) => ({ key: i, ...Object.fromEntries((explainResult.column_list || []).map((c: string, j: number) => [c, r[j]])) }))}
            columns={(explainResult.column_list || []).map((c: string) => ({ title: c, dataIndex: c, key: c, ellipsis: true, width: 140 }))}
            size="small" scroll={{ x: 'max-content' }} pagination={false} />
        </Card>
      )}
    </div>
  )
}
