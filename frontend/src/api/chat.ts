import client from './client';

export interface SourceCitation {
  filename: string;
  chunk_text: string;
  score: number;
}

export interface ChatMessage {
  id: string;
  question: string;
  answer: string | null;
  sources: SourceCitation[];
  model_used: string | null;
  created_at: string;
}

export const chatApi = {
  ask: async (question: string): Promise<ChatMessage> => {
    const response = await client.post<ChatMessage>('/api/v1/chat/ask', { question });
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
