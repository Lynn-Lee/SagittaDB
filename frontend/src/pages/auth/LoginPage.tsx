import { useState } from 'react'
import { Button, Form, Input, Alert, Divider, Tooltip } from 'antd'
import {
  UserOutlined, LockOutlined, EyeInvisibleOutlined, EyeTwoTone,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import apiClient from '@/api/client'

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

// ── 第三方登录按钮 ──────────────────────────────────────────
const OAuthBtn = ({
  icon, label, color, onClick,
}: { icon: React.ReactNode; label: string; color: string; onClick: () => void }) => (
  <Tooltip title={`使用 ${label} 登录`} placement="top">
    <button onClick={onClick} style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
      padding: '10px 14px', borderRadius: 10, cursor: 'pointer',
      background: 'rgba(255,255,255,0.05)',
      border: `1px solid rgba(255,255,255,0.08)`,
      transition: 'all 0.2s',
      flex: 1,
    }}
    onMouseEnter={e => {
      (e.currentTarget as HTMLElement).style.background = `${color}18`
      ;(e.currentTarget as HTMLElement).style.borderColor = `${color}50`
    }}
    onMouseLeave={e => {
      (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)'
      ;(e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.08)'
    }}>
      <span style={{ fontSize: 20 }}>{icon}</span>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, color: 'rgba(255,255,255,0.45)',
        letterSpacing: '0.5px',
      }}>{label}</span>
    </button>
  </Tooltip>
)

// ── 主组件 ────────────────────────────────────────────────────
export default function LoginPage() {
  const navigate = useNavigate()
  const { setTokens, setUser } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    setError('')
    try {
      const tokenRes = await apiClient.post('/auth/login/', {
        username: values.username,
        password: values.password,
      })
      const { access_token, refresh_token } = tokenRes.data
      const meRes = await apiClient.get('/auth/me/', {
        headers: { Authorization: `Bearer ${access_token}` },
      })
      setTokens(access_token, refresh_token)
      setUser(meRes.data)
      navigate('/dashboard', { replace: true })
    } catch (e: any) {
      setError(e.response?.data?.detail || '用户名或密码错误')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuth = (type: string) => {
    // 跳转到对应 OAuth 入口（后续接入时替换为真实 URL）
    const routes: Record<string, string> = {
      ldap:    '/login?method=ldap',
      oidc:    '/login?method=oidc',
      dingtalk:'/login?method=dingtalk',
      feishu:  '/login?method=feishu',
      wecom:   '/login?method=wecom',
    }
    window.location.href = routes[type] || '/login'
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
          {/* Logo 图标 */}
          <div style={{
            display: 'inline-block',
            filter: 'drop-shadow(0 0 28px rgba(22,93,255,0.45))',
            marginBottom: 16,
          }}>
            <SagittaLogo />
          </div>

          {/* 品牌名 */}
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

          {/* 中文副标题 — 紧贴品牌名居中 */}
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

          {/* Slogan */}
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

        {/* ── 登录表单 ── */}
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
          <OAuthBtn icon="🏢" label="LDAP"    color="#60A5FA" onClick={() => handleOAuth('ldap')} />
          <OAuthBtn icon="🔑" label="OIDC"    color="#A78BFA" onClick={() => handleOAuth('oidc')} />
          <OAuthBtn icon="🔔" label="钉钉"    color="#1677FF" onClick={() => handleOAuth('dingtalk')} />
          <OAuthBtn icon="🦅" label="飞书"    color="#00B42A" onClick={() => handleOAuth('feishu')} />
          <OAuthBtn icon="💼" label="企微"    color="#07C160" onClick={() => handleOAuth('wecom')} />
        </div>
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
