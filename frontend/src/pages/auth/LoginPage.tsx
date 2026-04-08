import { useState } from 'react'
import { Button, Form, Input, Alert, Divider, Tooltip, Tag } from 'antd'
import {
  UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone, ArrowLeftOutlined,
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import apiClient from '@/api/client'
import { authApi } from '@/api/auth'

// ── SagittaDB Logo ────────────────────────────────────────────
const SagittaLogo = () => (
  <svg viewBox="0 0 88 88" fill="none" width={80} height={80}>
    <path d="M44 8L79 28V60L44 80L9 60V28L44 8Z" fill="#165DFF"/>
    <path d="M30 38L44 24L58 38" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
    <line x1="44" y1="24" x2="44" y2="64" stroke="white" strokeWidth="4" strokeLinecap="round"/>
    <path d="M33 52H55" stroke="white" strokeWidth="3" strokeLinecap="round"/>
    <path d="M35 58H53" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.5"/>
    <circle cx="44" cy="24" r="3.5" fill="white" opacity="0.85"/>
  </svg>
)

// ── 第三方平台图标 ──────────────────────────────────────────
const DingTalkLogo = ({ size = 20 }: { size?: number }) => (
  <svg viewBox="0 0 200 200" width={size} height={size} fill="none">
    {/* 左翼 */}
    <path d="M18 108 C14 72 36 38 68 26 L56 62 Z" fill="#1677FF"/>
    {/* 右翼 */}
    <path d="M182 108 C186 72 164 38 132 26 L144 62 Z" fill="#1677FF"/>
    {/* 闪电主体 */}
    <path d="M100 18 L72 96 L100 80 L82 166 L140 80 L108 96 Z" fill="#1677FF"/>
  </svg>
)

const FeishuLogo = ({ size = 20 }: { size?: number }) => (
  <svg viewBox="0 0 200 180" width={size * (200/180)} height={size} fill="none">
    {/* 左翼（深蓝色） */}
    <path d="M30 165 C10 120 18 68 52 40 L88 105 Z" fill="#1C6EF2"/>
    {/* 右翼（青绿色） */}
    <path d="M88 105 C100 58 138 28 176 42 C176 42 148 85 110 105 Z" fill="#00C2A8"/>
    {/* 身体连接部分（深青） */}
    <path d="M52 40 C68 24 88 18 106 24 L88 105 Z" fill="#0E4DB1"/>
  </svg>
)

const WeComLogo = ({ size = 20 }: { size?: number }) => (
  <svg viewBox="0 0 200 200" width={size} height={size} fill="none">
    {/* 主气泡（蓝色） */}
    <ellipse cx="115" cy="88" rx="68" ry="52" fill="none" stroke="#1677FF" strokeWidth="10"/>
    <path d="M82 132 L70 162 L108 138" fill="#1677FF"/>
    {/* 4个彩色圆点 2×2 */}
    <circle cx="90"  cy="80" r="11" fill="#07C160"/>
    <circle cx="122" cy="80" r="11" fill="#FA8C16"/>
    <circle cx="90"  cy="104" r="11" fill="#1677FF"/>
    <circle cx="122" cy="104" r="11" fill="#F5222D"/>
    {/* 右上角小辅助气泡 */}
    <ellipse cx="58" cy="60" rx="32" ry="24" fill="none" stroke="#07C160" strokeWidth="7"/>
  </svg>
)

// ── 第三方登录按钮 ──────────────────────────────────────────
const OAuthBtn = ({
  icon, label, color, loading, onClick,
}: { icon: React.ReactNode; label: string; color: string; loading?: boolean; onClick: () => void }) => (
  <Tooltip title={loading ? '正在跳转…' : `使用 ${label} 登录`} placement="top">
    <button onClick={onClick} disabled={loading} style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
      padding: '10px 14px', borderRadius: 10, cursor: loading ? 'not-allowed' : 'pointer',
      background: loading ? `${color}20` : 'rgba(255,255,255,0.05)',
      border: loading ? `1px solid ${color}60` : `1px solid rgba(255,255,255,0.08)`,
      transition: 'all 0.2s',
      flex: 1,
      opacity: loading ? 0.7 : 1,
    }}
    onMouseEnter={e => {
      if (!loading) {
        (e.currentTarget as HTMLElement).style.background = `${color}18`
        ;(e.currentTarget as HTMLElement).style.borderColor = `${color}50`
      }
    }}
    onMouseLeave={e => {
      if (!loading) {
        (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)'
        ;(e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.08)'
      }
    }}>
      <span style={{ fontSize: 20 }}>{loading ? '⏳' : icon}</span>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, color: loading ? color : 'rgba(255,255,255,0.45)',
        letterSpacing: '0.5px',
      }}>{label}</span>
    </button>
  </Tooltip>
)

