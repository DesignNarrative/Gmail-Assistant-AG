import client from './client';

export interface AuditLogItem {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface AuditLogsResponse {
  total: number;
  page: number;
  limit: number;
  logs: AuditLogItem[];
}

export interface SystemStatusResponse {
  database_status: string;
  redis_status: string;
  celery_worker_status: string;
  vector_search_engine: string;
  llm_model: string;
  active_label: string;
  debug_mode: boolean;
}

export const auditApi = {
  getLogs: async (params?: { page?: number; limit?: number; action?: string }): Promise<AuditLogsResponse> => {
    const response = await client.get<AuditLogsResponse>('/api/v1/audit/logs', { params });
    return response.data;
  },

  getSystemStatus: async (): Promise<SystemStatusResponse> => {
    const response = await client.get<SystemStatusResponse>('/api/v1/audit/system-status');
    return response.data;
  }
};
