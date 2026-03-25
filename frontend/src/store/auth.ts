/**
 * 认证状态管理。
 * 使用 Zustand persist + localStorage 持久化 token。
 * storage name: 'archery2-auth'
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  email: string
  is_superuser: boolean
  totp_enabled: boolean
  permissions: string[]
  resource_groups: number[]
  tenant_id: number
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserInfo | null
  isAuthenticated: boolean
  setTokens: (access: string, refresh: string) => void
  setUser: (user: UserInfo) => void
  logout: () => void
  hasPermission: (perm: string) => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      setTokens: (access, refresh) => {
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true })
      },

      setUser: (user) => set({ user }),

      logout: () => set({
        accessToken: null, refreshToken: null,
        user: null, isAuthenticated: false,
      }),

      hasPermission: (perm: string) => {
        const { user } = get()
        if (!user) return false
        if (user.is_superuser) return true
        return user.permissions.includes(perm)
      },
    }),
    {
      name: 'archery2-auth',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