// ── 主组件 ────────────────────────────────────────────────────
export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { setTokens, setUser } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [oauthLoading, setOauthLoading] = useState('')
  const [error, setError] = useState(
    searchParams.get('oauth_error') ? decodeURIComponent(searchParams.get('oauth_error')!) : ''
  )

  const method = searchParams.get('method')
  const isLdap = method === 'ldap'

  const _doLogin = async (tokenData: { access_token: string; refresh_token: string }) => {
    const { access_token, refresh_token } = tokenData
    const meRes = await apiClient.get('/auth/me/', {
      headers: { Authorization: `Bearer ${access_token}` },
    })
    setTokens(access_token, refresh_token)
    setUser(meRes.data)
    navigate('/dashboard', { replace: true })
  }

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    setError('')
    try {
      const tokenRes = await apiClient.post('/auth/login/', {
        username: values.username,
        password: values.password,
      })
      await _doLogin(tokenRes.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || '用户名或密码错误')
    } finally {
      setLoading(false)
    }
  }

  const handleLdapLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    setError('')
    try {
      const tokenData = await authApi.ldapLogin(values.username, values.password)
      await _doLogin(tokenData)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'LDAP 认证失败')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuth = async (type: string) => {
    if (type === 'ldap') {
      setSearchParams({ method: 'ldap' })
      setError('')
      return
    }
    setOauthLoading(type)
    setError('')
    try {
      const resp = await apiClient.get(`/auth/${type}/authorize/`)
      window.location.href = resp.data.url
    } catch (e: any) {
      setError(e.response?.data?.detail || `${type} 登录暂不可用，请联系管理员开启`)
      setOauthLoading('')
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0F172A',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: "'Inter', 'Noto Sans SC', sans-serif",
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* 背景光晕 */}
      <div style={{
        position: 'absolute', width: 700, height: 700,
        background: 'radial-gradient(circle, rgba(22,93,255,0.18) 0%, transparent 70%)',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        pointerEvents: 'none',
      }} />
      {/* 网格纹理 */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `
          linear-gradient(rgba(22,93,255,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(22,93,255,0.04) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
        pointerEvents: 'none',
      }} />

      {/* 登录卡片 */}
      <div style={{
        position: 'relative', zIndex: 2,
        width: 420,
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(22,93,255,0.15)',
        borderRadius: 20,
        padding: '44px 40px 36px',
        backdropFilter: 'blur(24px)',
      }}>

        {/* ── Logo 区域 ── */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            display: 'inline-block',
            filter: 'drop-shadow(0 0 28px rgba(22,93,255,0.45))',
            marginBottom: 16,
          }}>
            <SagittaLogo />
          </div>
          <div style={{
            fontFamily: "'Inter', sans-serif",
            fontWeight: 800,
            fontSize: 30,
            color: '#FFFFFF',
            letterSpacing: '-1px',
            lineHeight: 1,
          }}>
            SagittaDB
          </div>
          <div style={{
            fontFamily: "'Noto Sans SC', sans-serif",
            fontWeight: 500,
            fontSize: 13,
            color: '#4080FF',
            letterSpacing: '7px',
            marginTop: 7,
            textAlign: 'center',
          }}>
            矢 准 数 据
          </div>
          <div style={{
            fontFamily: "'Inter', sans-serif",
            fontWeight: 300,
            fontSize: 11,
            color: 'rgba(255,255,255,0.28)',
            letterSpacing: '1.5px',
            marginTop: 12,
          }}>
            SagittaDB · Aim at Data, Control with Precision
          </div>
        </div>

        {/* ── 错误提示 ── */}
        {error && (
          <Alert type="error" message={error} showIcon
            style={{
              marginBottom: 16, borderRadius: 8,
              background: 'rgba(245,63,63,0.1)',
              border: '1px solid rgba(245,63,63,0.3)',
            }} />
        )}

        {isLdap ? (
          /* ── LDAP 登录表单 ── */
          <>
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Button
                type="text" size="small" icon={<ArrowLeftOutlined />}
                style={{ color: 'rgba(255,255,255,0.45)', padding: 0 }}
                onClick={() => { setSearchParams({}); setError('') }}
              >
                返回
              </Button>
              <Tag color="blue" style={{ borderRadius: 4, fontSize: 11 }}>🏢 LDAP 认证</Tag>
            </div>
            <Form onFinish={handleLdapLogin} size="large" layout="vertical">
              <Form.Item name="username" rules={[{ required: true, message: '请输入 LDAP 用户名' }]}
                style={{ marginBottom: 14 }}>
                <Input
                  prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                  placeholder="LDAP 用户名"
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, color: '#FFFFFF', height: 46,
                  }}
                />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: '请输入 LDAP 密码' }]}
                style={{ marginBottom: 22 }}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                  placeholder="LDAP 密码"
                  iconRender={v => v
                    ? <EyeTwoTone twoToneColor="#165DFF" />
                    : <EyeInvisibleOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />
                  }
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, color: '#FFFFFF', height: 46,
                  }}
                />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button
                  type="primary" htmlType="submit" loading={loading} block
                  style={{
                    height: 46, borderRadius: 8,
                    background: '#60A5FA', border: 'none',
                    fontWeight: 600, fontSize: 15,
                    letterSpacing: '1px',
                    boxShadow: '0 4px 20px rgba(96,165,250,0.4)',
                  }}
                >
                  LDAP 登 录
                </Button>
              </Form.Item>
            </Form>
          </>
        ) : (
          /* ── 本地登录表单 ── */
          <>
            <Form onFinish={handleLogin} size="large" layout="vertical">
              <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}
                style={{ marginBottom: 14 }}>
                <Input
                  prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                  placeholder="用户名"
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, color: '#FFFFFF', height: 46,
                  }}
                />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}
                style={{ marginBottom: 22 }}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                  placeholder="密码"
                  iconRender={v => v
                    ? <EyeTwoTone twoToneColor="#165DFF" />
                    : <EyeInvisibleOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />
                  }
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8, color: '#FFFFFF', height: 46,
                  }}
                />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Button
                  type="primary" htmlType="submit" loading={loading} block
                  style={{
                    height: 46, borderRadius: 8,
                    background: '#165DFF', border: 'none',
                    fontWeight: 600, fontSize: 15,
                    letterSpacing: '1px',
                    boxShadow: '0 4px 20px rgba(22,93,255,0.4)',
                  }}
                >
                  登 录
                </Button>
              </Form.Item>
            </Form>

            {/* ── 第三方登录 ── */}
            <Divider style={{
              borderColor: 'rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.25)',
              fontSize: 11,
              fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: '1px',
              margin: '20px 0 16px',
            }}>
              其他登录方式
            </Divider>

            <div style={{ display: 'flex', gap: 8 }}>
              <OAuthBtn icon="🏢" label="LDAP"  color="#60A5FA" onClick={() => handleOAuth('ldap')} />
              <OAuthBtn icon="🔑" label="OIDC"  color="#A78BFA" loading={oauthLoading === 'oidc'}     onClick={() => handleOAuth('oidc')} />
              <OAuthBtn icon={<DingTalkLogo />} label="钉钉"  color="#1677FF" loading={oauthLoading === 'dingtalk'} onClick={() => handleOAuth('dingtalk')} />
              <OAuthBtn icon={<FeishuLogo />}  label="飞书"  color="#00C2A8" loading={oauthLoading === 'feishu'}   onClick={() => handleOAuth('feishu')} />
              <OAuthBtn icon={<WeComLogo />}   label="企微"  color="#07C160" loading={oauthLoading === 'wecom'}    onClick={() => handleOAuth('wecom')} />
            </div>
          </>
        )}
      </div>

      {/* 底部版本号 */}
      <div style={{
        position: 'absolute', bottom: 24,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        color: 'rgba(255,255,255,0.15)',
        letterSpacing: '1px',
        zIndex: 2,
        textAlign: 'center',
      }}>
        SagittaDB v2.0.0 · Full Engine Compatibility, End-to-End Observability
      </div>
    </div>
  )
}
