import { useState } from 'react'
import {
  Card, Col, Row, Select, Space, Spin, Table, Tag, Tree, Typography, message,
} from 'antd'
import {
  DatabaseOutlined, TableOutlined, FieldBinaryOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { instanceApi } from '@/api/instance'
import apiClient from '@/api/client'

const { Title, Text } = Typography
const { Option } = Select

export default function DataDictPage() {
  const [instanceId, setInstanceId] = useState<number | undefined>()
  const [dbName, setDbName] = useState<string>('')
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [msgApi, msgCtx] = message.useMessage()

  const { data: instances } = useQuery({
    queryKey: ['instances-for-dict'],
    queryFn: () => instanceApi.list({ page_size: 200 }),
  })

  const { data: dbData } = useQuery({
    queryKey: ['registered-dbs-dict', instanceId],
    queryFn: () => instanceApi.listRegisteredDbs(instanceId!),
    enabled: !!instanceId,
  })

  const { data: tableData, isLoading: tableLoading } = useQuery({
    queryKey: ['tables-dict', instanceId, dbName],
    queryFn: () => apiClient.get(`/instances/${instanceId}/tables/`, { params: { db_name: dbName } }).then(r => r.data),
    enabled: !!instanceId && !!dbName,
  })

  const { data: columnData, isLoading: colLoading } = useQuery({
    queryKey: ['columns-dict', instanceId, dbName, selectedTable],
    queryFn: () => apiClient.get(`/instances/${instanceId}/columns/`, {
      params: { db_name: dbName, tb_name: selectedTable }
    }).then(r => r.data),
    enabled: !!instanceId && !!dbName && !!selectedTable,
  })

  const tables: string[] = tableData?.tables || []
  const columns: any[] = columnData?.columns || []

  const treeData = tables.map(t => ({
    key: t, title: (
      <Space size={4}>
        <TableOutlined style={{ color: '#1558A8' }} />
        <Text style={{ fontSize: 13 }}>{t}</Text>
      </Space>
    ),
    icon: null,
  }))

  const colTableCols = [
    { title: '列名', dataIndex: 'column_name', key: 'column_name',
      render: (v: string) => <Text code style={{ fontSize: 12 }}>{v}</Text> },
    { title: '数据类型', dataIndex: 'column_type', key: 'column_type', width: 150,
      render: (v: string) => <Tag color="geekblue" style={{ fontSize: 11 }}>{v}</Tag> },
    { title: '可空', dataIndex: 'is_nullable', key: 'is_nullable', width: 70,
      render: (v: string | boolean) => {
        const nullable = v === 'YES' || v === true
        return <Tag color={nullable ? 'default' : 'red'}>{nullable ? 'YES' : 'NO'}</Tag>
      }},
    { title: '默认值', dataIndex: 'column_default', key: 'column_default', width: 120,
      render: (v: any) => v !== null && v !== undefined
        ? <Text code style={{ fontSize: 11 }}>{String(v)}</Text>
        : <Text type="secondary" style={{ fontSize: 11 }}>NULL</Text> },
    { title: '注释', dataIndex: 'column_comment', key: 'column_comment', ellipsis: true,
      render: (v: string) => v || <Text type="secondary">—</Text> },
  ]

  return (
    <div>
      {msgCtx}
      <Title level={2} style={{ marginBottom: 20 }}>数据字典</Title>

      {/* 选择条件 */}
      <Card style={{ marginBottom: 16, borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
        styles={{ body: { padding: '12px 16px' } }}>
        <Space wrap>
          <Select placeholder="选择实例" style={{ width: 220 }} value={instanceId}
            onChange={(v) => { setInstanceId(v); setDbName(''); setSelectedTable('') }}
            showSearch optionFilterProp="label">
            {instances?.items?.map((i: any) => (
              <Option key={i.id} value={i.id} label={i.instance_name}>
                <Tag color="blue" style={{ fontSize: 11 }}>{i.db_type.toUpperCase()}</Tag>
                {i.instance_name}
              </Option>
            ))}
          </Select>
          <Select placeholder="选择数据库" style={{ width: 160 }}
            value={dbName || undefined} onChange={(v) => { setDbName(v); setSelectedTable('') }}
            disabled={!instanceId} showSearch>
            {(dbData?.items || []).map((d: any) => (
              <Option key={d.db_name} value={d.db_name}>{d.db_name}</Option>
            ))}
          </Select>
          {tableLoading && <Spin size="small" />}
          {tables.length > 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              共 {tables.length} 张表
              {selectedTable && `，已选：${selectedTable}`}
            </Text>
          )}
        </Space>
      </Card>

      {dbName && (
        <Row gutter={16}>
          {/* 表列表 */}
          <Col xs={24} md={7}>
            <Card title={<Space><DatabaseOutlined />{dbName}</Space>}
              style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
              styles={{ body: { padding: 0, maxHeight: 'calc(100vh - 320px)', overflowY: 'auto' } }}>
              {tableLoading ? (
                <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div>
              ) : (
                <Tree
                  treeData={treeData}
                  selectedKeys={selectedTable ? [selectedTable] : []}
                  onSelect={(keys) => setSelectedTable(keys[0] as string || '')}
                  style={{ padding: '8px 0' }}
                  blockNode
                />
              )}
            </Card>
          </Col>

          {/* 列结构 */}
          <Col xs={24} md={17}>
            <Card
              title={selectedTable ? (
                <Space>
                  <FieldBinaryOutlined />
                  <Text>{selectedTable}</Text>
                  {columns.length > 0 && <Tag>{columns.length} 列</Tag>}
                </Space>
              ) : '请选择一张表查看字段详情'}
              style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}
              styles={{ body: { padding: 0 } }}>
              {selectedTable ? (
                <Table
                  dataSource={columns.map((c, i) => ({ key: i, ...c }))}
                  columns={colTableCols}
                  loading={colLoading}
                  size="small"
                  pagination={{ pageSize: 50, showSizeChanger: false }}
                />
              ) : (
                <div style={{ padding: 60, textAlign: 'center', color: '#AEAEB2' }}>
                  <DatabaseOutlined style={{ fontSize: 40, marginBottom: 12 }} />
                  <div>从左侧选择一张表查看字段结构</div>
                </div>
              )}
            </Card>
          </Col>
        </Row>
      )}

      {!dbName && (
        <Card style={{ borderRadius: 12, border: '1px solid rgba(0,0,0,0.08)' }}>
          <div style={{ padding: '60px 0', textAlign: 'center', color: '#AEAEB2' }}>
            <DatabaseOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <div style={{ fontSize: 15 }}>请先选择实例和数据库</div>
          </div>
        </Card>
      )}
    </div>
  )
}
