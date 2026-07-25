import client from './client';

export interface SourceCitation {
  filename: string;
  chunk_text: string;
  score: number;
}

export type ChatMode = 'hybrid' | 'email_only';

// Where an answer's content came from:
//   email_grounded    -> facts from the user's synced emails/documents (cited)
//   general_knowledge -> the LLM's own general knowledge (NOT from the emails)
//   no_emails         -> nothing synced yet
//   error             -> the AI call failed (e.g. rate limit); not persisted to history
export type SourceType = 'email_grounded' | 'general_knowledge' | 'no_emails' | 'error';

export interface ChatMessage {
  id: string;
  question: string;
  answer: string | null;
  sources: SourceCitation[];
  model_used: string | null;
  source_type?: SourceType | null;
  created_at: string;
}

export const chatApi = {
  ask: async (question: string, mode: ChatMode = 'hybrid'): Promise<ChatMessage> => {
    const response = await client.post<ChatMessage>('/api/v1/chat/ask', { question, mode });
    return response.data;
  },

  getHistory: async (): Promise<ChatMessage[]> => {
    const response = await client.get<ChatMessage[]>('/api/v1/chat/history');
    return response.data;
  },

  clearHistory: async (): Promise<void> => {
    await client.delete('/api/v1/chat/history');
  }
};
