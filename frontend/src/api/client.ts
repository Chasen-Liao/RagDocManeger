// API client for RagDocMan

// Use direct backend URL in dev to bypass Vite proxy buffering
const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : '/api'
const AGENT_API_BASE = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1'

interface ApiResponse<T> {
  success: boolean
  data: T | null
  error?: {
    code: string
    message: string
  }
  message?: string
  meta?: {
    total: number
    page: number
    limit: number
    pages: number
  }
}

export interface KnowledgeBase {
  id: string
  name: string
  description: string
  document_count: number
  total_size: number
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  kb_id: string
  name: string
  file_size: number
  file_type: string
  chunk_count: number
  created_at: string
}

export interface SearchResult {
  id: string
  content: string
  doc_id: string
  doc_name: string
  score: number
}

export interface SourceReference {
  doc_id: string
  doc_name: string
  chunk_id: string
  content: string
  score: number
}

export interface RagAnswerRequest {
  kb_id: string
  query: string
  top_k?: number
  include_sources?: boolean
  session_id?: string
}

export interface Config {
  app_name: string
  app_version: string
  debug: boolean
  log_level: string
  llm_provider: string
  llm_model: string
  embedding_provider: string
  embedding_model: string
  reranker_provider: string
  reranker_model: string
  max_file_size_mb: number
  supported_file_types: string[]
  chunk_size: number
  chunk_overlap: number
  retrieval_top_k: number
  reranking_top_k: number
}

// Agent API Types
export interface AgentMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface AgentToolCall {
  tool_name: string
  tool_input: Record<string, unknown>
  tool_output: Record<string, unknown>
  execution_time: number
}

export interface AgentRequest {
  user_input: string
  session_id: string
  stream?: boolean
  metadata?: Record<string, unknown>
}

export interface AgentResponse {
  success: boolean
  output: string
  tool_calls: AgentToolCall[]
  execution_time: number
  error?: string
  timestamp?: string
}

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const data = await response.json()
  return data as ApiResponse<T>
}

