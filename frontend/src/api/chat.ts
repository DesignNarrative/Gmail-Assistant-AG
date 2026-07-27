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

// Callbacks fired while an answer streams in token-by-token (SSE).
export interface StreamCallbacks {
  // Knowledge source decided (before any tokens arrive)
  onMeta?: (sourceType: SourceType) => void;
  // A new token arrived; `fullAnswer` is the accumulated text so far
  onToken?: (fullAnswer: string) => void;
  // Discard the partial answer (hybrid fallback / error) and start over
  onReset?: (sourceType: SourceType) => void;
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

  // Streaming variant of ask(): consumes Server-Sent Events from /ask/stream and
  // fires callbacks as tokens arrive. Resolves with the final persisted message.
  // Uses fetch (not axios) because axios cannot read response streams in the browser.
  askStream: async (
    question: string,
    mode: ChatMode = 'hybrid',
    conversationId?: string | null,
    callbacks?: StreamCallbacks
  ): Promise<ChatMessage> => {
    const baseURL = (import.meta as any).env.VITE_API_URL || '';
    const token = localStorage.getItem('abhinav_ai_token');
    const response = await fetch(`${baseURL}/api/v1/chat/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question, mode, conversation_id: conversationId ?? null }),
    });

    if (!response.ok || !response.body) {
      let detail = `Stream request failed (${response.status})`;
      try {
        const err = await response.json();
        if (err?.detail) detail = err.detail;
      } catch { /* non-JSON error body */ }
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullAnswer = '';
    let finalMessage: ChatMessage | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line (\n\n)
      let sep;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const dataLine = frame.split('\n').find((l) => l.startsWith('data: '));
        if (!dataLine) continue;

        let evt: any;
        try {
          evt = JSON.parse(dataLine.slice(6));
        } catch {
          continue; // skip malformed frame
        }

        switch (evt.type) {
          case 'meta':
            callbacks?.onMeta?.(evt.source_type as SourceType);
            break;
          case 'token':
            fullAnswer += evt.content;
            callbacks?.onToken?.(fullAnswer);
            break;
          case 'reset':
            fullAnswer = '';
            callbacks?.onReset?.(evt.source_type as SourceType);
            break;
          case 'done':
            finalMessage = evt.message as ChatMessage;
            break;
        }
      }
    }

    if (!finalMessage) {
      throw new Error('The answer stream ended unexpectedly. Please try again.');
    }
    return finalMessage;
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
