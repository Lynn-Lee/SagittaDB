export const DB_TYPE_LABELS: Record<string, string> = {
  mysql: 'MySQL',
  pgsql: 'PostgreSQL',
  postgresql: 'PostgreSQL',
  oracle: 'Oracle',
  tidb: 'TiDB',
  doris: 'Doris',
  mssql: 'MSSQL',
  clickhouse: 'ClickHouse',
  mongo: 'MongoDB',
  mongodb: 'MongoDB',
  cassandra: 'Cassandra',
  redis: 'Redis',
  elasticsearch: 'Elasticsearch',
  opensearch: 'OpenSearch',
}

export function formatDbTypeLabel(dbType?: string | null): string {
  if (!dbType) return '-'
  return DB_TYPE_LABELS[dbType.toLowerCase()] || dbType
}
