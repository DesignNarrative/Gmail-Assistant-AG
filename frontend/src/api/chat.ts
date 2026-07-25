import client from './client';

export interface SourceCitation {
  filename: string;
  chunk_text: string;
  score: number;
  // Email metadata (optional; absent for older history rows or non-email chunks)
  subject?: string | null;
  sender?: string | null;
  sender_email?: string | null;
  date?: string | null;
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
  conversation_id?: string | null;
  question: string;
  answer: string | null;
  sources: SourceCitation[];
  model_used: string | null;
  source_type?: SourceType | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string | null;
}

export const chatApi = {
  ask: async (question: string, mode: ChatMode = 'hybrid', conversationId?: string | null): Promise<ChatMessage> => {
    const response = await client.post<ChatMessage>('/api/v1/chat/ask', {
      question,
      mode,
      conversation_id: conversationId ?? null,
    });
    return response.data;
  },

  listConversations: async (): Promise<Conversation[]> => {
    const response = await client.get<Conversation[]>('/api/v1/chat/conversations');
    return response.data;
  },

  getConversationMessages: async (conversationId: string): Promise<ChatMessage[]> => {
    const response = await client.get<ChatMessage[]>(`/api/v1/chat/conversations/${conversationId}`);
    return response.data;
  },

  deleteConversation: async (conversationId: string): Promise<void> => {
    await client.delete(`/api/v1/chat/conversations/${conversationId}`);
  },

  getHistory: async (): Promise<ChatMessage[]> => {
    const response = await client.get<ChatMessage[]>('/api/v1/chat/history');
    return response.data;
  },

  clearHistory: async (): Promise<void> => {
    await client.delete('/api/v1/chat/history');
  }
};
