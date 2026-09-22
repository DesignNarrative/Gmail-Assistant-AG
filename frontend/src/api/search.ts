import client from './client';

export interface SearchResultItem {
  id: string;
  type: 'email' | 'document';
  title: string;
  snippet: string;
  sender?: string | null;
  date?: string | null;
  filename?: string | null;
  mime_type?: string | null;
  email_id?: string | null;
}

export interface AttachmentDetail {
  id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  has_extracted_text: boolean;
  extracted_text_preview?: string | null;
}

export interface EmailDetailResponse {
  id: string;
  subject: string;
  sender_name?: string | null;
  sender_email: string;
  recipients: Array<{ name?: string; email: string } | string>;
  cc: Array<{ name?: string; email: string } | string>;
  date_sent?: string | null;
  date_received?: string | null;
  body_text?: string | null;
  snippet?: string | null;
  has_attachments: boolean;
  attachments: AttachmentDetail[];
}

export interface GlobalSearchResponse {
  query: string;
  total_results: number;
  page: number;
  limit: number;
  results: SearchResultItem[];
}

export interface AnalyticsSummaryResponse {
  total_emails: number;
  total_threads: number;
  total_attachments: number;
  total_processed_documents: number;
  total_vector_chunks: number;
  document_type_breakdown: Record<string, number>;
  last_sync_status: string;
  last_sync_time: string | null;
}

export const searchApi = {
  search: async (params: {
    q?: string;
    sender?: string;
    has_attachment?: boolean;
    doc_type?: string;
    page?: number;
    limit?: number;
  }): Promise<GlobalSearchResponse> => {
    const response = await client.get<GlobalSearchResponse>('/api/v1/search/global', { params });
    return response.data;
  },

  getAnalytics: async (): Promise<AnalyticsSummaryResponse> => {
    const response = await client.get<AnalyticsSummaryResponse>('/api/v1/search/analytics/summary');
    return response.data;
  },

  getEmailDetail: async (emailId: string): Promise<EmailDetailResponse> => {
    const response = await client.get<EmailDetailResponse>(`/api/v1/search/emails/${emailId}`);
    return response.data;
  }
};
