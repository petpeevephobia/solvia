import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Send, Bot, User, FileDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Card, Button, Input } from '@/components/ui'
import { chatService } from '@/services/chat'
import { auditService } from '@/services/audit'
import { useWebsiteStore } from '@/stores/websiteStore'
import { clsx } from 'clsx'
import type { ChatMessage } from '@/types'

export default function ChatPage() {
  const [message, setMessage] = useState('')
  const [currentConversationId, setCurrentConversationId] = useState<number | undefined>()
  const [isAuditRunning, setIsAuditRunning] = useState(false)
  const [latestAuditId, setLatestAuditId] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  // Get selected website from store (1:1 with Python - chat requires selected website for metrics)
  const selectedWebsite = useWebsiteStore((state) => state.selectedWebsite)

  // Fetch current conversation messages
  const { data: conversationData } = useQuery({
    queryKey: ['conversation', currentConversationId],
    queryFn: () => currentConversationId ? chatService.getConversation(currentConversationId) : null,
    enabled: !!currentConversationId,
  })

  const messages = conversationData?.messages || []

  // Send message mutation - includes website URL for metrics context (1:1 with Python)
  const sendMutation = useMutation({
    mutationFn: (content: string) => chatService.sendMessage(content, currentConversationId, selectedWebsite || undefined),
    onSuccess: async (response) => {
      // Update conversation ID if this is a new conversation
      if (!currentConversationId) {
        setCurrentConversationId(response.conversation_id)
      }
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      queryClient.invalidateQueries({ queryKey: ['conversation', response.conversation_id] })
      setMessage('')

      // Handle audit trigger - automatically start audit when user requests it (1:1 with Python)
      if (response.audit_triggered && selectedWebsite) {
        setIsAuditRunning(true)
        try {
          const auditResponse = await auditService.startAudit(selectedWebsite)
          setLatestAuditId(auditResponse.audit.id)
          // Invalidate audit queries to refresh the list
          queryClient.invalidateQueries({ queryKey: ['audits'] })
        } catch (error) {
          console.error('Failed to start audit:', error)
        } finally {
          setIsAuditRunning(false)
        }
      }
    },
  })

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (message.trim() && !sendMutation.isPending) {
      sendMutation.mutate(message.trim())
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const startNewConversation = () => {
    setCurrentConversationId(undefined)
  }

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Page header */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-h1 font-heading font-bold text-text-primary">AI Assistant</h1>
          <p className="text-p1 font-sans text-text-secondary mt-1">Get SEO recommendations and insights</p>
        </div>
        <Button variant="secondary" onClick={startNewConversation}>
          New Chat
        </Button>
      </div>

      {/* Warning if no website selected */}
      {!selectedWebsite && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-yellow-800 text-p2 font-sans">
            No website selected. Please select a website in Settings to get personalized SEO data.
          </p>
        </div>
      )}

      {/* Audit status banner */}
      {isAuditRunning && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2">
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
          <p className="text-blue-800 text-p2 font-sans">Running SEO audit... This may take a few minutes.</p>
        </div>
      )}

      {/* Audit completed banner with PDF download */}
      {latestAuditId && !isAuditRunning && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center justify-between">
          <p className="text-green-800 text-p2 font-sans">Audit completed successfully!</p>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate(`/audit/${latestAuditId}`)}
          >
            <FileDown className="w-4 h-4 mr-2" />
            View Report
          </Button>
        </div>
      )}

      {/* Chat container */}
      <Card className="flex-1 flex flex-col overflow-hidden" padding="none">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Bot className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-p1 font-sans text-text-secondary">Start a conversation with your SEO assistant</p>
                <p className="text-p2 font-sans text-text-muted mt-2">
                  Ask about your website's SEO, get recommendations, or analyze issues
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg: ChatMessage) => (
              <div
                key={msg.id}
                className={clsx(
                  'flex gap-3',
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-primary-600" />
                  </div>
                )}
                <div
                  className={clsx(
                    'max-w-[70%] px-4 py-2 rounded-2xl',
                    msg.role === 'user'
                      ? 'bg-primary-600 text-white rounded-tr-sm'
                      : 'bg-gray-100 text-text-primary rounded-tl-sm'
                  )}
                >
                  {msg.role === 'assistant' ? (
                    <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  )}
                  <p
                    className={clsx(
                      'text-note font-sans mt-1',
                      msg.role === 'user' ? 'text-primary-200' : 'text-text-muted'
                    )}
                  >
                    {new Date(msg.created_at).toLocaleTimeString()}
                  </p>
                </div>
                {msg.role === 'user' && (
                  <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-text-secondary" />
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex gap-3">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your SEO..."
              disabled={sendMutation.isPending}
              className="flex-1"
            />
            <Button
              onClick={handleSend}
              isLoading={sendMutation.isPending}
              disabled={!message.trim()}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
