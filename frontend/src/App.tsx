import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import AuthGuard from '@/components/common/AuthGuard'

const LoginPage            = lazy(() => import('@/pages/auth/LoginPage'))
const OAuthCallbackPage    = lazy(() => import('@/pages/auth/OAuthCallbackPage'))
const ProfilePage          = lazy(() => import('@/pages/auth/ProfilePage'))
const MainLayout           = lazy(() => import('@/components/layout/MainLayout'))
const Dashboard            = lazy(() => import('@/pages/dashboard/DashboardPage'))
const WorkflowList         = lazy(() => import('@/pages/workflow/WorkflowList'))
const WorkflowSubmit       = lazy(() => import('@/pages/workflow/WorkflowSubmit'))
const WorkflowDetail       = lazy(() => import('@/pages/workflow/WorkflowDetail'))
const WorkflowTemplatePage = lazy(() => import('@/pages/workflow/WorkflowTemplatePage'))
const QueryPage            = lazy(() => import('@/pages/query/QueryPage'))
const QueryPrivPage        = lazy(() => import('@/pages/query/QueryPrivPage'))
const MonitorPage          = lazy(() => import('@/pages/monitor/MonitorPage'))
const DiagnosticPage       = lazy(() => import('@/pages/diagnostic/DiagnosticPage'))
const SlowlogPage          = lazy(() => import('@/pages/slowlog/SlowlogPage'))
const OptimizePage         = lazy(() => import('@/pages/optimize/OptimizePage'))
const DataDictPage         = lazy(() => import('@/pages/schema/DataDictPage'))
const InstanceList         = lazy(() => import('@/pages/instance/InstanceList'))
const UserManagement       = lazy(() => import('@/pages/system/UserManagement'))
const ResourceGroupManagement = lazy(() => import('@/pages/system/ResourceGroupManagement'))
const SystemConfig         = lazy(() => import('@/pages/system/SystemConfig'))
const MaskingRulePage      = lazy(() => import('@/pages/masking/MaskingRulePage'))
const AuditLog             = lazy(() => import('@/pages/audit/AuditLog'))
const Placeholder          = lazy(() => import('@/pages/Placeholder'))
const ArchivePage          = lazy(() => import('@/pages/archive/ArchivePage'))
const BinlogPage           = lazy(() => import('@/pages/binlog/BinlogPage'))

const Loading = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
    <Spin size="large" />
  </div>
)

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
        <Route path="/" element={<AuthGuard><MainLayout /></AuthGuard>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"            element={<Dashboard />} />
          <Route path="workflow"             element={<WorkflowList />} />
          <Route path="workflow/submit"      element={<WorkflowSubmit />} />
          <Route path="workflow/templates"   element={<WorkflowTemplatePage />} />
          <Route path="workflow/:id"         element={<WorkflowDetail />} />
          <Route path="query"                element={<QueryPage />} />
          <Route path="query/privileges"     element={<QueryPrivPage />} />
          <Route path="monitor"              element={<MonitorPage />} />
          <Route path="slowlog"              element={<SlowlogPage />} />
          <Route path="diagnostic"           element={<DiagnosticPage />} />
          <Route path="archive"              element={<ArchivePage />} />
          <Route path="binlog"               element={<BinlogPage />} />
          <Route path="optimize"             element={<OptimizePage />} />
          <Route path="schema"               element={<DataDictPage />} />
          <Route path="instance"             element={<InstanceList />} />
          <Route path="system/users"         element={<UserManagement />} />
          <Route path="system/groups"        element={<ResourceGroupManagement />} />
          <Route path="system/config"        element={<SystemConfig />} />
          <Route path="masking"              element={<MaskingRulePage />} />
          <Route path="audit"                element={<AuditLog />} />
          <Route path="profile"              element={<ProfilePage />} />
          <Route path="*"                    element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
