import api, { extractData } from './api'
import type { ChatMessage, Conversation } from '@/types'

export interface ChatRequest {
  message: string
  conversation_id?: number
  website_url?: string
  include_metrics?: boolean
}

export interface ChatResponse {
  conversation_id: number
  message: string
  tokens_used: number
  audit_triggered?: boolean
  action_buttons?: string[]
}

export const chatService = {
  // Send message - ALWAYS includes metrics for real GSC data (1:1 with Python)
  async sendMessage(message: string, conversationId?: number, websiteUrl?: string): Promise<ChatResponse> {
    const response = await api.post('/chat', {
      message,
      conversation_id: conversationId,
      website_url: websiteUrl,
      include_metrics: true  // Always include metrics for real data (1:1 with Python)
    })
    return extractData(response)
  },

  // Get all conversations
  async getConversations(limit?: number): Promise<Conversation[]> {
    const response = await api.get('/chat/conversations', { params: { limit } })
    const data = extractData(response) as { conversations: Conversation[] }
    return data.conversations || []
  },

  // Get single conversation with messages
  async getConversation(id: number): Promise<{ conversation: Conversation; messages: ChatMessage[] }> {
    const response = await api.get(`/chat/conversations/${id}`)
    return extractData(response)
  },

  // Delete conversation
  async deleteConversation(id: number): Promise<void> {
    await api.delete(`/chat/conversations/${id}`)
  },

  // Update conversation title
  async updateTitle(id: number, title: string): Promise<void> {
    await api.patch(`/chat/conversations/${id}/title`, { title })
  },
}
