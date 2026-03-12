import { useState, useRef, useEffect } from 'react'
import { clsx } from 'clsx'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { chatService } from '@/services/chat'

// Default suggestions
const DEFAULT_SUGGESTIONS = [
  'How was my SEO last week?',
  'Run a new audit',
  'What are my top issues?',
  'Show me traffic trends',
]

// Chat Message Component
function ChatMessage({ message, isUser }: { message: { content: string; role: string }; isUser: boolean }) {
  return (
    <div className={clsx('flex gap-3 mb-4', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div className={clsx(
        'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
        isUser ? 'bg-[#FFEADE]' : 'bg-primary-600'
      )}>
        {isUser ? (
          <svg className="w-[18px] h-[18px] text-primary-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
          </svg>
        )}
      </div>

      {/* Message Content */}
      <div className={clsx(
        'rounded-2xl px-4 py-3 max-w-[80%]',
        isUser ? 'bg-[#FFEADE]' : 'bg-gray-100'
      )}>
        <div className="text-p1 font-sans text-text-secondary">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Text elements
              p: ({ children }) => <p className="text-p1 font-sans mb-2 last:mb-0">{children}</p>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              // Lists
              ul: ({ children }) => <ul className="text-p1 font-sans list-disc list-inside mb-2 last:mb-0 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="text-p1 font-sans list-decimal list-inside mb-2 last:mb-0 space-y-1">{children}</ol>,
              li: ({ children }) => <li className="text-p1 font-sans">{children}</li>,
              // Headings
              h1: ({ children }) => <h1 className="text-h3 font-heading font-bold mb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-h3 font-heading font-semibold mb-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-h3 font-heading font-semibold mb-1">{children}</h3>,
              // Code
              code: ({ children, className }) => {
                const isInline = !className
                return isInline
                  ? <code className="text-note font-sans bg-gray-200 px-1 py-0.5 rounded">{children}</code>
                  : <code className="block text-note font-sans bg-gray-800 text-green-400 p-2 rounded overflow-x-auto my-2">{children}</code>
              },
              pre: ({ children }) => <pre className="text-note font-sans bg-gray-800 text-green-400 p-2 rounded overflow-x-auto my-2">{children}</pre>,
              // Tables
              table: ({ children }) => (
                <div className="overflow-x-auto my-2">
                  <table className="text-note font-sans border-collapse border border-gray-300 w-full">{children}</table>
                </div>
              ),
              thead: ({ children }) => <thead className="bg-gray-100">{children}</thead>,
              tbody: ({ children }) => <tbody>{children}</tbody>,
              tr: ({ children }) => <tr className="border-b border-gray-200">{children}</tr>,
              th: ({ children }) => <th className="text-left px-2 py-1 border border-gray-300 font-semibold">{children}</th>,
              td: ({ children }) => <td className="text-left px-2 py-1 border border-gray-300">{children}</td>,
              // Links
              a: ({ href, children }) => <a href={href} className="text-primary-600 underline hover:text-primary-700" target="_blank" rel="noopener noreferrer">{children}</a>,
              // Blockquote
              blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-3 italic text-text-secondary my-2">{children}</blockquote>,
              // Horizontal rule
              hr: () => <hr className="my-2 border-gray-300" />,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

interface ChatSectionProps {
  selectedWebsite: string | null
  onAuditRequest: () => void
}

export function ChatSection({ selectedWebsite, onAuditRequest }: ChatSectionProps) {
  const [chatInput, setChatInput] = useState('')
  const [messages, setMessages] = useState<{ content: string; role: 'user' | 'assistant' }[]>([])
  const [isSending, setIsSending] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [pendingAuditConfirmation, setPendingAuditConfirmation] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load latest conversation on mount
  useEffect(() => {
    const loadConversation = async () => {
      try {
        // Get conversations list
        const conversations = await chatService.getConversations(1)
        if (conversations && conversations.length > 0) {
          const latestConv = conversations[0]
          setConversationId(latestConv.id)

          // Load messages for this conversation
          const convData = await chatService.getConversation(latestConv.id)
          if (convData?.messages && convData.messages.length > 0) {
            setMessages(convData.messages.map(m => ({
              content: m.content,
              role: m.role as 'user' | 'assistant'
            })))
          }
        }
      } catch (error) {
        console.error('Failed to load conversation:', error)
      } finally {
        setIsLoading(false)
      }
    }
    loadConversation()
  }, [])

  // Send chat message
  const sendMessage = async (text: string) => {
    if (!text.trim() || isSending) return

    const userMessage = { content: text.trim(), role: 'user' as const }
    setMessages(prev => [...prev, userMessage])
    setChatInput('')
    setIsSending(true)

    // Check if user wants to run audit
    const auditKeywords = ['run audit', 'new audit', 'run a new audit', 'start audit']
    const confirmKeywords = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'please', 'do it']
    const shouldRunAudit = auditKeywords.some(keyword => text.toLowerCase().includes(keyword))
    const isConfirmation = confirmKeywords.some(keyword => text.toLowerCase().trim() === keyword || text.toLowerCase().includes(keyword))

    // Trigger audit if explicit request OR confirmation after AI asked
    if ((shouldRunAudit || (pendingAuditConfirmation && isConfirmation)) && selectedWebsite) {
      onAuditRequest()
      setPendingAuditConfirmation(false)
    }

    try {
      const response = await chatService.sendMessage(text.trim(), conversationId ?? undefined, selectedWebsite ?? undefined)

      if (response.conversation_id) {
        setConversationId(response.conversation_id)
      }

      const aiMessage = {
        content: response.message || "I understand your question. Let me help you with that.",
        role: 'assistant' as const
      }
      setMessages(prev => [...prev, aiMessage])

      // Check if AI is asking about running an audit - set pending confirmation
      const aiAskingAudit = response.message?.toLowerCase().includes('would you like me to run') ||
                           response.message?.toLowerCase().includes('run an audit') ||
                           response.message?.toLowerCase().includes('run a comprehensive audit')
      if (aiAskingAudit) {
        setPendingAuditConfirmation(true)
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        content: "Sorry, I encountered an error. Please try again.",
        role: 'assistant'
      }])
    } finally {
      setIsSending(false)
    }
  }

  // Auto-scroll to bottom only when there are messages
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  return (
    <section className="chat-section">
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <div className="mb-4 pb-4 border-b border-gray-200">
          <h2 className="text-h2 font-heading font-semibold text-text-primary">Solvia</h2>
          <p className="text-p1 font-sans text-text-secondary">
            I oversee your entire SEO team. Ask me anything about your SEO performance.
          </p>
        </div>

        {/* Chat Messages - White background */}
        <div className="mb-4 max-h-[300px] overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin h-5 w-5 border-2 border-primary-600 border-t-transparent rounded-full"></div>
              <span className="ml-2 text-p2 font-sans text-text-secondary">Loading conversation...</span>
            </div>
          ) : messages.length === 0 ? (
            <ChatMessage
              message={{ content: "Hello! I'm Solvia, your SEO agent. How can I help you today?", role: 'assistant' }}
              isUser={false}
            />
          ) : (
            messages.map((msg, idx) => (
              <ChatMessage key={idx} message={msg} isUser={msg.role === 'user'} />
            ))
          )}

          {isSending && (
            <div className="flex gap-3 mb-4">
              <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white animate-pulse" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                </svg>
              </div>
              <div className="bg-gray-100 rounded-2xl px-4 py-3">
                <p className="text-p2 font-sans text-text-secondary">Thinking...</p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input - Connected but separate */}
        <div className="flex">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage(chatInput)}
            placeholder="Type a message ..."
            className="flex-1 px-4 py-3 text-p1 font-sans border border-gray-200 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            disabled={isSending}
          />
          <button
            onClick={() => sendMessage(chatInput)}
            disabled={isSending || !chatInput.trim()}
            className="px-4 py-3 bg-primary-600 text-white rounded-r-lg border border-l-0 border-primary-600 hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5 -rotate-45" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
            </svg>
          </button>
        </div>

        {/* Suggestion Buttons - Compact */}
        <div className="flex flex-wrap gap-2 mt-3">
          {DEFAULT_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => sendMessage(suggestion)}
              disabled={isSending}
              className={clsx(
                'px-3 py-1.5 text-p2 font-sans rounded-full border transition-all',
                'bg-white text-primary-600 border-primary-600',
                'hover:bg-primary-600 hover:text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
