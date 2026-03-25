import apiClient from './client'

// ── 用户 ──────────────────────────────────────────────────────
export const userApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; is_active?: boolean }) =>
    apiClient.get('/system/users/', { params }).then(r => r.data),

  get: (id: number) =>
    apiClient.get(`/system/users/${id}/`).then(r => r.data),

  create: (data: {
    username: string; password: string; display_name?: string
    email?: string; phone?: string; is_superuser?: boolean; resource_group_ids?: number[]
  }) => apiClient.post('/system/users/', data).then(r => r.data),

  update: (id: number, data: any) =>
    apiClient.put(`/system/users/${id}/`, data).then(r => r.data),

  delete: (id: number) =>
    apiClient.delete(`/system/users/${id}/`).then(r => r.data),

  grantPermissions: (id: number, permission_codes: string[]) =>
    apiClient.post(`/system/users/${id}/permissions/grant/`, { permission_codes }).then(r => r.data),

  revokePermissions: (id: number, permission_codes: string[]) =>
    apiClient.post(`/system/users/${id}/permissions/revoke/`, { permission_codes }).then(r => r.data),
}

// ── 资源组 ────────────────────────────────────────────────────
export const resourceGroupApi = {
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    apiClient.get('/system/resource-groups/', { params }).then(r => r.data),

  create: (data: { group_name: string; group_name_cn?: string; ding_webhook?: string; feishu_webhook?: string }) =>
    apiClient.post('/system/resource-groups/', data).then(r => r.data),

  update: (id: number, data: any) =>
    apiClient.put(`/system/resource-groups/${id}/`, data).then(r => r.data),

  delete: (id: number) =>
    apiClient.delete(`/system/resource-groups/${id}/`).then(r => r.data),
}

// ── 权限列表 ──────────────────────────────────────────────────
export const permissionApi = {
  list: () => apiClient.get('/system/permissions/').then(r => r.data),
}

// ── 系统初始化 ────────────────────────────────────────────────
export const systemApi = {
  init: () => apiClient.post('/system/init/').then(r => r.data),
}