export const api = {
  // Knowledge Bases
  async getKnowledgeBases(skip = 0, limit = 20): Promise<ApiResponse<KnowledgeBase[]>> {
    const res = await fetch(`${API_BASE}/knowledge-bases?skip=${skip}&limit=${limit}`)
    return handleResponse<KnowledgeBase[]>(res)
  },

  async getKnowledgeBase(kbId: string): Promise<ApiResponse<KnowledgeBase>> {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}`)
    return handleResponse<KnowledgeBase>(res)
  },

  async createKnowledgeBase(data: { name: string; description: string }): Promise<ApiResponse<KnowledgeBase>> {
    const res = await fetch(`${API_BASE}/knowledge-bases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return handleResponse<KnowledgeBase>(res)
  },

  async updateKnowledgeBase(kbId: string, data: { name?: string; description?: string }): Promise<ApiResponse<KnowledgeBase>> {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return handleResponse<KnowledgeBase>(res)
  },

  async deleteKnowledgeBase(kbId: string): Promise<ApiResponse<null>> {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}`, {
      method: 'DELETE'
    })
    return handleResponse<null>(res)
  },

  // Documents
  async getDocuments(kbId: string, skip = 0, limit = 20): Promise<ApiResponse<Document[]>> {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/documents?skip=${skip}&limit=${limit}`)
    return handleResponse<Document[]>(res)
  },

  async uploadDocument(kbId: string, file: File): Promise<ApiResponse<Document>> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/documents/upload`, {
      method: 'POST',
      body: formData
    })
    return handleResponse<Document>(res)
  },

  async deleteDocument(kbId: string, docId: string): Promise<ApiResponse<null>> {
    const res = await fetch(`${API_BASE}/knowledge-bases/${kbId}/documents/${docId}`, {
      method: 'DELETE'
    })
    return handleResponse<null>(res)
  },

  // Search
  async search(kbId: string, query: string, topK = 5): Promise<ApiResponse<SearchResult[]>> {
    const res = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kb_id: kbId, query, top_k: topK })
    })
    return handleResponse<SearchResult[]>(res)
  },

  // Config
  async getConfig(): Promise<ApiResponse<Config>> {
    const res = await fetch(`${API_BASE}/config`)
    return handleResponse<Config>(res)
  },

  async updateConfig(data: Partial<Config>): Promise<ApiResponse<Config>> {
    const res = await fetch(`${API_BASE}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return handleResponse<Config>(res)
  },

  // RAG Streaming - callback-based for true streaming
  streamRagAnswer(
    request: RagAnswerRequest,
    callbacks: {
      onSources?: (sources: SourceReference[]) => void
      onContent?: (content: string, isFirst: boolean) => void
      onDone?: () => void
      onError?: (error: string) => void
    }
  ): Promise<void> {
    return new Promise(async (resolve, reject) => {
      try {
        const res = await fetch(`${API_BASE}/rag/answer/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  // Disable Nginx buffering
          },
          body: JSON.stringify(request)
        })

        if (!res.ok || !res.body) {
          throw new Error('Stream request failed')
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          buffer += chunk

          // Process each line immediately
          const lines = buffer.split('\n')
          // Keep the last partial line in buffer
          buffer = lines.pop() || ''

          for (const line of lines) {
            const trimmedLine = line.trim()
            if (!trimmedLine) continue

            if (trimmedLine.startsWith('data: ')) {
              try {
                const data = JSON.parse(trimmedLine.slice(6))

                if (data.type === 'sources' && callbacks.onSources) {
                  callbacks.onSources(data.data)
                } else if (data.type === 'content' && callbacks.onContent) {
                  callbacks.onContent(data.data, false)
                } else if (data.type === 'error' && callbacks.onError) {
                  callbacks.onError(data.data)
                } else if (data.type === 'done' && callbacks.onDone) {
                  callbacks.onDone()
                  resolve()
                  return
                }
              } catch {
                // Skip invalid JSON
              }
            }
          }
        }

        // Process any remaining buffer
        if (buffer.trim()) {
          const line = buffer.trim()
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'content' && callbacks.onContent) {
                callbacks.onContent(data.data, false)
              } else if (data.type === 'done' && callbacks.onDone) {
                callbacks.onDone()
              }
            } catch {
              // Skip
            }
          }
        }

        if (callbacks.onDone) {
          callbacks.onDone()
        }
        resolve()
      } catch (error) {
        if (callbacks.onError) {
          callbacks.onError(String(error))
        }
        reject(error)
      }
    })
  },

  // Agent API (new in backend)
  async sendAgentMessage(
    userInput: string,
    sessionId: string,
    callbacks?: {
      onToolCall?: (toolCall: AgentToolCall) => void
      onContent?: (content: string) => void
      onDone?: (response: AgentResponse) => void
      onError?: (error: string) => void
    }
  ): Promise<AgentResponse> {
    try {
      const res = await fetch(`${AGENT_API_BASE}/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: userInput,
          session_id: sessionId,
          stream: false
        })
      })

      const data = await res.json() as ApiResponse<AgentResponse>

      if (!data.success || !data.data) {
        throw new Error(data.error?.message || 'Agent request failed')
      }

      if (callbacks?.onToolCall) {
        data.data.tool_calls.forEach(tc => callbacks.onToolCall!(tc))
      }

      if (callbacks?.onContent) {
        callbacks.onContent(data.data.output)
      }

      if (callbacks?.onDone) {
        callbacks.onDone(data.data)
      }

      return data.data
    } catch (error) {
      if (callbacks?.onError) {
        callbacks.onError(String(error))
      }
      throw error
    }
  },

  // Agent Streaming
  streamAgentMessage(
    userInput: string,
    sessionId: string,
    callbacks: {
      onToolCall?: (toolCall: { type: string; data: AgentToolCall }) => void
      onContent?: (content: string, type: string) => void
      onDone?: () => void
      onError?: (error: string) => void
    }
  ): Promise<void> {
    return new Promise(async (resolve, reject) => {
      try {
        const res = await fetch(`${AGENT_API_BASE}/agent/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
          },
          body: JSON.stringify({
            user_input: userInput,
            session_id: sessionId,
            stream: true
          })
        })

        if (!res.ok || !res.body) {
          throw new Error('Stream request failed')
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          buffer += chunk

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const trimmedLine = line.trim()
            if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue

            try {
              const data = JSON.parse(trimmedLine.slice(6))
              const chunkType = data.type || 'output'

              if (chunkType === 'tool_call' && callbacks.onToolCall) {
                callbacks.onToolCall(data)
              } else if (chunkType === 'output' && callbacks.onContent) {
                callbacks.onContent(data.data?.output || '', chunkType)
              } else if (chunkType === 'end' && callbacks.onDone) {
                callbacks.onDone()
                resolve()
                return
              } else if (chunkType === 'error' && callbacks.onError) {
                callbacks.onError(data.data?.error || 'Unknown error')
              }
            } catch {
              // Skip invalid JSON
            }
          }
        }

        if (callbacks.onDone) {
          callbacks.onDone()
        }
        resolve()
      } catch (error) {
        if (callbacks.onError) {
          callbacks.onError(String(error))
        }
        reject(error)
      }
    })
  },

  // Clear agent session
  async clearAgentSession(sessionId: string): Promise<ApiResponse<{ success: boolean; message: string; session_id: string }>> {
    const res = await fetch(`${AGENT_API_BASE}/agent/session/${sessionId}`, {
      method: 'DELETE'
    })
    return handleResponse(res)
  },

  // List all sessions
  async listSessions(): Promise<ApiResponse<Array<{
    session_id: string
    last_message_at: string
    preview: string
    message_count: number
  }>>> {
    const res = await fetch(`${AGENT_API_BASE}/agent/sessions`)
    return handleResponse(res)
  },

  // Get session history
  async getSessionHistory(sessionId: string, limit = 50): Promise<ApiResponse<{
    session_id: string
    messages: Array<{
      role: string
      content: string
      created_at: string
    }>
    message_count: number
  }>> {
    const res = await fetch(`${AGENT_API_BASE}/agent/sessions/${sessionId}/history?limit=${limit}`)
    return handleResponse(res)
  },

  // Health
  async healthCheck(): Promise<ApiResponse<{ status: string; app_name: string; version: string }>> {
    const res = await fetch(`${API_BASE}/health`)
    return handleResponse(res)
  }
}