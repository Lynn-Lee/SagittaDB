import { useState, useCallback } from 'react'
import {
  Button, Card, InputNumber, Select, Space, Spin, Table, Tag, Typography, message, Alert,
} from 'antd'
import {
  PlayCircleOutlined, ClearOutlined, HistoryOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import Editor from '@monaco-editor/react'
import { useQuery } from '@tanstack/react-query'
import { instanceApi } from '@/api/instance'
import { queryApi, type QueryResult } from '@/api/query'

const { Text } = Typography
const { Option } = Select

const EDITOR_OPTIONS = {
  fontFamily: '"JetBrains Mono", "Fira Code", Menlo, Consolas, monospace',
  fontSize: 13,
  lineHeight: 22,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  renderLineHighlight: 'line' as const,
  smoothScrolling: true,
  cursorBlinking: 'smooth' as const,
  padding: { top: 12, bottom: 12 },
  automaticLayout: true,
}

export default function QueryPage() {
  const [instanceId, setInstanceId] = useState<number | undefined>()
  const [dbName, setDbName] = useState<string>('')
  const [sql, setSql] = useState<string>('SELECT 1')
  const [limitNum, setLimitNum] = useState<number>(100)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [executing, setExecuting] = useState(false)
  const [msgApi, msgCtx] = message.useMessage()

  const { data: instanceData } = useQuery({
    queryKey: ['instances-for-query'],
    queryFn: () => instanceApi.list({ page_size: 200 }),
  })

  const { data: dbData, isLoading: dbLoading } = useQuery({
    queryKey: ['registered-dbs', instanceId],
    queryFn: () => instanceApi.listRegisteredDbs(instanceId!),
    enabled: !!instanceId,
  })

  const handleExecute = useCallback(async () => {
    if (!instanceId) { msgApi.warning('请先选择实例'); return }
    if (!dbName) { msgApi.warning('请先选择数据库'); return }
    if (!sql.trim()) { msgApi.warning('SQL 不能为空'); return }

    setExecuting(true)
    setResult(null)
    try {
      const res = await queryApi.execute({ instance_id: instanceId, db_name: dbName, sql, limit_num: limitNum })
      setResult(res)
      if (res.error) {
        msgApi.error(`执行失败：${res.error}`)
      } else {
        msgApi.success(`查询成功，${res.affected_rows} 行，耗时 ${res.cost_time_ms}ms`)
      }
    } catch (e: any) {
      msgApi.error(e.response?.data?.msg || e.response?.data?.detail || '查询失败')
    } finally {
      setExecuting(false)
    }
  }, [instanceId, dbName, sql, limitNum, msgApi])

  const resultColumns = result?.column_list.map((col, idx) => ({
    title: col,
    dataIndex: idx,
    key: col,
    ellipsis: true,
    width: 150,
    render: (v: any) => v === null ? <Text type="secondary" italic>NULL</Text> : String(v),
  })) ?? []

  const resultRows = result?.rows.map((row, i) => ({
    key: i,
    ...Object.fromEntries(row.map((v: any, j: number) => [j, v])),
  })) ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {msgCtx}
      <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: '12px 16px' } }}>
        <Space wrap>
          <Select placeholder="选择实例" style={{ minWidth: 220, maxWidth: 360 }}
            popupMatchSelectWidth={false}
            onChange={(v) => { setInstanceId(v); setDbName('') }} showSearch optionFilterProp="label">
            {instanceData?.items?.map((inst: any) => (
              <Option key={inst.id} value={inst.id} label={inst.instance_name} style={{ whiteSpace: 'normal', wordBreak: 'break-all' }}>
                <Space>
                  <Tag color="blue" style={{ fontSize: 11 }}>{inst.db_type.toUpperCase()}</Tag>
                  {inst.instance_name}
                </Space>
              </Option>
            ))}
          </Select>
          <Select placeholder="选择数据库" style={{ minWidth: 180, maxWidth: 400 }} value={dbName || undefined}
            popupMatchSelectWidth={false}
            onChange={setDbName} loading={dbLoading} disabled={!instanceId} showSearch
            optionFilterProp="children">
            {(dbData?.items || []).map((d: any) => (
              <Option key={d.db_name} value={d.db_name} title={d.db_name}>
                {d.db_name}{!d.is_active && <Tag color="default" style={{marginLeft: 4, fontSize: 10}}>已禁用</Tag>}
              </Option>
            ))}
          </Select>
          <Space>
            <Text type="secondary" style={{ fontSize: 13 }}>行数上限</Text>
            <InputNumber min={1} max={10000} value={limitNum}
              onChange={(v) => v && setLimitNum(v)} style={{ width: 90 }} />
          </Space>
          <Button type="primary" icon={<PlayCircleOutlined />} loading={executing}
            onClick={handleExecute} disabled={!instanceId || !dbName}>
            执行
          </Button>
          <Button icon={<ClearOutlined />} onClick={() => { setSql(''); setResult(null) }}>清空</Button>
        </Space>
      </Card>

      <Card title="SQL 编辑器" style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: 0 } }}>
        <Editor height="200px" defaultLanguage="sql" value={sql}
          onChange={(v) => setSql(v || '')} options={EDITOR_OPTIONS} />
      </Card>

      <Card
        title={result ? (
          <Space>
            <HistoryOutlined /><span>查询结果</span>
            {result.error
              ? <Tag color="error">执行失败</Tag>
              : <><Tag color="success">{result.affected_rows} 行</Tag>
                  <Tag icon={<ClockCircleOutlined />}>{result.cost_time_ms}ms</Tag>
                  {result.is_masked && <Tag color="warning">已脱敏</Tag>}</>}
          </Space>
        ) : <Space><HistoryOutlined /><span>结果</span></Space>}
        style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: 0 } }}>
        {executing && <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spin tip="执行中..." /></div>}
        {result && !executing && (
          result.error
            ? <Alert type="error" showIcon message="执行失败" description={result.error} style={{ margin: 16, borderRadius: 8 }} />
            : <Table dataSource={resultRows} columns={resultColumns} size="small"
                scroll={{ x: 'max-content', y: 300 }} pagination={false} />
        )}
        {!result && !executing && (
          <div style={{ padding: 40, textAlign: 'center', color: '#AEAEB2' }}>选择实例和数据库，输入 SQL 后点击执行</div>
        )}
      </Card>
    </div>
  )
}
