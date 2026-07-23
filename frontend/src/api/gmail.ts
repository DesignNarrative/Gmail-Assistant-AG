import client from './client';

export interface SyncLogEntry {
  id: string;
  user_id: string;
  sync_type: string;
  status: string;
  emails_synced: number;
  attachments_downloaded: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface SyncStats {
  total_emails: number;
  total_threads: number;
  total_attachments: number;
  total_size_bytes: number;
  latest_sync: SyncLogEntry | null;
}

export const gmailApi = {
  triggerSync: async (): Promise<{ detail: string; sync_job_id: string; status: string; started_at: string }> => {
    const response = await client.post('/api/v1/gmail/sync/trigger');
    return response.data;
  },

  getSyncStatus: async (limit: number = 10): Promise<SyncLogEntry[]> => {
    const response = await client.get(`/api/v1/gmail/sync/status?limit=${limit}`);
    return response.data;
  },

  getSyncStats: async (): Promise<SyncStats> => {
    const response = await client.get('/api/v1/gmail/sync/stats');
    return response.data;
  },

  updateGmailLabel: async (gmail_label: string): Promise<{ detail: string; gmail_label: string }> => {
    const response = await client.put('/api/v1/gmail/settings/label', { gmail_label });
    return response.data;
  }
};
